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

from argparse import ArgumentParser
from aridity import Context, Repl
from aridimpl.model import Function, Text
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from functools import lru_cache, partial
from lagoon import bash, diff, git, tput
from pathlib import Path
from shutil import copyfileobj
from threading import Lock
import subprocess, sys, tempfile, yaml

@contextmanager
def nullcontext(x):
    yield x

sopsargs = '-ic', 'sops -d "$@"', 'sops'
sopskwargs = dict(start_new_session = True, stderr = subprocess.DEVNULL)

@contextmanager
def unsops(suffix, encstream):
    with tempfile.NamedTemporaryFile('w', suffix = suffix) as f:
        copyfileobj(encstream, f)
        f.flush()
        with bash.bg(*sopsargs, f.name, **sopskwargs) as decstream:
            yield decstream

@lru_cache()
def _unsopsimpl(path):
    return yaml.safe_load(bash(*sopsargs, path, **sopskwargs))

def _unsops(context, resolvable):
    return _unsopsimpl(resolvable.resolve(context).cat())

def sops2arid(context, resolvable):
    def process(obj, *path):
        try:
            items = obj.items
        except AttributeError:
            entries.append((path, obj))
            return
        for key, value in items():
            process(value, *path, key)
    entries = []
    process(_unsops(context, resolvable))
    return Text(''.join(f"{' '.join(path)} = {value}\n" for path, value in entries))

def sopsget(context, pathresolvable, *nameresolvables):
    obj = _unsops(context, pathresolvable)
    for r in nameresolvables:
        obj = obj[r.resolve(context).cat()]
    return Text(obj)

def readfile(context, resolvable):
    with open(resolvable.resolve(context).cat()) as f:
        return Text(f.read())

def blockliteral(context, indentresolvable, textresolvable):
    indent = (indentresolvable.resolve(context).value - 2) * ' '
    text = yaml.dump(textresolvable.resolve(context).cat(), default_style = '|')
    return Text('\n'.join(f"{indent if i else ''}{line}" for i, line in enumerate(text.splitlines())))

class Terminal:

    def __init__(self):
        self.lock = Lock()

    def log(self, upcount, text):
        with self.lock:
            tput.cuu(upcount, stdout = sys.stderr)
            print(text, file = sys.stderr)
            tput.sgr0(stdout = sys.stderr)
            tput.rc(stdout = sys.stderr)
            sys.stderr.flush()

class SoakConfig:

    soakkey = 'soak'
    parent = Context()
    with Repl(parent) as repl:
        repl('plain = false')
    for f in sops2arid, sopsget, readfile:
        parent[f.__name__,] = Function(f)
    parent['|',] = Function(blockliteral)
    del repl, f

    def __init__(self, configpath):
        self.context = self.parent.createchild()
        with Repl(self.context) as repl:
            repl.printf("cwd = %s", configpath.parent)
            repl.printf(". %s", configpath.name)
        self.reltargets = self.context.resolved(self.soakkey).resolvables.keys()
        self.dirpath = configpath.parent

    def process(self, log, reltarget):
        relpartial = f"{reltarget}.part"
        target = self.dirpath / reltarget
        log(f"{tput.rev()}{target}")
        with Repl(self.context.createchild()) as repl:
            repl.printf("redirect %s", relpartial)
            repl.printf("< $(%s %s from)", self.soakkey, reltarget)
        (self.dirpath / relpartial).rename(target)
        log(target)

    def diff(self):
        for reltarget in self.reltargets:
            orig = self.dirpath / self.context.resolved(self.soakkey, reltarget, 'diff').value
            filter = nullcontext if self.context.resolved(self.soakkey, reltarget, 'plain').value else partial(unsops, orig.suffix)
            with git.show.bg(f"master:./{orig}") as origstream, filter(origstream) as plainstream:
                diff.print('-us', '--color=always', plainstream, self.dirpath / reltarget, check = False)

def main_soak():
    parser = ArgumentParser()
    parser.add_argument('-n', action = 'store_true')
    parser.add_argument('-d', action = 'store_true')
    config = parser.parse_args()
    soakconfigs = [SoakConfig(p) for p in Path('.').rglob('soak.arid')]
    if not config.n:
        upcount = sum(len(sc.reltargets) for sc in soakconfigs)
        sys.stderr.write('\n' * upcount)
        tput.sc(stdout = sys.stderr)
        terminal = Terminal()
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
