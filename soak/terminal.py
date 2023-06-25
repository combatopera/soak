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
from lagoon import tput
import sys

class AbstractLog:

    stream = sys.stderr

    @innerclass
    class Section:

        height = 1

        def log(self, obj, rev = False, dark = False):
            self.obj = obj
            self.rev = rev
            self.dark = dark
            self.logsection(self)

    def addsection(self):
        return self.Section()

class Terminal(AbstractLog):

    @property
    def height(self):
        return sum(s.height for s in self.sections)

    def __init__(self):
        self.sections = {}

    def addsection(self):
        s = super().addsection()
        self.sections[s] = len(self.sections)
        self.stream.write('\n' * s.height)
        return s

    def _off(self, section):
        index = self.sections[section]
        return sum(s.height for s, i in self.sections.items() if i < index)

    def logsection(self, section):
        def g():
            dy = self.height - self._off(section)
            yield tput.cuu(dy)
            if section.rev:
                yield tput.rev()
            if section.dark:
                yield tput.setaf(0)
            yield str(section.obj)
            yield '\r'
            yield tput.sgr0()
            yield tput.cud(dy)
        self.stream.write(''.join(g()))
        self.stream.flush()

@singleton
class LogFile(AbstractLog):

    def logsection(self, section):
        if not section.dark:
            print('Damp:' if section.rev else 'Soaked:', section.obj, file = self.stream)
