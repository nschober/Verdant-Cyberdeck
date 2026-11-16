"""Convert stable local captures into daily Hashcat files and a CSV inventory.

No wireless operations, password guesses or Hashcat jobs are started.
"""
import argparse
import csv
import datetime as dt
import fcntl
import hashlib
import io
import json
import logging
import os
from pathlib import Path
import re
import shutil
import signal
import stat
import subprocess
import tempfile
import time

EXTENSIONS={'.pcap','.pcapng','.cap'}
MAX_CAPTURE=256*1024*1024
COLUMNS=('capture_date','captured_at','timezone','source_capture','capture_sha256','capture_size_bytes','capture_format',
         'ssid','ssid_hex','access_point_mac','client_mac','handshake_type',
         'record_sha256','message_pair_hex','daily_hash_file','converted_at',
         'status','records_in_capture','new_daily_records','converter','processing_seconds','error')


def atomic(path,data,mode=0o640):
    path=Path(path)
    if path.is_symlink():raise ValueError('Refusing symlink output')
    fd,name=tempfile.mkstemp(prefix='.processor-',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as out:
            out.write(data);out.flush();os.fsync(out.fileno());os.fchmod(out.fileno(),mode)
        os.replace(name,path)
        directory=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
        try:os.fsync(directory)
        finally:os.close(directory)
    finally:
        if os.path.exists(name):os.unlink(name)


def fingerprint(info):return [info.st_dev,info.st_ino,info.st_size,info.st_mtime_ns,info.st_ctime_ns]


def parse_record(line):
    parts=line.strip().split('*')
    if len(parts)!=9 or parts[0]!='WPA' or parts[1] not in ('01','02'):raise ValueError('Invalid mode-22000 record')
    if any(not re.fullmatch('[0-9a-fA-F]*',part) or len(part)%2 for part in parts[2:]):raise ValueError('Invalid hexadecimal record fields')
    if len(parts[2])!=32 or len(parts[3])!=12 or len(parts[4])!=12 or len(parts[5])>64:raise ValueError('Invalid mode-22000 field length')
    if parts[1]=='02' and (len(parts[6])!=64 or not parts[7] or len(parts[8])!=2):raise ValueError('Incomplete EAPOL record')
    if parts[1]=='01' and any(parts[6:]):raise ValueError('Invalid PMKID record')
    canonical='*'.join(parts[:2]+[part.lower() for part in parts[2:]])
    ssid=bytes.fromhex(parts[5]).decode('utf-8',errors='replace')
    ssid=''.join(c if c.isprintable() else '\\x%02x'%ord(c) for c in ssid)
    mac=lambda text:':'.join(text[i:i+2].lower() for i in range(0,12,2))
    return canonical,{'ssid':ssid,'ssid_hex':parts[5].lower(),'access_point_mac':mac(parts[3]),
                      'client_mac':mac(parts[4]),'handshake_type':'PMKID' if parts[1]=='01' else 'EAPOL',
                      'record_sha256':hashlib.sha256(canonical.encode()).hexdigest(),
                      'message_pair_hex':parts[8].lower()}


def read_records(path):
    path=Path(path)
    if not path.exists():return []
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    with os.fdopen(fd,'rb') as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):raise ValueError('Expected regular hash output')
        data=stream.read(128*1024*1024+1)
    if len(data)>128*1024*1024:raise ValueError('Daily hash output exceeds 128 MiB limit')
    return sorted({parse_record(line)[0] for line in data.decode('ascii').splitlines() if line.strip()})


def spreadsheet_cell(value):
    value=str(value)
    # Excel can interpret quoted CSV cells as formulas; prefix dangerous cells.
    if value.lstrip().startswith(('=','+','-','@')) or value.startswith(('\t','\r','\n')):return "'"+value
    return value


