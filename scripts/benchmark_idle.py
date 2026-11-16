#!/usr/bin/env python3
"""Offscreen CPU benchmark; no services, radios or display devices are touched."""
import argparse
import json
from pathlib import Path
import sys
import tempfile
import time
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--installed-baseline',action='store_true');parser.add_argument('--seconds',type=float,default=3);args=parser.parse_args()
sys.path.insert(0,'/usr/local/lib/verdant-cyberdeck' if args.installed_baseline else str(Path(__file__).resolve().parents[1]))
from cyberdeck.native import NativeDeck
with tempfile.TemporaryDirectory() as directory:
 app=NativeDeck(lambda _:None,lambda _:None,log_path=Path(directory)/'benchmark.log')
 app.splash_until=0;app._splash_pending=False;app.status='Stable benchmark status';app.next_status=float('inf')
 start=time.monotonic();cpu=time.process_time();renders=writes=polls=0;frame=None;rendered=0;written=0
 while time.monotonic()-start<args.seconds:
  now=time.monotonic();polls+=1
  if args.installed_baseline:
   if frame is None or now-rendered>=0.1:frame=app.render();renders+=1;rendered=now
   if now-written>=1/30:frame.tobytes('raw','BGRX');writes+=1;written=now
   time.sleep(0.01)
  else:
   if app.needs_redraw():frame=app.render();frame.tobytes('raw','BGRX');renders+=1;writes+=1
   time.sleep(0.25)
 elapsed=time.monotonic()-start;used=time.process_time()-cpu;app.close_runtime()
 print(json.dumps({'implementation':'installed baseline' if args.installed_baseline else 'updated event redraw','seconds':round(elapsed,3),'cpu_seconds':round(used,4),'one_core_percent':round(100*used/elapsed,2),'renders':renders,'frame_encodes':writes,'polls':polls,'offscreen_only':True}))
