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

from diapyr.util import innerclass, singleton
from itertools import islice
from lagoon import tput
import sys

class AbstractLog:

    stream = sys.stderr

    @innerclass
    class Section:

        height = 1

        def __init__(self, index):
            self.index = index

        def log(self, obj, rev = False, dark = False):
            self.logsection(self.index, obj, rev, dark)

    def __init__(self):
        self.sections = []

    def addsection(self):
        s = self.Section(len(self.sections))
        self.sections.append(s)
        return s

class Terminal(AbstractLog):

    def addsection(self):
        s = super().addsection()
        self.stream.write('\n' * s.height)
        return s

    def logsection(self, index, obj, rev, dark):
        def g():
            dy = sum(s.height for s in islice(self.sections, index, None))
            yield tput.cuu(dy)
            if rev:
                yield tput.rev()
            if dark:
                yield tput.setaf(0)
            yield str(obj)
            yield '\r'
            yield tput.sgr0()
            yield tput.cud(dy)
        self.stream.write(''.join(g()))
        self.stream.flush()

@singleton
class LogFile(AbstractLog):

    def logsection(self, index, obj, rev, dark):
        if not dark:
            print('Damp:' if rev else 'Soaked:', obj, file = self.stream)
