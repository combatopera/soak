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

class Terminal:

    def __init__(self, height):
        sys.stderr.write('\n' * height)
        self.height = height

    def log(self, index, text, rev = False, dark = False):
        def g():
            dy = self.height - index
            yield tput.cuu(dy)
            if rev:
                yield tput.rev()
            if dark:
                yield tput.setaf(0)
            yield str(text)
            yield '\r'
            yield tput.sgr0()
            yield tput.cud(dy)
        sys.stderr.write(''.join(g()))
        sys.stderr.flush()

@singleton
class LogFile:

    def log(self, index, text, rev = False, dark = False):
        if not dark:
            print('Damp:' if rev else 'Soaked:', text, file = sys.stderr)
