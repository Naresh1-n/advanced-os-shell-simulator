# Advanced Shell Simulation — Residency Day 2

**Course:** MSCS-630 Advanced Operating Systems  
**Group:** Naresh Landam, Nikitha Desam, Subhash Kalal

This project **extends the submitted Day 1 `myshell.py`** with a discrete-time CPU scheduling simulator. The existing shell built-ins and POSIX job control remain intact.

## Requirements
Python 3.10+ on Linux/macOS or Ubuntu under WSL. No third-party packages are needed to run the shell or tests.

## Run
```bash
python3 myshell.py
```
At the `myshell` prompt:
```text
sched demo rr
sched list
sched rr 2
sched rr 1 0.1
sched reset
sched demo priority
sched priority
```
To enter your own processes:
```text
sched reset
sched add A 6 3 0
sched add B 3 1 2
sched add C 2 1 2
sched priority 0.1
sched rr 2
```
Syntax:
- `sched add NAME BURST PRIORITY [ARRIVAL]` — positive integer burst; nonnegative integer arrival; **lower priority number means higher priority**.
- `sched rr QUANTUM [TICK_DELAY]` — round-robin; quantum positive integer, delay 0–2 real seconds per simulated tick.
- `sched priority [TICK_DELAY]` — preemptive priority; arrival/preemption decisions occur at simulated tick boundaries.
- `sched list`, `sched reset`, `sched demo rr`, `sched demo priority`.

A simulated process is a CPU-burst record; **it is not a real Linux process**. Day 1 commands such as `sleep 5 &`, `jobs`, `fg`, `bg`, and `kill` still operate on actual child processes separately.

## Metrics
For each process: turnaround = completion − arrival; waiting = turnaround − burst; response = first dispatch − arrival. All are **simulated time units**, not wall-clock measurements. Context switch overhead is assumed zero. Run `python3 test_scheduler.py` to verify correctness.

## Evidence
- `scheduling_demo_output.txt` is a captured execution transcript of the updated shell.
- `round_robin_evidence.png` and `priority_evidence.png` are **renderings of captured text output**, not screenshots of a graphical terminal. For an instructor requiring real terminal screenshots, run the commands above in Ubuntu and capture your terminal using Windows Snipping Tool.
- `test_results.txt` shows the automated tests.

## Files
- `myshell.py`: Day 1 shell extended with `sched` built-in.
- `scheduler.py`: Round-Robin and preemptive priority scheduling simulator.
- `test_scheduler.py`: automated regression and integration tests.
- `Residency_Day2_Deliverable2_Report.docx`: written report with analysis and evidence.
