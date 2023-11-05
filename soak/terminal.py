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

    stream = sys.stderr

    def head(self, index, obj, rev = False, dark = False):
        return self.headimpl(index, obj, rev, dark)

class Terminal(AbstractLog):

    class Section:

        height = 0

    def __init__(self):
        self.sections = []

    def headimpl(self, index, obj, rev, dark):
        for _ in range(len(self.sections), index + 1):
            self.sections.append(self.Section())
        dy = sum(s.height for s in islice(self.sections, index + 1, None))
        section = self.sections[index]
        oldh = section.height
        section.height = newh = max(1, oldh)
        if dy:
            tput.cuu(dy, stdout = self.stream)
        if newh > oldh:
            tput.il(newh - oldh, stdout = self.stream)
        if oldh:
            tput.cuu(oldh, stdout = self.stream)
        if rev:
            tput.rev(stdout = self.stream)
        if dark:
            tput.setaf(0, stdout = self.stream)
        self.stream.write(f"{obj}{tput.sgr0()}\n")
        self.stream.write('\n' * (newh - 1 + dy))

    def log(self, index, stream, line):
        dy = sum(s.height for s in islice(self.sections, index + 1, None))
        section = self.sections[index]
        oldh = section.height
        section.height = newh = oldh + 1
        if dy:
            tput.cuu(dy, stdout = self.stream)
        if newh > oldh:
            tput.il(newh - oldh, stdout = self.stream)
        stream.write(line)
        self.stream.write('\n' * dy)

@singleton
class LogFile(AbstractLog):

    def headimpl(self, index, obj, rev, dark):
        if not dark:
            print('Damp:' if rev else 'Soaked:', obj, file = self.stream)

    def log(self, index, stream, line):
        stream.write(line)
