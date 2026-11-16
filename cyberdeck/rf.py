"""Explicit launchers for SDR receive/transmit, protocol and signal analysis tools."""
import argparse
import os
from pathlib import Path
import subprocess
from .backend import installed

GUI={'gqrx','gnuradio-companion','inspectrum','urh'}
GROUPS={
 'RF SPECTRUM':[('GQRX','gqrx',[]),('GNU RADIO','gnuradio-companion',[]),('INSPECTRUM','inspectrum',[]),('URH','urh',[])],
 'RF PROTOCOLS':[('RTL 433','rtl_433',['-h']),('URH','urh',[]),('GNU RADIO','gnuradio-companion',[])],
 'RF GSM':[('GSM LIVEMON','grgsm_livemon',['--help']),('GSM SCANNER','grgsm_scanner',['--help']),('GSM DECODE','grgsm_decode',['--help']),('KALIBRATE RTL','kal',['-h'])],
 'RF DEVICES':[('HACKRF RX / TX','hackrf_transfer',['-h']),('HACKRF SWEEP','hackrf_sweep',['-h']),('RTL POWER','rtl_power',['-h']),('RTL SDR RECORD','rtl_sdr',['-h']),('BLADERF CLI','bladeRF-cli',['-h']),('SOAPY SDR','SoapySDRUtil',['--help'])]
}

def user_tool_path(executable):
    if executable not in ('urh','grgsm_decode','grgsm_scanner','grgsm_livemon','grgsm_livemon_headless'):return None
    path=Path('/home/kali/.local/bin')/executable
    return str(path) if path.is_file() and os.access(path,os.X_OK) else None

def tool_path(executable):return installed(executable) or user_tool_path(executable)


def hardware():
    rows=['RF / SDR HARDWARE','']
    products=[]
    for file in sorted(Path('/sys/bus/usb/devices').glob('*/product')):
        try:
            product=file.read_text().strip();products.append(product);rows.append(product)
        except OSError:pass
    rows += ['',('Recognized SDR USB product: '+', '.join(p for p in products if any(tag in p.lower() for tag in ('hackrf','portapack','rtl283','rtl-sdr','bladerf','limesdr','airspy','sdrplay','plutosdr')))) if any(any(tag in p.lower() for tag in ('hackrf','portapack','rtl283','rtl-sdr','bladerf','limesdr','airspy','sdrplay','plutosdr')) for p in products) else 'No known SDR USB product identified. Driver-level compatibility must be confirmed.',
             'Built-in Wi-Fi/Bluetooth are not general-purpose GSM or sub-GHz receivers. GSM and remote/key protocols require matching RF hardware and frequency coverage.',
             'Receive, transmit, device control and protocol tools are available through explicit launchers. Opening this menu starts no RF operation.',
             'Graphical SDR tools open in the existing desktop/HDMI session. The native TFT remains the launcher and CLI console.']
    return '\n'.join(rows)

def status():
    return '\n'.join(f'{name}: {tool_path(exe) or "NOT INSTALLED"}' for group in GROUPS.values() for name,exe,_ in group)

def launch_gui(executable):
    if executable not in GUI:raise ValueError('Unknown RF graphical application')
    path=tool_path(executable)
    if not path:raise RuntimeError(executable+' is not installed')
    if os.geteuid()==0:raise RuntimeError('Launch the desktop application as the logged-in user')
    environment=dict(os.environ)
    if not environment.get('DISPLAY'):
        keys=('DISPLAY','XAUTHORITY','XDG_RUNTIME_DIR','DBUS_SESSION_BUS_ADDRESS')
        for directory in Path('/proc').iterdir():
            if not directory.name.isdigit():continue
            try:
                if directory.stat().st_uid!=os.getuid():continue
                if (directory/'comm').read_text().strip() not in ('xfce4-session','gnome-session','plasmashell'):continue
                values=dict(part.split('=',1) for part in (directory/'environ').read_bytes().decode(errors='replace').split('\0') if '=' in part)
                if values.get('DISPLAY'):
                    environment.update({k:values[k] for k in keys if values.get(k)});break
            except OSError:continue
    if not environment.get('DISPLAY'):raise RuntimeError('No accessible existing desktop session. Use the CLI tools or log in on HDMI first.')
    return subprocess.Popen([path],env=environment,start_new_session=True)

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--gui',choices=sorted(GUI),required=True)
    args=parser.parse_args()
    try:launch_gui(args.gui)
    except (OSError,RuntimeError,ValueError) as exc:parser.exit(1,str(exc)+'\n')

if __name__=='__main__':main()
