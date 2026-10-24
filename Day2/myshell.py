#!/usr/bin/env python3
"""
myshell.py - Advanced Shell Simulation, Deliverables 1 and 2
Basic shell implementation with built-in commands, foreground/background
process execution, and job control (jobs, fg, bg, stop, kill).

Requires a Unix-like OS (Linux, macOS, or WSL on Windows) because it uses
POSIX process groups and signals (SIGSTOP, SIGCONT, SIGTSTP).

Run:  python3 myshell.py
"""

import os
import shlex
import signal
import stat
import subprocess
import sys
import time
from datetime import datetime
from scheduler import Scheduler, format_result

# Job states
RUNNING = "Running"
STOPPED = "Stopped"
DONE = "Done"


class Job:
    """A process launched by the shell and tracked for job control."""

    def __init__(self, job_id, process, command):
        self.job_id = job_id
        self.process = process          # subprocess.Popen object
        self.pid = process.pid
        self.command = command
        self.status = RUNNING
        self.exit_code = None
        self.started = time.time()

    def __str__(self):
        return f"[{self.job_id}] {self.pid:<7} {self.status:<8} {self.command}"


class Shell:
    def __init__(self):
        self.jobs = {}               # job_id -> Job
        self.fg_job = None           # job currently in the foreground
        self.running = True
        self.last_status = 0
        self.scheduler = Scheduler()

        self.builtins = {
            "cd": self.cmd_cd,
            "pwd": self.cmd_pwd,
            "exit": self.cmd_exit,
            "echo": self.cmd_echo,
            "clear": self.cmd_clear,
            "ls": self.cmd_ls,
            "cat": self.cmd_cat,
            "mkdir": self.cmd_mkdir,
            "rmdir": self.cmd_rmdir,
            "rm": self.cmd_rm,
            "touch": self.cmd_touch,
            "kill": self.cmd_kill,
            "jobs": self.cmd_jobs,
            "fg": self.cmd_fg,
            "bg": self.cmd_bg,
            "stop": self.cmd_stop,
            "help": self.cmd_help,
            "sched": self.cmd_sched,
        }

        # The shell itself ignores Ctrl+C and Ctrl+Z; they are forwarded
        # to the foreground job instead, so the shell keeps running.
        signal.signal(signal.SIGINT, self.handle_sigint)
        signal.signal(signal.SIGTSTP, self.handle_sigtstp)

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------
    def prompt(self):
        cwd = os.getcwd()
        home = os.path.expanduser("~")
        if cwd.startswith(home):
            cwd = "~" + cwd[len(home):]
        return f"myshell:{cwd}$ "

    def run(self):
        print("Welcome to myshell. Type 'help' for a list of commands.")
        while self.running:
            self.reap_jobs()
            try:
                line = input(self.prompt())
            except EOFError:
                print()
                self.cmd_exit([])
                break
            except KeyboardInterrupt:
                print()
                continue
            self.execute_line(line)

    def execute_line(self, line):
        line = line.strip()
        if not line or line.startswith("#"):
            return

        background = False
        if line.endswith("&"):
            background = True
            line = line[:-1].strip()
            if not line:
                self.error("syntax error near '&'")
                return

        try:
            args = shlex.split(line)
        except ValueError as e:
            self.error(f"parse error: {e}")
            return

        name = args[0]
        if name in self.builtins:
            if background:
                self.error(f"{name}: built-in commands cannot run in the background")
                return
            try:
                self.last_status = self.builtins[name](args[1:]) or 0
            except Exception as e:  # last line of defence: never crash the shell
                self.error(f"{name}: {e}")
                self.last_status = 1
        else:
            self.launch(args, line, background)

    # ------------------------------------------------------------------
    # Process creation and job control
    # ------------------------------------------------------------------
    def launch(self, args, command_text, background):
        """Create a new process for an external command (fork + exec)."""
        try:
            # Popen performs fork() + exec() internally. start_new_session
            # places the child in its own process group so job-control
            # signals reach it without affecting the shell.
            proc = subprocess.Popen(args, start_new_session=True)
        except FileNotFoundError:
            self.error(f"{args[0]}: command not found")
            self.last_status = 127
            return
        except PermissionError:
            self.error(f"{args[0]}: permission denied")
            self.last_status = 126
            return
        except OSError as e:
            self.error(f"{args[0]}: {e.strerror}")
            self.last_status = 1
            return

        # Like bash, job numbers restart from 1 when no jobs are active.
        job_id = max(self.jobs) + 1 if self.jobs else 1
        job = Job(job_id, proc, command_text)
        self.jobs[job.job_id] = job

        if background:
            print(f"[{job.job_id}] {job.pid}")
        else:
            self.wait_foreground(job)

    def wait_foreground(self, job):
        """Wait for a foreground job to finish or stop (like wait())."""
        self.fg_job = job
        while True:
            try:
                pid, status = os.waitpid(job.pid, os.WUNTRACED)
            except ChildProcessError:
                job.status = DONE
                break
            except InterruptedError:
                continue
            if os.WIFSTOPPED(status):
                job.status = STOPPED
                print(f"\n{job}")
                break
            if os.WIFEXITED(status) or os.WIFSIGNALED(status):
                job.status = DONE
                job.exit_code = (os.WEXITSTATUS(status) if os.WIFEXITED(status)
                                 else -os.WTERMSIG(status))
                job.process.returncode = job.exit_code
                self.last_status = job.exit_code
                if os.WIFSIGNALED(status) and os.WTERMSIG(status) == signal.SIGINT:
                    print()   # move the prompt off the ^C line
                break
        self.fg_job = None
        if job.status == DONE:
            del self.jobs[job.job_id]

    def reap_jobs(self):
        """Check background jobs without blocking and report changes."""
        for job in list(self.jobs.values()):
            try:
                pid, status = os.waitpid(job.pid, os.WNOHANG | os.WUNTRACED
                                         | os.WCONTINUED)
            except ChildProcessError:
                pid, status = job.pid, 0
                job.status = DONE
            if pid == 0:
                continue
            if os.WIFSTOPPED(status):
                job.status = STOPPED
            elif os.WIFCONTINUED(status):
                job.status = RUNNING
            elif os.WIFEXITED(status) or os.WIFSIGNALED(status):
                job.status = DONE
                job.exit_code = (os.WEXITSTATUS(status) if os.WIFEXITED(status)
                                 else -os.WTERMSIG(status))
                job.process.returncode = job.exit_code
            if job.status == DONE:
                print(f"{job}  (exit code {job.exit_code})")
                del self.jobs[job.job_id]

    def get_job(self, args, command):
        """Find a job from a job id argument, or the most recent job."""
        if not self.jobs:
            self.error(f"{command}: no current jobs")
            return None
        if not args:
            return self.jobs[max(self.jobs)]
        ref = args[0].lstrip("%")
        if not ref.isdigit():
            self.error(f"{command}: invalid job id '{args[0]}'")
            return None
        job = self.jobs.get(int(ref))
        if job is None:
            self.error(f"{command}: job {ref} not found")
        return job

    def handle_sigint(self, signum, frame):
        if self.fg_job:
            os.killpg(self.fg_job.pid, signal.SIGINT)
        else:
            raise KeyboardInterrupt

    def handle_sigtstp(self, signum, frame):
        # The child runs in its own session, so the kernel would discard a
        # forwarded SIGTSTP (orphaned process group). SIGSTOP cannot be
        # ignored or discarded, so it reliably suspends the job.
        if self.fg_job:
            os.killpg(self.fg_job.pid, signal.SIGSTOP)

    # ------------------------------------------------------------------
    # Built-in commands
    # ------------------------------------------------------------------
    def error(self, message):
        print(f"myshell: {message}", file=sys.stderr)

    def cmd_cd(self, args):
        target = args[0] if args else os.path.expanduser("~")
        target = os.path.expanduser(target)
        try:
            os.chdir(target)
        except FileNotFoundError:
            self.error(f"cd: {target}: no such directory")
            return 1
        except NotADirectoryError:
            self.error(f"cd: {target}: not a directory")
            return 1
        except PermissionError:
            self.error(f"cd: {target}: permission denied")
            return 1
        return 0

    def cmd_pwd(self, args):
        print(os.getcwd())
        return 0

    def cmd_exit(self, args):
        if self.jobs:
            print(f"Terminating {len(self.jobs)} remaining job(s)...")
            for job in self.jobs.values():
                try:
                    os.killpg(job.pid, signal.SIGCONT)
                    os.killpg(job.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
        print("Goodbye.")
        self.running = False
        return 0

    def cmd_echo(self, args):
        print(" ".join(args))
        return 0

    def cmd_clear(self, args):
        os.system("cls" if os.name == "nt" else "clear")
        return 0

    def cmd_ls(self, args):
        show_all = "-a" in args
        long = "-l" in args
        paths = [a for a in args if not a.startswith("-")] or ["."]
        status = 0
        for path in paths:
            try:
                entries = sorted(os.listdir(path))
            except FileNotFoundError:
                self.error(f"ls: {path}: no such file or directory")
                status = 1
                continue
            except NotADirectoryError:
                print(path)
                continue
            except PermissionError:
                self.error(f"ls: {path}: permission denied")
                status = 1
                continue
            if not show_all:
                entries = [e for e in entries if not e.startswith(".")]
            for name in entries:
                full = os.path.join(path, name)
                if long:
                    info = os.lstat(full)
                    mode = stat.filemode(info.st_mode)
                    mtime = datetime.fromtimestamp(info.st_mtime).strftime("%b %d %H:%M")
                    print(f"{mode} {info.st_size:>8} {mtime} {name}")
                else:
                    suffix = "/" if os.path.isdir(full) else ""
                    print(name + suffix)
        return status

    def cmd_cat(self, args):
        if not args:
            self.error("cat: missing file operand")
            return 1
        status = 0
        for name in args:
            try:
                with open(name, "r", errors="replace") as f:
                    sys.stdout.write(f.read())
            except FileNotFoundError:
                self.error(f"cat: {name}: no such file")
                status = 1
            except IsADirectoryError:
                self.error(f"cat: {name}: is a directory")
                status = 1
            except PermissionError:
                self.error(f"cat: {name}: permission denied")
                status = 1
        sys.stdout.flush()
        return status

    def cmd_mkdir(self, args):
        if not args:
            self.error("mkdir: missing directory operand")
            return 1
        status = 0
        for name in args:
            try:
                os.mkdir(name)
            except FileExistsError:
                self.error(f"mkdir: {name}: already exists")
                status = 1
            except FileNotFoundError:
                self.error(f"mkdir: {name}: parent directory does not exist")
                status = 1
            except PermissionError:
                self.error(f"mkdir: {name}: permission denied")
                status = 1
        return status

    def cmd_rmdir(self, args):
        if not args:
            self.error("rmdir: missing directory operand")
            return 1
        status = 0
        for name in args:
            try:
                os.rmdir(name)
            except FileNotFoundError:
                self.error(f"rmdir: {name}: no such directory")
                status = 1
            except NotADirectoryError:
                self.error(f"rmdir: {name}: not a directory")
                status = 1
            except OSError:
                self.error(f"rmdir: {name}: directory not empty")
                status = 1
        return status

    def cmd_rm(self, args):
        if not args:
            self.error("rm: missing file operand")
            return 1
        status = 0
        for name in args:
            if os.path.isdir(name):
                self.error(f"rm: {name}: is a directory (use rmdir)")
                status = 1
                continue
            try:
                os.remove(name)
            except FileNotFoundError:
                self.error(f"rm: {name}: no such file")
                status = 1
            except PermissionError:
                self.error(f"rm: {name}: permission denied")
                status = 1
        return status

    def cmd_touch(self, args):
        if not args:
            self.error("touch: missing file operand")
            return 1
        status = 0
        for name in args:
            try:
                with open(name, "a"):
                    os.utime(name, None)   # update timestamp if it exists
            except IsADirectoryError:
                os.utime(name, None)
            except (FileNotFoundError, PermissionError) as e:
                self.error(f"touch: {name}: {e.strerror}")
                status = 1
        return status

    def cmd_kill(self, args):
        if not args:
            self.error("kill: usage: kill [pid | %job_id]")
            return 1
        status = 0
        for target in args:
            if target.startswith("%"):
                job = self.get_job([target], "kill")
                if job is None:
                    status = 1
                    continue
                pid = job.pid
            elif target.isdigit():
                pid = int(target)
            else:
                self.error(f"kill: {target}: invalid process id")
                status = 1
                continue
            try:
                os.kill(pid, signal.SIGTERM)
                # Wake a stopped process so it can receive SIGTERM.
                os.kill(pid, signal.SIGCONT)
                print(f"Sent SIGTERM to process {pid}")
            except ProcessLookupError:
                self.error(f"kill: ({pid}) - no such process")
                status = 1
            except PermissionError:
                self.error(f"kill: ({pid}) - operation not permitted")
                status = 1
        time.sleep(0.1)
        self.reap_jobs()
        return status

    def cmd_jobs(self, args):
        self.reap_jobs()
        if not self.jobs:
            print("No background jobs.")
            return 0
        print(f"{'JOB':<4}{'PID':<8}{'STATUS':<9}COMMAND")
        for job in sorted(self.jobs.values(), key=lambda j: j.job_id):
            print(job)
        return 0

    def cmd_fg(self, args):
        job = self.get_job(args, "fg")
        if job is None:
            return 1
        print(job.command)
        if job.status == STOPPED:
            os.killpg(job.pid, signal.SIGCONT)
        job.status = RUNNING
        self.wait_foreground(job)
        return 0

    def cmd_bg(self, args):
        job = self.get_job(args, "bg")
        if job is None:
            return 1
        if job.status == RUNNING:
            self.error(f"bg: job {job.job_id} is already running in the background")
            return 1
        os.killpg(job.pid, signal.SIGCONT)
        job.status = RUNNING
        print(f"[{job.job_id}] {job.command} &")
        return 0

    def cmd_stop(self, args):
        """Stop (suspend) a background job, same effect as Ctrl+Z."""
        job = self.get_job(args, "stop")
        if job is None:
            return 1
        if job.status == STOPPED:
            self.error(f"stop: job {job.job_id} is already stopped")
            return 1
        os.killpg(job.pid, signal.SIGSTOP)
        job.status = STOPPED
        print(job)
        return 0

    def cmd_sched(self, args):
        """Manage simulated CPU bursts; does not schedule real OS processes."""
        usage = ("sched add NAME BURST PRIORITY [ARRIVAL] | sched list | sched reset | "
                 "sched demo rr|priority | sched rr QUANTUM [TICK_DELAY] | "
                 "sched priority [TICK_DELAY]")
        if not args:
            print(usage)
            return 0
        try:
            sub = args[0]
            if sub == "add" and len(args) in (4, 5):
                self.scheduler.add(args[1], int(args[2]), int(args[3]),
                                   int(args[4]) if len(args) == 5 else 0)
                print(f"Added simulated process {args[1]}")
            elif sub == "list" and len(args) == 1:
                if not self.scheduler.specs:
                    print("No simulated processes queued.")
                for name, burst, priority, arrival in self.scheduler.specs:
                    print(f"{name}: burst={burst}, priority={priority}, arrival={arrival}")
            elif sub == "reset" and len(args) == 1:
                self.scheduler.reset()
                print("Simulated queue cleared.")
            elif sub == "demo" and len(args) == 2 and args[1] in ("rr", "priority"):
                self.scheduler.demo(args[1])
                print(f"Loaded {args[1]} demonstration workload. Use sched list to inspect it.")
            elif sub == "rr" and len(args) in (2, 3):
                result = self.scheduler.run('rr', quantum=int(args[1]),
                                            tick_seconds=float(args[2]) if len(args) == 3 else 0.0)
                print(format_result(result))
            elif sub == "priority" and len(args) in (1, 2):
                result = self.scheduler.run('priority',
                                            tick_seconds=float(args[1]) if len(args) == 2 else 0.0)
                print(format_result(result))
            else:
                self.error(f"usage: {usage}")
                return 1
        except (ValueError, OverflowError) as exc:
            self.error(f"sched: {exc}")
            return 1
        return 0

    def cmd_help(self, args):
        print("""Built-in commands:
  cd [dir]        change directory           pwd            print working directory
  echo [text]     print text                 clear          clear the screen
  ls [-a] [-l]    list files                 cat [file]     display a file
  mkdir [dir]     create a directory         rmdir [dir]    remove an empty directory
  rm [file]       remove a file              touch [file]   create/update a file
  kill [pid|%id]  terminate a process        exit           quit the shell
Job control:
  command &       run in background          jobs           list jobs
  fg [id]         bring job to foreground    bg [id]        resume stopped job in background
  stop [id]       stop (suspend) a job       Ctrl+Z         stop the foreground job
CPU scheduling simulator:
  sched add NAME BURST PRIORITY [ARRIVAL]   add simulated process
  sched list | sched reset                 inspect/clear simulation queue
  sched demo rr|priority                   load example workload
  sched rr QUANTUM [TICK_DELAY]            round robin scheduling
  sched priority [TICK_DELAY]              preemptive priority scheduling
  Priority 1 is higher than priority 2; time is measured in simulated ticks.
Any other command (e.g. sleep 10, python3 script.py) runs as an external process.""")
        return 0


if __name__ == "__main__":
    if os.name == "nt":
        print("myshell requires Linux, macOS, or WSL (POSIX signals).")
        sys.exit(1)
    Shell().run()
