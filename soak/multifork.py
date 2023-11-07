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

class Job:

    def __init__(self, task):
        self.task = task

class Tasks(list):

    def drain(self, limit):
        def report(task, line):
            index, obj = pickle.loads(b64decode(line))
            results[index] = obj.get
        pids = {}
        streams = {}
        running = {}
        results = [None] * len(self)
        while self or streams:
            while self and len(running) < limit:
                job = Job(self.pop(0))
                pid, r1, r2, rx = _start(job.task, len(pids))
                pids[job] = pid
                streams[r1] = job, self.stdout
                streams[r2] = job, self.stderr
                streams[rx] = job, report
                running[job] = 3
                self.started(job.task)
            for r in select(streams, [], [])[0]:
                line = r.readline()
                if line:
                    job, callback = streams[r]
                    callback(job.task, line)
                else:
                    job = streams.pop(r)[0]
                    r.close()
                    ttl = running[job] - 1
                    if ttl:
                        running[job] = ttl
                    else:
                        running.pop(job)
                        os.waitpid(pids[job], 0)
                        self.stopped(job.task)
        return invokeall(results)

    def started(self, task):
        pass

    def stdout(self, task, line):
        pass

    def stderr(self, task, line):
        pass

    def stopped(self, task):
        pass
