"""Bounded subprocesses. No shell, implicit privilege escalation, or radio changes."""
import logging
import shutil
import subprocess
from dataclasses import dataclass

@dataclass
class Result:
    code: int
    output: str

def run(args, timeout=12):
    try:
        p = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        result = Result(p.returncode, (p.stdout + p.stderr).strip())
    except (OSError, subprocess.TimeoutExpired) as exc:
        result = Result(127, str(exc))
    if result.code:
        logging.warning('Command %s returned %s: %s', args[0], result.code, result.output[:500])
    return result

def installed(executable):
    return shutil.which(executable)
