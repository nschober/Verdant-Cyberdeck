"""Writable per-user state for source, wheel and Debian installations."""
import os
from pathlib import Path

def log_directory():
    return Path(os.environ.get('XDG_STATE_HOME',str(Path.home()/'.local/state')))/'verdant-cyberdeck/logs'

def asset_directory(root):
    # Validation must not mutate tracked source or installed package resources.
    target=Path(os.environ.get('XDG_CACHE_HOME',str(Path.home()/'.cache')))/'verdant-cyberdeck/previews'
    target.mkdir(parents=True,exist_ok=True)
    return target
