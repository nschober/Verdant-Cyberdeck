import os
import shlex
import subprocess
from .backend import installed

TOOLS = {
 'NETWORK': [('Nmap','nmap',['--help']), ('Bettercap','bettercap',['-h']), ('Metasploit','msfconsole',[])],
 'WIRELESS': [('Aircrack-ng','aircrack-ng',['--help']), ('Wifite','wifite',['--help']), ('Kismet','kismet',['--help'])],
 'TRAFFIC / WEB': [('tcpdump','tcpdump',['--help']), ('TShark','tshark',['--help']), ('Nikto','nikto',['-Help']), ('Gobuster','gobuster',['--help']), ('SQLmap','sqlmap',['-h'])],
 'SYSTEM': [('tmux','tmux',[]), ('htop','htop',[]), ('Terminal','bash',[])]
}

def terminal_command(argv):
    terminal = installed('xterm')
    if not terminal:
        raise RuntimeError('xterm is missing')
    # Arguments are positional parameters; no command text is evaluated by the shell.
    return [terminal, '-geometry', '65x18', '-fa', 'DejaVu Sans Mono', '-fs', '8', '-e',
            '/bin/bash', '-c', '"$@"; rc=$?; printf "\\nExit code: %s\\nPress Enter to return" "$rc"; read -r _', 'cyberdeck', *argv]

def launch(executable, args=()):
    path = installed(executable)
    if not path:
        raise RuntimeError(f'{executable} is not installed')
    if not os.environ.get('DISPLAY'):
        raise RuntimeError('Interactive terminal needs an existing desktop session. Use tool help on the TFT or launch from SSH.')
    subprocess.Popen(terminal_command([path, *args]), start_new_session=True)

def service(action):
    from .pwnagotchi import control_args
    argv = control_args(action)
    # Existing desktop policy agent asks for authentication, no sudoers changes.
    if installed('pkexec'):
        argv = [installed('pkexec'), *argv]
    subprocess.Popen(terminal_command(argv), start_new_session=True)
