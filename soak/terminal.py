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

class Terminal(AbstractLog):

    def __init__(self, height):
        self.stream.write('\n' * height)
        self.height = height

    def log(self, index, obj, rev = False, dark = False):
        def g():
            dy = self.height - index
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

    def log(self, index, obj, rev = False, dark = False):
        if not dark:
            print('Damp:' if rev else 'Soaked:', obj, file = self.stream)
