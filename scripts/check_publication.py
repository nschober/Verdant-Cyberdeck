#!/usr/bin/env python3
"""Check staged/tracked content for common accidental private artifacts.

This is a focused publication check, not an exhaustive secret scanner.
"""
from pathlib import Path
import re
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
RULES={
    'private key':re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----'),
    'GitHub token':re.compile(rb'\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b'),
    'AWS access key':re.compile(rb'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b'),
    'URL credentials':re.compile(rb'https?://[^\s/:]+:[^\s/@]+@'),
}

def main():
    output=subprocess.check_output(['git','ls-files','--cached','-z'],cwd=ROOT)
    files=[Path(p.decode()) for p in output.split(b'\0') if p]
    if not files:
        print('No staged or tracked files to inspect',file=sys.stderr)
        return 1
    failures=[]
    for relative in files:
        if relative.parts[0] in ('logs','backups') or '__pycache__' in relative.parts or relative.suffix in ('.pcap','.pcapng','.cap','.pem','.key','.pyc'):
            failures.append(f'{relative}: host-local or sensitive artifact type')
        content=(ROOT/relative).read_bytes()
        for name,pattern in RULES.items():
            if pattern.search(content):
                failures.append(f'{relative}: possible {name}; inspect privately')
    if failures:
        print('\n'.join(failures),file=sys.stderr)
        return 1
    print(f'Publication checks passed for {len(files)} files. Manual review is still required.')
    return 0

if __name__=='__main__':
    sys.exit(main())
