"""Regression tests for Day 2 scheduling and retained Day 1 shell commands."""
import contextlib
import io
import os
import tempfile
import unittest
from scheduler import Scheduler
from myshell import Shell

class SchedulingTests(unittest.TestCase):
    def test_round_robin_order_and_metrics(self):
        s = Scheduler(); s.demo('rr')
        r = s.run('rr', quantum=2)
        self.assertEqual([x[2] for x in r['timeline']], ['P1','P1','P2','P2','P3','P3','P1','P1','P2','P1'])
        self.assertEqual({p['name']: p['completion'] for p in r['results']}, {'P1':10,'P2':9,'P3':6})
        self.assertEqual(r['averages']['waiting'], 13/3)
        self.assertEqual(r['averages']['turnaround'], 23/3)
        self.assertEqual(r['averages']['response'], 4/3)

    def test_priority_preemption_and_fcfs(self):
        s = Scheduler(); s.demo('priority')
        r = s.run('priority')
        self.assertIn('PREEMPT P1 -> P2', '\n'.join(r['events']))
        self.assertEqual([x[2] for x in r['timeline']], ['P1','P1','P2','P2','P2','P3','P3','P4','P4','P1','P1','P1','P1'])
        self.assertEqual({p['name']:p['completion'] for p in r['results']}, {'P1':13,'P2':5,'P3':7,'P4':9})

    def test_idle_and_validation(self):
        s = Scheduler(); s.add('late', 1, 1, 3)
        self.assertEqual(s.run('rr', 1)['total_time'], 4)
        with self.assertRaises(ValueError): s.run('rr', 0)
        with self.assertRaises(ValueError): s.add('late', 1, 1)
        with self.assertRaises(ValueError): s.add('bad', 0, 1)

    def test_shell_integration_and_day1(self):
        shell = Shell()
        with tempfile.TemporaryDirectory() as d:
            before = os.getcwd()
            try:
                os.chdir(d)
                with contextlib.redirect_stdout(io.StringIO()) as output:
                    for cmd in ['mkdir sample','cd sample','touch notes.txt','ls','cd ..','rm sample/notes.txt','rmdir sample',
                                'sched add A 2 1 0','sched add B 1 2 1','sched rr 1','sched priority','exit']:
                        shell.execute_line(cmd)
                self.assertIn('AVERAGES:', output.getvalue())
                self.assertIn('notes.txt', output.getvalue())
                self.assertFalse(os.path.exists('sample'))
            finally:
                os.chdir(before)

if __name__ == '__main__':
    unittest.main(verbosity=2)
