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

from . import cpuexecutor
from .context import createparent
from .terminal import LogFile, Terminal
from argparse import ArgumentParser
from aridity import Repl
from functools import partial
from lagoon import diff
from pathlib import Path
from splut import invokeall
import logging, os

class SoakConfig:

    soakkey = 'soak'

    def __init__(self, parent, configpath):
        self.context = parent.createchild()
        with Repl(self.context) as repl:
            repl.printf("cwd = %s", configpath.parent)
            repl.printf(". %s", configpath.name)
        self.reltargets = [Path(rt) for rt, _ in self.context.resolved(self.soakkey).resolvables.items()]
        self.dirpath = configpath.parent

    def process(self, log, reltarget):
        relpartial = reltarget.with_name(f"{reltarget.name}.part")
        target = self.dirpath / reltarget
        log(target, rev = True)
        self.context.resolved(self.soakkey, str(reltarget), 'data').writeout(self.dirpath / relpartial)
        (self.dirpath / relpartial).rename(target)
        log(target)

    def origtext(self, reltarget):
        return self.context.resolved(self.soakkey, str(reltarget), 'diff').cat()

    def diff(self, origtext, reltarget):
        diff._us.print('--color=always', '-', self.dirpath / reltarget, input = origtext, check = False)

def main_soak():
    parser = ArgumentParser()
    parser.add_argument('-n', action = 'store_true')
    parser.add_argument('-d', action = 'store_true')
    parser.add_argument('-v', action = 'store_true')
    soak(parser.parse_args(), Path('.'))

def soak(config, soakroot):
    logging.basicConfig(format = "[%(levelname)s] %(message)s", level = logging.DEBUG if config.v else logging.INFO)
    parent = createparent(soakroot)
    soakconfigs = [SoakConfig(parent, p) for p in soakroot.rglob('soak.arid')]
    if not config.n:
        terminal = Terminal(sum(len(sc.reltargets) for sc in soakconfigs)) if 'TERM' in os.environ else LogFile
        with cpuexecutor() as executor:
            results = []
            for soakconfig in soakconfigs:
                for reltarget in soakconfig.reltargets:
                    log = partial(terminal.log, len(results))
                    log(soakconfig.dirpath / reltarget, dark = True)
                    results.append(executor.submit(soakconfig.process, log, reltarget).result)
            invokeall(results)
    if config.d:
        with cpuexecutor() as executor:
            diffs = []
            for soakconfig in soakconfigs:
                for reltarget in soakconfig.reltargets:
                    diffs.append(partial(lambda soakconfig, origtextfuture, reltarget: soakconfig.diff(origtextfuture.result(), reltarget),
                            soakconfig, executor.submit(soakconfig.origtext, reltarget), reltarget))
            invokeall(diffs)
