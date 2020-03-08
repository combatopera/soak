from argparse import ArgumentParser
from aridity import Context, Repl
from aridimpl.model import Function, Text
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from lagoon import bash, diff, git, tput
from pathlib import Path
from threading import Lock
import subprocess, sys, yaml

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
    for f in sops2arid, sopsget, readfile:
        parent[f.__name__,] = Function(f)

    def __init__(self, configpath):
        self.context = self.parent.createchild()
        with Repl(self.context) as repl:
            repl.printf("cwd = %s", configpath.parent)
            repl.printf(". %s", configpath.name)
        self.reltargets = self.context.resolved(self.soakkey).resolvables.keys()
        self.cwd = configpath.parent

    def process(self, log, reltarget):
        relpartial = f"{reltarget}.part"
        log(f"{tput.rev()}{self.cwd / reltarget}")
        with Repl(self.context.createchild()) as repl:
            repl.printf("redirect %s", relpartial)
            repl.printf("< $(%s %s from)", self.soakkey, reltarget)
        (self.cwd / relpartial).rename(self.cwd / reltarget)
        log(self.cwd / reltarget)
        return self.cwd / self.context.resolved(self.soakkey, reltarget, 'diff').value, self.cwd / reltarget

def main_soak():
    parser = ArgumentParser()
    parser.add_argument('-d', action = 'store_true')
    config = parser.parse_args()
    soakconfigs = [SoakConfig(p) for p in Path('.').rglob('soak.arid')]
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
        for f in futures:
            p, q = f.result()
            with git.show.bg(f"master:./{p}") as gitshow:
                diff.print('-u', '--color=always', gitshow, q, check = False)
