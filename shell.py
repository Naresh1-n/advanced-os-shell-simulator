#!/usr/bin/env python3
"""Residency Day 1: Unix-like shell with built-ins and basic job control.

Runs on POSIX systems (Linux/macOS). External commands are executed with
subprocess, rather than reimplementing fork/exec/wait in Python.
"""
import os
import shlex
import shutil
import signal
import subprocess
import sys
import time
from dataclasses import dataclass


@dataclass
class Job:
    number: int
    process: subprocess.Popen
    command: str
    state: str = 'Running'


class Shell:
    def __init__(self):
        self.jobs = {}
        self.next_job = 1
        self.active = True
        self.interactive = sys.stdin.isatty()

    def report_finished(self):
        for job in self.jobs.values():
            code = job.process.poll()
            if code is not None and job.state != 'Done':
                job.state = 'Done'
                print(f'[{job.number}] Done (exit {code}) {job.command}')

    def get_job(self, argument):
        try:
            number = int(argument.lstrip('%'))
        except ValueError:
            print('shell: job ID must be a number')
            return None
        job = self.jobs.get(number)
        if job is None:
            print(f'shell: no such job: {number}')
        return job

    def built_in(self, args):
        cmd = args[0]
        try:
            if cmd == 'pwd':
                print(os.getcwd())
            elif cmd == 'cd':
                if len(args) > 2:
                    print('cd: usage: cd [directory]')
                else:
                    os.chdir(os.path.expanduser(args[1] if len(args) == 2 else '~'))
            elif cmd == 'exit':
                if any(j.process.poll() is None for j in self.jobs.values()):
                    print('shell: background jobs still running; they will continue after exit')
                self.active = False
            elif cmd == 'echo':
                print(' '.join(args[1:]))
            elif cmd == 'clear':
                if self.interactive:
                    print('\033[2J\033[H', end='', flush=True)
                else:
                    print('[screen cleared]')
            elif cmd == 'ls':
                if len(args) > 2:
                    print('ls: usage: ls [directory]')
                else:
                    path = args[1] if len(args) == 2 else '.'
                    for item in sorted(os.listdir(path)):
                        print(item)
            elif cmd == 'cat':
                if len(args) < 2:
                    print('cat: usage: cat filename [filename ...]')
                else:
                    for path in args[1:]:
                        with open(path, 'r', encoding='utf-8') as handle:
                            print(handle.read(), end='')
            elif cmd == 'mkdir':
                if len(args) != 2:
                    print('mkdir: usage: mkdir directory')
                else:
                    os.mkdir(args[1])
            elif cmd == 'rmdir':
                if len(args) != 2:
                    print('rmdir: usage: rmdir directory')
                else:
                    os.rmdir(args[1])
            elif cmd == 'rm':
                if len(args) != 2:
                    print('rm: usage: rm filename')
                else:
                    os.remove(args[1])
            elif cmd == 'touch':
                if len(args) != 2:
                    print('touch: usage: touch filename')
                else:
                    with open(args[1], 'a', encoding='utf-8'):
                        pass
                    os.utime(args[1], None)
            elif cmd == 'kill':
                if len(args) != 2:
                    print('kill: usage: kill pid')
                else:
                    pid = int(args[1]); os.kill(pid, signal.SIGTERM)
                    print(f'Sent SIGTERM to PID {pid}')
            elif cmd == 'jobs':
                self.report_finished()
                if not self.jobs:
                    print('No background jobs')
                for j in self.jobs.values():
                    print(f'[{j.number}] {j.state:<7} PID={j.process.pid} {j.command}')
            elif cmd == 'fg':
                if len(args) != 2:
                    print('fg: usage: fg job_id')
                    return True
                job = self.get_job(args[1])
                if job is None:
                    return True
                if job.process.poll() is not None:
                    print('fg: job has already finished')
                    return True
                if job.state == 'Stopped':
                    os.killpg(job.process.pid, signal.SIGCONT)
                job.state = 'Running'
                print(f'Foreground: [{job.number}] PID={job.process.pid} {job.command}', flush=True)
                self.wait_foreground(job.process, job)
            elif cmd == 'bg':
                if len(args) != 2:
                    print('bg: usage: bg job_id')
                    return True
                job = self.get_job(args[1])
                if job is None:
                    return True
                if job.process.poll() is not None:
                    print('bg: job has already finished')
                    return True
                if job.state == 'Stopped':
                    os.killpg(job.process.pid, signal.SIGCONT)
                    job.state = 'Running'
                    print(f'[{job.number}] Continued PID={job.process.pid}')
                else:
                    print(f'bg: job [{job.number}] is already running')
            else:
                return False
        except (OSError, UnicodeError, ValueError) as exc:
            print(f'{cmd}: {exc}')
        return True

    def wait_foreground(self, process, job=None):
        try:
            while process.poll() is None:
                # WUNTRACED detects an externally stopped process (SIGSTOP).
                pid, status = os.waitpid(process.pid, os.WNOHANG | os.WUNTRACED)
                if pid and os.WIFSTOPPED(status):
                    if job is None:
                        job = Job(self.next_job, process, 'foreground process', 'Stopped')
                        self.jobs[self.next_job] = job
                        self.next_job += 1
                    job.state = 'Stopped'
                    print(f'[{job.number}] Stopped PID={process.pid}')
                    return
                if pid and (os.WIFEXITED(status) or os.WIFSIGNALED(status)):
                    process.returncode = (os.waitstatus_to_exitcode(status))
                    break
                time.sleep(0.05)
        except KeyboardInterrupt:
            # Ctrl+C interrupts the foreground command, not the shell.
            try:
                os.killpg(process.pid, signal.SIGINT)
            except ProcessLookupError:
                pass
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                pass
            print('\nForeground process interrupted')
        if job and process.poll() is not None:
            job.state = 'Done'
        if process.poll() is not None:
            print(f'Process {process.pid} finished (exit {process.returncode})')

    def execute(self, line):
        try:
            args = shlex.split(line, posix=True)
        except ValueError as exc:
            print(f'shell: invalid input: {exc}')
            return
        if not args:
            return
        background = args[-1] == '&'
        if background:
            args.pop()
        if not args:
            print('shell: missing command before &')
            return
        if self.built_in(args):
            if background:
                print('shell: built-in commands execute in the shell (not backgrounded)')
            return
        program = shutil.which(args[0])
        if program is None:
            print(f'shell: command not found: {args[0]}')
            return
        try:
            process = subprocess.Popen(args, start_new_session=True)
        except OSError as exc:
            print(f'shell: could not start command: {exc}')
            return
        if background:
            number = self.next_job
            self.next_job += 1
            self.jobs[number] = Job(number, process, ' '.join(args))
            print(f'[{number}] PID={process.pid} started in background')
        else:
            print(f'Foreground PID={process.pid}: {" ".join(args)}', flush=True)
            self.wait_foreground(process)

    def run(self):
        print('Advanced Shell Simulator | type exit to quit')
        print('Built-ins: cd pwd exit echo clear ls cat mkdir rmdir rm touch kill jobs fg bg')
        while self.active:
            self.report_finished()
            try:
                prompt = f'shell:{os.path.basename(os.getcwd())}$ '
                line = input(prompt)
            except EOFError:
                print()
                break
            except KeyboardInterrupt:
                print()
                continue
            self.execute(line.strip())
        print('Shell closed')


if __name__ == '__main__':
    if os.name != 'posix':
        print('This shell requires Linux/macOS (POSIX signals and process groups).')
        sys.exit(1)
    Shell().run()
