RESIDENCY DAY 1 — DELIVERABLE 1

DAY 1 LAUNCH CHECKLIST
[x] Choose Python and initialize a local Git repository.
[x] Prompt -> shlex parser -> built-in/external command loop.
[x] Implement built-in commands before adding job control.
[x] Define reusable Job record (number, process/PID, command, state).
[x] Provide a repeatable demo script and execution evidence.
[x] Explain process states: Running, Stopped, Done.

FILES
shell.py                  Interactive shell implementation
verify.py                 Repeatable checks and evidence logs
demo.py                   Repeatable instructor-friendly demonstration
demo_output.txt           Actual captured output of demo.py
Deliverable_1_Report.docx Written report with test evidence
*_screenshot.png          Rendered images of actual test logs
*_output.txt              Actual captured test logs

REQUIREMENTS
Python 3.9+ on Linux, macOS, or Windows Subsystem for Linux (WSL).

RUN
python3 shell.py
python3 demo.py
python3 verify.py

EXAMPLE INTERACTIVE COMMANDS
pwd
echo "Hello"
mkdir example
cd example
touch file.txt
ls
cat file.txt
cd ..
rm example/file.txt
rmdir example
sleep 5 &
jobs
fg 1
exit

JOB STATES
Running: child process has started and has not completed.
Stopped: child process was paused with SIGSTOP (demo simulates this).
Done: child process has exited or was terminated.
fg waits for a job; bg resumes a stopped job with SIGCONT.

REPOSITORY
A local Git repository was initialized in the project folder.
To publish on GitHub, create an empty repository in your own account,
then from this folder run:
  git remote add origin <YOUR_GITHUB_REPOSITORY_URL>
  git branch -M main
  git push -u origin main
Do not submit a fake GitHub link.

LIMITATIONS
Built-ins run in the shell process. External commands use POSIX subprocesses.
This is basic job control; full interactive terminal Ctrl+Z / tcsetpgrp
handoff is not implemented. The demo explicitly simulates SIGSTOP.
Screenshots are terminal-style images of real captured logs, not photographs
of a desktop terminal. Capture your own terminal screenshots if required.
