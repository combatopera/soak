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
import sys

class AbstractLog:

    def head(self, index, obj, rev = False, dark = False):
        return self.headimpl(index, obj, rev, dark)

class Terminal(AbstractLog):

    class Section:

        height = 0

    def __init__(self):
        self.width = int(tput.cols())
        self.sections = []

    def headimpl(self, index, obj, rev, dark):
        for _ in range(len(self.sections), index + 1):
            self.sections.append(self.Section())
        dy = sum(s.height for s in islice(self.sections, index + 1, None))
        section = self.sections[index]
        oldh = section.height
        section.height = newh = max(1, oldh)
        if dy:
            tput.cuu(dy, stdout = sys.stderr)
        if newh > oldh:
            tput.il(newh - oldh, stdout = sys.stderr)
        if oldh:
            tput.cuu(oldh, stdout = sys.stderr)
        if rev:
            tput.rev(stdout = sys.stderr)
        if dark:
            tput.setaf(0, stdout = sys.stderr)
        sys.stderr.write(f"{obj}{tput.sgr0()}\n")
        sys.stderr.write('\n' * (newh - 1 + dy))

    def log(self, index, stream, line):
        dy = sum(s.height for s in islice(self.sections, index + 1, None))
        section = self.sections[index]
        oldh = section.height
        section.height = newh = oldh + 1
        if dy:
            tput.cuu(dy, stdout = sys.stderr)
        if newh > oldh:
            tput.il(newh - oldh, stdout = sys.stderr)
        obj, = line.splitlines()
        if len(obj) > self.width:
            obj = f"{obj[:self.width - 1]}\N{HORIZONTAL ELLIPSIS}"
        stream.write(f"{obj}\n")
        sys.stderr.write('\n' * dy)

@singleton
class LogFile(AbstractLog):

    def headimpl(self, index, obj, rev, dark):
        if not dark:
            print('Damp:' if rev else 'Soaked:', obj, file = sys.stderr)

    def log(self, index, stream, line):
        stream.write(line)
