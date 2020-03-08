from argparse import ArgumentParser
from aridity import Context, Repl
from aridimpl.model import Function, Text
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from functools import partial
from lagoon import bash, diff, git, tput
from pathlib import Path
from shutil import copyfileobj
from threading import Lock
import subprocess, sys, tempfile, yaml

@contextmanager
def nullcontext(x):
    yield x

@contextmanager
def unsops(suffix, encstream):
    with tempfile.NamedTemporaryFile('w', suffix = suffix) as f:
        copyfileobj(encstream, f)
        f.flush()
        with bash.bg('-ic', 'sops -d "$@"', 'sops', f.name, start_new_session = True, stderr = subprocess.DEVNULL) as decstream:
            yield decstream

def _unsops(context, resolvable):
    return yaml.safe_load(bash('-ic', 'sops -d "$@"', 'sops', resolvable.resolve(context).cat(), start_new_session = True, stderr = subprocess.DEVNULL))

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

def sopsget(context, resolvable, *resolvables):
    obj = _unsops(context, resolvable)
    for r in resolvables:
        obj = obj[r.resolve(context).cat()]
    return Text(obj)

def readfile(context, resolvable):
    with open(resolvable.resolve(context).cat()) as f:
        return Text(f.read())

class Terminal:

    def __init__(self):
        self.lock = Lock()

    def log(self, upcount, text):
        with self.lock:
            tput.rc(stdout = sys.stderr)
            tput.cuu(upcount, stdout = sys.stderr)
            print(text, end = '', file = sys.stderr)
            tput.sgr0(stdout = sys.stderr)
            sys.stderr.flush()

class SoakConfig:

    soakkey = 'soak'
    parent = Context()
    with Repl(parent) as repl:
        repl('plain = false')
    for f in sops2arid, sopsget, readfile:
        parent[f.__name__,] = Function(f)
    del repl, f

    def __init__(self, configpath):
        self.context = self.parent.createchild()
        with Repl(self.context) as repl:
            repl.printf("cwd = %s", configpath.parent)
            repl.printf(". %s", configpath.name)
        self.reltargets = self.context.resolved(self.soakkey).resolvables.keys()
        self.cwd = configpath.parent

    def process(self, log, reltarget):
        relpartial = f"{reltarget}.part"
        target = self.cwd / reltarget
        log(f"{tput.rev()}{target}")
        with Repl(self.context.createchild()) as repl:
            repl.printf("redirect %s", relpartial)
            repl.printf("< $(%s %s from)", self.soakkey, reltarget)
        (self.cwd / relpartial).rename(target)
        log(target)

    def diff(self):
        for reltarget in self.reltargets:
            orig = self.cwd / self.context.resolved(self.soakkey, reltarget, 'diff').value
            filter = nullcontext if self.context.resolved(self.soakkey, reltarget, 'plain').value else partial(unsops, orig.suffix)
            with git.show.bg(f"master:./{orig}") as origstream, filter(origstream) as plainstream:
                diff.print('-u', '--color=always', plainstream, self.cwd / reltarget, check = False)

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
        tput.rc(stdout = sys.stderr)
    if config.d:
        for soakconfig in soakconfigs:
            soakconfig.diff()
