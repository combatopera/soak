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

from diapyr.util import singleton
from itertools import islice
from lagoon import tput
from threading import Lock
import sys

class AbstractLog:

    stream = sys.stderr

    def log(self, index, obj, rev = False, dark = False):
        return self.logimpl(index, obj, rev, dark)

class Terminal(AbstractLog):

    class Section:

        height = 0

    def __init__(self):
        self.lock = Lock()
        self.sections = []

    def logimpl(self, index, obj, rev, dark):
        def g():
            if dy:
                yield tput.cuu(dy)
            if newh > h:
                yield tput.il(newh - h)
            if h:
                yield tput.cuu(h)
            if rev:
                yield tput.rev()
            if dark:
                yield tput.setaf(0)
            yield f"{obj}{tput.sgr0()}\n"
            yield '\n' * dy
        with self.lock:
            for _ in range(len(self.sections), index + 1):
                self.sections.append(self.Section())
            section = self.sections[index]
            newh = 1
            h = section.height
            dy = sum(s.height for s in islice(self.sections, index + 1, None))
            section.height = newh
            self.stream.write(''.join(g()))

@singleton
class LogFile(AbstractLog):

    def logimpl(self, index, obj, rev, dark):
        if not dark:
            print('Damp:' if rev else 'Soaked:', obj, file = self.stream)
