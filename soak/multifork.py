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
from tblib import Traceback
import os, pickle, sys

class GoodResult:

    def __init__(self, value):
        self.value = value

    def get(self):
        return self.value

class BadResult:

    @classmethod
    def _of(cls, *args):
        return cls(*args)

    def __init__(self, exception):
        self.exception = exception

    def __getstate__(self):
        c = self.exception.__context__
        return dict(
            context = None if c is None else self._of(c),
            exception = self.exception,
            tb = Traceback(self.exception.__traceback__),
        )

    def __setstate__(self, state):
        self.exception = e = state['exception']
        c = state['context']
        e.__context__ = None if c is None else c.exception
        e.__traceback__ = state['tb'].as_traceback()

    def get(self):
        raise self.exception

class Job:

    ttl = 3

    def __init__(self, index, task):
        self.index = index
        self.task = task

    def start(self):
        r1, w1 = os.pipe()
        r2, w2 = os.pipe()
        rx, wx = os.pipe()
        pid = os.fork()
        if pid:
            os.close(w1)
            os.close(w2)
            os.close(wx)
            self.pid = pid
            return map(os.fdopen, [r1, r2, rx])
        os.close(r1)
        os.close(r2)
        os.close(rx)
        os.dup2(w1, 1)
        os.close(w1)
        os.dup2(w2, 2)
        os.close(w2)
        try:
            obj = GoodResult(self.task())
            code = 0
        except BaseException as e:
            obj = BadResult(e)
            code = 1
        os.write(wx, b64encode(pickle.dumps([self.index, obj])))
        sys.exit(code)

    def decr(self):
        self.ttl = ttl = self.ttl - 1
        if not ttl:
            s = os.waitpid(self.pid, 0)[1]
            return -os.WTERMSIG(s) if os.WIFSIGNALED(s) else os.WEXITSTATUS(s)

class Tasks(list):

    def drain(self, limit):
        def report(task, line):
            index, obj = pickle.loads(b64decode(line))
            results[index] = obj.get
        streams = {}
        running = 0
        results = [None] * len(self)
        while self or streams:
            while self and running < limit:
                job = Job(len(results) - len(self), self.pop(0))
                r1, r2, rx = job.start()
                streams[r1] = job, self.stdout
                streams[r2] = job, self.stderr
                streams[rx] = job, report
                running += 1
                self.started(job.task)
            for r in select(streams, [], [])[0]:
                line = r.readline()
                if line:
                    job, callback = streams[r]
                    callback(job.task, line)
                else:
                    job = streams.pop(r)[0]
                    r.close()
                    code = job.decr()
                    if code is not None:
                        running -= 1
                        self.stopped(job.task, code)
        return invokeall(results)

    def started(self, task):
        pass

    def stdout(self, task, line):
        pass

    def stderr(self, task, line):
        pass

    def stopped(self, task, code):
        pass
