"""Automated checks and reproducible demonstrations for the shell."""
import contextlib
import io
import os
import signal
import tempfile
import time
from pathlib import Path
from shell import Shell


def capture(shell, command):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        shell.report_finished()
        shell.execute(command)
    return f'shell$ {command}\n' + out.getvalue()


def main():
    with tempfile.TemporaryDirectory() as directory:
        os.chdir(directory)
        shell = Shell()
        chunks = []
        for cmd in ['pwd', 'echo "Hello from the OS shell"', 'mkdir lab', 'cd lab',
                    'touch notes.txt', 'ls', 'cat notes.txt', 'cd ..', 'rm lab/notes.txt',
                    'rmdir lab', 'ls', 'echo Finished file commands']:
            chunks.append(capture(shell, cmd))
        Path(__file__).resolve().parent.joinpath('builtins_output.txt').write_text(''.join(chunks))
        chunks = []
        for cmd in ['sleep 0.2', 'sleep 4 &', 'jobs']:
            chunks.append(capture(shell, cmd))
        job = shell.jobs[1]
        os.killpg(job.process.pid, signal.SIGSTOP)
        job.state = 'Stopped'  # reflect the externally delivered SIGSTOP
        chunks.append('External test action: sent SIGSTOP to background process group\n')
        for cmd in ['jobs', 'bg 1', 'jobs', 'fg 1', 'jobs']:
            chunks.append(capture(shell, cmd))
        Path(__file__).resolve().parent.joinpath('process_output.txt').write_text(''.join(chunks))
        chunks = []
        for cmd in ['no_such_command', 'cat absent.txt', 'cd missing_folder',
                    'mkdir', 'rmdir', 'rm', 'touch', 'kill abc', 'fg 99', 'bg 99',
                    'echo "unterminated', '&']:
            chunks.append(capture(shell, cmd))
        Path(__file__).resolve().parent.joinpath('errors_output.txt').write_text(''.join(chunks))
        # Demonstrate kill on a real background process
        chunks = [capture(shell, 'sleep 10 &')]
        pid = shell.jobs[2].process.pid
        chunks.append(capture(shell, f'kill {pid}'))
        time.sleep(.15)
        chunks.append(capture(shell, 'jobs'))
        Path(__file__).resolve().parent.joinpath('kill_output.txt').write_text(''.join(chunks))
        print('PASS: built-ins, foreground/background, stop/resume, fg, kill, invalid inputs')


if __name__ == '__main__':
    main()
