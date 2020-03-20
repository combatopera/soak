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

from lagoon import tput
from threading import Lock
import sys

class Terminal:

    def __init__(self, height):
        sys.stderr.write('\n' * height)
        tput.sc(stdout = sys.stderr)
        self.lock = Lock()

    def log(self, upcount, text):
        with self.lock:
            tput.cuu(upcount, stdout = sys.stderr)
            print(text, file = sys.stderr)
            tput.sgr0(stdout = sys.stderr)
            tput.rc(stdout = sys.stderr)
            sys.stderr.flush()
