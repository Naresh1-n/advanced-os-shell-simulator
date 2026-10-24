"""Discrete-time CPU scheduling simulation used by myshell.py.

Each process represents a *simulated* CPU burst, not an OS child process.
One tick is one simulated time unit. Optional sleep slows the demonstration.
Lower numeric priority = higher priority. Equal priorities use arrival/ID FCFS.
"""
from collections import deque
from dataclasses import dataclass
import heapq
import time


@dataclass
class SimProcess:
    name: str
    burst: int
    priority: int
    arrival: int
    sequence: int
    remaining: int = 0
    first_start: int | None = None
    completion: int | None = None

    def __post_init__(self):
        self.remaining = self.burst


class Scheduler:
    def __init__(self):
        self.specs = []

    def add(self, name, burst, priority, arrival=0):
        if not name or any(p[0] == name for p in self.specs):
            raise ValueError('process name must be nonempty and unique')
        if burst <= 0 or arrival < 0:
            raise ValueError('burst must be positive and arrival must be nonnegative')
        self.specs.append((name, burst, priority, arrival))

    def reset(self):
        self.specs.clear()

    def demo(self, algorithm):
        self.reset()
        if algorithm == 'rr':
            for row in [('P1', 5, 3, 0), ('P2', 3, 2, 0), ('P3', 2, 1, 2)]:
                self.add(*row)
        else:
            for row in [('P1', 6, 3, 0), ('P2', 3, 1, 2), ('P3', 2, 1, 2), ('P4', 2, 2, 4)]:
                self.add(*row)

    def run(self, algorithm, quantum=2, tick_seconds=0.0):
        if algorithm not in ('rr', 'priority'):
            raise ValueError('algorithm must be rr or priority')
        if not self.specs:
            raise ValueError('queue is empty: use sched add or sched demo')
        if quantum <= 0:
            raise ValueError('quantum must be positive')
        if tick_seconds < 0 or tick_seconds > 2:
            raise ValueError('tick delay must be between 0 and 2 seconds')

        processes = [SimProcess(*spec, sequence=i) for i, spec in enumerate(self.specs)]
        arrivals = sorted(processes, key=lambda p: (p.arrival, p.sequence))
        pending = 0
        clock = 0
        completed = 0
        events = []
        timeline = []
        rr_ready = deque()
        priority_ready = []
        current = None
        slice_used = 0

        def enqueue_arrivals():
            nonlocal pending
            while pending < len(arrivals) and arrivals[pending].arrival <= clock:
                p = arrivals[pending]
                pending += 1
                if algorithm == 'rr':
                    rr_ready.append(p)
                else:
                    heapq.heappush(priority_ready, (p.priority, p.arrival, p.sequence, p))
                events.append(f't={clock:>2} ARRIVE {p.name} burst={p.burst} priority={p.priority}')

        while completed < len(processes):
            enqueue_arrivals()
            if algorithm == 'priority':
                if current and priority_ready and priority_ready[0][0] < current.priority:
                    events.append(f't={clock:>2} PREEMPT {current.name} -> {priority_ready[0][3].name} (higher priority)')
                    heapq.heappush(priority_ready, (current.priority, current.arrival, current.sequence, current))
                    current = None
                if current is None and priority_ready:
                    current = heapq.heappop(priority_ready)[3]
                    events.append(f't={clock:>2} DISPATCH {current.name} priority={current.priority}')
            else:
                if current is None and rr_ready:
                    current = rr_ready.popleft()
                    slice_used = 0
                    events.append(f't={clock:>2} DISPATCH {current.name} quantum={quantum}')

            if current is None:
                timeline.append((clock, clock + 1, 'IDLE'))
                events.append(f't={clock:>2} IDLE')
                time.sleep(tick_seconds)
                clock += 1
                continue

            if current.first_start is None:
                current.first_start = clock
            timeline.append((clock, clock + 1, current.name))
            events.append(f't={clock:>2}-{clock + 1:<2} RUN {current.name} remaining {current.remaining}->{current.remaining - 1}')
            time.sleep(tick_seconds)
            current.remaining -= 1
            clock += 1
            slice_used += 1
            if current.remaining == 0:
                current.completion = clock
                events.append(f't={clock:>2} FINISH {current.name}')
                current = None
                completed += 1
            elif algorithm == 'rr' and slice_used >= quantum:
                # At a quantum boundary, newly arrived processes enter first.
                enqueue_arrivals()
                rr_ready.append(current)
                events.append(f't={clock:>2} QUANTUM EXPIRED {current.name}; move to back of queue')
                current = None

        results = []
        for p in processes:
            turnaround = p.completion - p.arrival
            waiting = turnaround - p.burst
            response = p.first_start - p.arrival
            results.append(dict(name=p.name, arrival=p.arrival, burst=p.burst,
                                priority=p.priority, completion=p.completion,
                                waiting=waiting, turnaround=turnaround, response=response))
        return dict(algorithm=algorithm, quantum=quantum, events=events,
                    timeline=timeline, results=results, total_time=clock,
                    averages={key: sum(r[key] for r in results) / len(results)
                              for key in ('waiting', 'turnaround', 'response')})


def format_result(result):
    lines = [f'=== {"ROUND ROBIN" if result["algorithm"] == "rr" else "PREEMPTIVE PRIORITY"} ===']
    if result['algorithm'] == 'rr':
        lines.append(f'Time quantum: {result["quantum"]} simulated units')
    lines.extend(result['events'])
    lines.append('\nGANTT TIMELINE (simulated units)')
    lines.append(' | '.join(f'{start}-{end}:{name}' for start, end, name in result['timeline']))
    lines.append('\nPROCESS METRICS')
    lines.append(f'{"Name":<8}{"Arrive":>7}{"Burst":>7}{"Prio":>7}{"Finish":>8}{"Wait":>7}{"Turn":>7}{"Resp":>7}')
    for p in result['results']:
        lines.append(f'{p["name"]:<8}{p["arrival"]:>7}{p["burst"]:>7}{p["priority"]:>7}{p["completion"]:>8}{p["waiting"]:>7}{p["turnaround"]:>7}{p["response"]:>7}')
    a = result['averages']
    lines.append(f'AVERAGES: waiting={a["waiting"]:.2f}, turnaround={a["turnaround"]:.2f}, response={a["response"]:.2f} simulated units')
    return '\n'.join(lines)
