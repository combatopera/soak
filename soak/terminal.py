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
from lagoon import tput
import sys

class AbstractLog:

    stream = sys.stderr

    def log(self, section, obj, rev = False, dark = False):
        return self.logimpl(section, obj, rev, dark)

class Terminal(AbstractLog):

    @property
    def height(self):
        return sum(s.height for s in self.sections)

    def __init__(self, sections):
        self.sections = {s: i for i, s in enumerate(sections)}
        self.stream.write('\n' * self.height)

    def _off(self, section):
        index = self.sections[section]
        return sum(s.height for s, i in self.sections.items() if i < index)

    def logimpl(self, section, obj, rev, dark):
        def g():
            dy = self.height - self._off(section)
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

    def logimpl(self, section, obj, rev, dark):
        if not dark:
            print('Damp:' if rev else 'Soaked:', obj, file = self.stream)

class Section:

    height = 1
