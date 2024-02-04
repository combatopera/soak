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
from subprocess import CalledProcessError
import sys

class Style:

    pending = object()
    running = object()
    normal = object()
    abrupt = object()

class Terminal:

    class Section:

        height = 0

    def __init__(self, width):
        self.sections = []
        self.width = width

    def _common(self, index, tonewh):
        dy = sum(s.height for s in islice(self.sections, index + 1, None))
        section = self.sections[index]
        oldh = section.height
        section.height = newh = tonewh(oldh)
        if dy:
            tput.cuu(dy, stdout = sys.stderr)
        if newh > oldh:
            tput.il(newh - oldh, stdout = sys.stderr)
        return dy, oldh, newh

    def head(self, index, obj, style):
        for _ in range(len(self.sections), index + 1):
            self.sections.append(self.Section())
        dy, oldh, newh = self._common(index, lambda h: max(1, h))
        if oldh:
            tput.cuu(oldh, stdout = sys.stderr)
        if Style.pending == style:
            tput.setaf(0, stdout = sys.stderr)
        elif Style.running == style:
            tput.rev(stdout = sys.stderr)
        elif Style.abrupt == style:
            tput.setab(1, stdout = sys.stderr)
            tput.setaf(7, stdout = sys.stderr)
        sys.stderr.write(f"[{obj}]{tput.sgr0()}\n")
        sys.stderr.write('\n' * (newh - 1 + dy))

    def log(self, index, stream, line):
        dy, oldh, newh = self._common(index, lambda h: h + 1)
        noeol, = line.splitlines()
        eol = line[len(noeol):]
        if noeol:
            chunks = [noeol[i:i + self.width] for i in range(0, len(noeol), self.width)]
            stream.write(chunks[0])
            for c in islice(chunks, 1, None):
                stream.flush()
                tput.hpa(0, stdout = sys.stderr)
                sys.stderr.flush()
                stream.write(c)
        if eol:
            stream.write(eol)
        else:
            stream.flush()
        sys.stderr.write('\n' * ((not eol) + dy))

@singleton
class LogFile:

    words = {
        Style.running: 'Damp',
        Style.normal: 'Soaked',
        Style.abrupt: 'Failed',
    }

    def head(self, index, obj, style):
        try:
            word = self.words[style]
        except KeyError:
            return
        print(f"{word}:", obj, file = sys.stderr)

    def log(self, index, stream, line):
        stream.write(line)

def getterminal():
    try:
        width = int(tput.cols())
    except CalledProcessError:
        return LogFile
    return Terminal(width)
