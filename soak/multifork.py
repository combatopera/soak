# Copyright 2020 Andrzej Cichocki

# This file is part of soak.
#
# soak is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# soak is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with soak.  If not, see <http://www.gnu.org/licenses/>.

from base64 import b64decode, b64encode
from diapyr.util import invokeall
from functools import partial
from select import select
import os, pickle, sys

class GoodResult:

    def __init__(self, value):
        self.value = value

    def get(self):
        return self.value

class BadResult:

    def __init__(self, exception):
        self.exception = exception

    def get(self):
        raise self.exception

def _start(task, index):
    r1, w1 = os.pipe()
    r2, w2 = os.pipe()
    rx, wx = os.pipe()
    pid = os.fork()
    if pid:
        os.close(w1)
        os.close(w2)
        os.close(wx)
        return [pid, *map(os.fdopen, [r1, r2, rx])]
    os.close(r1)
    os.close(r2)
    os.close(rx)
    os.dup2(w1, 1)
    os.close(w1)
    os.dup2(w2, 2)
    os.close(w2)
    try:
        obj = GoodResult(task())
    except BaseException as e:
        obj = BadResult(e)
    os.write(wx, b64encode(pickle.dumps([index, obj])))
    sys.exit()

class Tasks:

    def __init__(self):
        self.waiting = []

    def add(self, task):
        self.waiting.append(task)

    def __len__(self):
        return len(self.waiting)

    def drain(self, limit):
        def report(task, line):
            index, obj = pickle.loads(b64decode(line))
            results[index] = obj.get
        pids = {}
        streams = {}
        running = {}
        results = [None] * len(self.waiting)
        while self.waiting or streams:
            while self.waiting and len(running) < limit:
                task = self.waiting.pop(0)
                pid, r1, r2, rx = _start(task, len(pids))
                pids[task] = pid
                streams[r1] = self.stdout, task
                streams[r2] = self.stderr, task
                streams[rx] = report, task
                running[task] = 3
                self.started(task)
            for r in select(streams, [], [])[0]:
                line = r.readline()
                if line:
                    partial(*streams[r])(line)
                else:
                    task = streams.pop(r)[1]
                    r.close()
                    ttl = running[task] - 1
                    if ttl:
                        running[task] = ttl
                    else:
                        running.pop(task)
                        os.waitpid(pids[task], 0)
                        self.stopped(task)
        return invokeall(results)

    def started(self, task):
        pass

    def stdout(self, task, line):
        pass

    def stderr(self, task, line):
        pass

    def stopped(self, task):
        pass
