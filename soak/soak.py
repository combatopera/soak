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

from .context import createparent, sops
from .terminal import Terminal
from argparse import ArgumentParser
from aridity import Repl
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from functools import partial
from lagoon import diff, git
from pathlib import Path
from shutil import copyfileobj
import subprocess, tempfile

@contextmanager
def nullcontext(x):
    yield x

@contextmanager
def unsops(suffix, encstream):
    with tempfile.NamedTemporaryFile('w', suffix = suffix) as f:
        copyfileobj(encstream, f)
        f.flush()
        with sops.bg(f.name, stderr = subprocess.DEVNULL) as decstream:
            yield decstream

class SoakConfig:

    soakkey = 'soak'

    def __init__(self, parent, configpath):
        self.context = parent.createchild()
        with Repl(self.context) as repl:
            repl.printf("cwd = %s", configpath.parent)
            repl.printf(". %s", configpath.name)
        self.reltargets = self.context.resolved(self.soakkey).resolvables.keys()
        self.dirpath = configpath.parent

    def process(self, log, reltarget):
        relpartial = f"{reltarget}.part"
        target = self.dirpath / reltarget
        log(target, rev = True)
        with Repl(self.context.createchild()) as repl:
            repl.printf("redirect %s", relpartial)
            repl.printf("< $(%s %s from)", self.soakkey, reltarget)
        (self.dirpath / relpartial).rename(target)
        log(target)

    def diff(self):
        # TODO: Parallelise the expensive bits.
        for reltarget in self.reltargets:
            orig = self.dirpath / self.context.resolved(self.soakkey, reltarget, 'diff').value
            filter = nullcontext if self.context.resolved(self.soakkey, reltarget, 'plain').value else partial(unsops, orig.suffix)
            with git.show.bg(f"master:./{orig}") as origstream, filter(origstream) as plainstream:
                diff._us.print('--color=always', plainstream, self.dirpath / reltarget, check = False)

def main_soak():
    parser = ArgumentParser()
    parser.add_argument('-n', action = 'store_true')
    parser.add_argument('-d', action = 'store_true')
    config = parser.parse_args()
    parent = createparent()
    soakconfigs = [SoakConfig(parent, p) for p in Path('.').rglob('soak.arid')]
    if not config.n:
        upcount = sum(len(sc.reltargets) for sc in soakconfigs)
        terminal = Terminal(upcount)
        with ThreadPoolExecutor() as executor:
            futures = []
            for soakconfig in soakconfigs:
                for reltarget in soakconfig.reltargets:
                    futures.append(executor.submit(soakconfig.process, partial(terminal.log, upcount), reltarget))
                    upcount -= 1
            for f in futures:
                f.result()
    if config.d:
        for soakconfig in soakconfigs:
            soakconfig.diff()
