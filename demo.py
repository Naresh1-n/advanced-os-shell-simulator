#!/usr/bin/env python3
"""Repeatable Day 1 demonstration of the shell's command loop and job states."""
import contextlib
import io
import os
import signal
import tempfile
from shell import Shell


def run(shell, command):
    print(f'shell$ {command}', flush=True)
    shell.execute(command)


def main():
    with tempfile.TemporaryDirectory() as workdir:
        original = os.getcwd()
        try:
            os.chdir(workdir)
            shell = Shell()
            print('=== BUILT-IN COMMANDS ===')
            for cmd in ('pwd', 'echo "Hello from Day 1"', 'mkdir sample',
                        'cd sample', 'touch notes.txt', 'ls', 'cat notes.txt',
                        'cd ..', 'rm sample/notes.txt', 'rmdir sample'):
                run(shell, cmd)
            print('\n=== FOREGROUND AND BACKGROUND JOBS ===')
            run(shell, 'sleep 0.1')
            run(shell, 'sleep 2 &')
            run(shell, 'jobs')
            job = shell.jobs[1]
            os.killpg(job.process.pid, signal.SIGSTOP)
            job.state = 'Stopped'  # simulate external stop; see shell limitations
            print(f'[demo] SIGSTOP sent to PID {job.process.pid}')
            run(shell, 'jobs')
            run(shell, 'bg 1')
            run(shell, 'fg 1')
            run(shell, 'jobs')
            print('\n=== ERROR HANDLING ===')
            for cmd in ('unknown_day1_command', 'cat missing.txt', 'fg 99',
                        'mkdir', 'echo "unfinished'):
                run(shell, cmd)
            run(shell, 'exit')
        finally:
            os.chdir(original)


if __name__ == '__main__':
    if os.name != 'posix':
        raise SystemExit('Demo requires Linux, macOS, or WSL')
    main()
