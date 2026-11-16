"""Writable per-user state for source, wheel and Debian installations."""
import os
from pathlib import Path

def log_directory():
    return Path(os.environ.get('XDG_STATE_HOME',str(Path.home()/'.local/state')))/'verdant-cyberdeck/logs'

def asset_directory(root):
    local=Path(root)/'assets'
    if local.is_dir() and os.access(local,os.W_OK):return local
    target=Path(os.environ.get('XDG_CACHE_HOME',str(Path.home()/'.cache')))/'verdant-cyberdeck/previews'
    target.mkdir(parents=True,exist_ok=True)
    return target