class Processor:
    def __init__(self,source,output,converter=None,settle=10,runner=subprocess.run):
        self.source=Path(source).resolve(strict=True)
        if not self.source.is_dir():raise ValueError('Capture source is not a directory')
        self.output=Path(output)
        if self.output.is_symlink():raise ValueError('Refusing symlink output directory')
        self.output.mkdir(parents=True,exist_ok=True,mode=0o750)
        if self.output.resolve()==self.source or self.source.is_relative_to(self.output.resolve()):raise ValueError('Output must be separate from capture input')
        self.converter=converter or shutil.which('hcxpcapngtool')
        if not self.converter:raise RuntimeError('hcxpcapngtool is required (hcxtools package)')
        self.settle=settle;self.runner=runner;self.seen={};self.running=True
        self.state_path=self.output/'.processor-state.json'
        if self.state_path.is_symlink():raise ValueError('Refusing symlink state')
        self.state=json.loads(self.state_path.read_text()) if self.state_path.exists() else {'version':1,'captures':{},'latest':{}}
        if self.state.get('version')!=1 or not isinstance(self.state.get('captures'),dict):raise ValueError('Unrecognized processor state')
        self.state.setdefault('latest',{})
        lockfd=os.open(self.output/'.processor.lock',os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW,0o600)
        self.lock=os.fdopen(lockfd,'w')
        try:fcntl.flock(self.lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:
            self.lock.close();raise RuntimeError('Another processor already owns this output directory')

    def close(self):self.lock.close()

    def inventory(self):
        content=io.StringIO(newline='');writer=csv.DictWriter(content,fieldnames=COLUMNS,quoting=csv.QUOTE_ALL)
        writer.writeheader()
        for name,item in sorted(self.state['captures'].items()):
            base={key:item.get(key,'') for key in COLUMNS}
            base['source_capture']=item.get('source_capture',name)
            records=item.get('records',[])
            for record in records or ['']:
                row=dict(base)
                if record:row.update(parse_record(record)[1])
                writer.writerow({k:spreadsheet_cell(v) for k,v in row.items()})
        atomic(self.output/'handshakes.csv',content.getvalue().encode('utf-8-sig'))

    def commit(self):
        atomic(self.state_path,(json.dumps(self.state,indent=2)+'\n').encode(),0o600)
        self.inventory()

    def scan(self,now=None):
        now=time.time() if now is None else now;converted=0
        paths=[]
        for parent,dirs,files in os.walk(self.source,followlinks=False):
            dirs[:]=[name for name in dirs if not (Path(parent)/name).is_symlink() and (Path(parent)/name).resolve()!=self.output.resolve()]
            paths.extend(Path(parent)/name for name in files)
        for path in sorted(paths):
            if not self.running:break
            if path.suffix.lower() not in EXTENSIONS or path.is_symlink():continue
            try:info=path.stat(follow_symlinks=False)
            except FileNotFoundError:continue
            if not stat.S_ISREG(info.st_mode):continue
            sig=fingerprint(info);name=str(path.relative_to(self.source))
            prior=self.state['latest'].get(name)
            if prior and prior.get('fingerprint')==sig:
                if prior.get('status')!='error' or now-prior.get('attempted_at',now)<60:continue
            previous=self.seen.get(name);self.seen[name]=sig
            if previous!=sig or now-info.st_mtime<self.settle:continue
            converted+=self.convert(path,info)
        # Rebuild CSV on every scan: recover a crash after state commit but before CSV.
        csv_path=self.output/'handshakes.csv'
        if not csv_path.exists() or (self.state_path.exists() and self.state_path.stat().st_mtime_ns>csv_path.stat().st_mtime_ns):self.inventory()
        return converted

    def convert(self,path,info):
        captured=dt.datetime.fromtimestamp(info.st_mtime).astimezone()
        date=captured.date().isoformat();daily=self.output/(date+'.22000')
        started=time.monotonic()
        name=str(path.relative_to(self.source))
        entry={'source_capture':name,'capture_size_bytes':info.st_size,'capture_format':path.suffix.lower().lstrip('.'),'processing_seconds':0,'fingerprint':fingerprint(info),'capture_date':date,'captured_at':captured.isoformat(),
               'timezone':captured.tzname(),'capture_sha256':'','daily_hash_file':str(daily),
               'converted_at':dt.datetime.now().astimezone().isoformat(),'status':'error',
               'records_in_capture':0,'new_daily_records':0,'records':[],'converter':Path(self.converter).name,'error':''}
        try:
            if info.st_size>MAX_CAPTURE:raise ValueError('Capture exceeds 256 MiB limit')
            with tempfile.TemporaryDirectory(prefix='.conversion-',dir=self.output) as work:
                work=Path(work);snapshot=work/('capture'+path.suffix.lower());result_path=work/'hashes.22000'
                fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
                with os.fdopen(fd,'rb') as source,snapshot.open('wb') as destination:
                    if fingerprint(os.fstat(source.fileno()))!=fingerprint(info):return 0
                    digest=hashlib.sha256();total=0
                    while True:
                        chunk=source.read(1024*1024)
                        if not chunk:break
                        total+=len(chunk)
                        if total>MAX_CAPTURE:raise ValueError('Capture exceeds 256 MiB limit')
                        digest.update(chunk);destination.write(chunk)
                    if fingerprint(os.fstat(source.fileno()))!=fingerprint(info):return 0
                entry['capture_sha256']=digest.hexdigest()
                # Stream converter output to a private log; retain only a short error detail.
                with (work/'converter.log').open('w+b') as log:
                    result=self.runner([self.converter,'-o',str(result_path),str(snapshot)],stdout=log,stderr=subprocess.STDOUT,timeout=120,check=False)
                    if result.returncode:
                        log.seek(0);detail=log.read(2000).decode(errors='replace')
                        raise RuntimeError('hcxpcapngtool exit '+str(result.returncode)+': '+detail)
                if fingerprint(path.stat(follow_symlinks=False))!=fingerprint(info):return 0
                records=read_records(result_path)
                old=set(read_records(daily));new=old|set(records)
                if records:
                    atomic(daily,(''.join(line+'\n' for line in sorted(new))).encode('ascii'))
                entry.update(records=records,records_in_capture=len(records),new_daily_records=len(new)-len(old),
                             status='converted' if records else 'no_usable_hash')
        except (OSError,ValueError,RuntimeError,subprocess.TimeoutExpired) as exc:
            entry['error']=str(exc)[:2000]
            logging.error('Capture conversion failed (%s): %s',path.name,type(exc).__name__)
        entry['processing_seconds']=round(time.monotonic()-started,3)
        key=hashlib.sha256((name+json.dumps(fingerprint(info))).encode()).hexdigest()
        self.state['captures'][key]=entry
        self.state['latest'][name]={'fingerprint':fingerprint(info),'status':entry['status'],'attempted_at':time.time()}
        self.commit()
        logging.info('Capture processed: date=%s status=%s records=%s new_daily_records=%s',date,entry['status'],entry['records_in_capture'],entry['new_daily_records'])
        return 1

    def run(self,watch=False,interval=5):
        if watch:
            def stop(*_):self.running=False
            signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
            while self.running:
                self.scan()
                for _ in range(max(1,int(interval*10))):
                    if not self.running:break
                    time.sleep(0.1)
        else:
            self.scan();time.sleep(self.settle);self.scan()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',required=True,type=Path)
    parser.add_argument('--output',type=Path,default=Path('/var/lib/verdant-cyberdeck/hashcat'))
    parser.add_argument('--watch',action='store_true')
    args=parser.parse_args()
    logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s')
    processor=Processor(args.input,args.output)
    try:processor.run(args.watch)
    finally:processor.close()

if __name__=='__main__':main()
