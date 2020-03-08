from argparse import ArgumentParser
from aridity import Context, Repl
from aridimpl.model import Function, Text
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from lagoon import bash, diff, git, tput
from pathlib import Path
from threading import Lock
import subprocess, sys, yaml

soakkey = 'soak'

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

    def __init__(self, configpath):
        self.context = Context()
        self.context['sops2arid',] = Function(sops2arid)
        self.context['sopsget',] = Function(sopsget)
        self.context['readfile',] = Function(readfile)
        with Repl(self.context) as repl:
            repl.printf("cwd = %s", configpath.parent)
            repl.printf(". %s", configpath.name)

    def process(self, log, dest):
        partial = f"{dest}.part"
        cwd = Path(self.context.resolved('cwd').value)
        log(f"{tput.rev()}{cwd / dest}")
        with Repl(self.context) as repl: # FIXME: Use child.
            repl.printf("redirect %s", partial)
            repl.printf("< $(%s %s from)", soakkey, dest)
        (cwd / partial).rename(cwd / dest)
        log(cwd / dest)
        return cwd / self.context.resolved(soakkey, dest, 'diff').value, cwd / dest

def main_soak():
    parser = ArgumentParser()
    parser.add_argument('-d', action = 'store_true')
    config = parser.parse_args()
    soakconfigs = [SoakConfig(p) for p in Path('.').rglob('soak.arid')]
    upcount = len(soakconfigs)
    sys.stderr.write('\n' * upcount)
    tput.sc(stdout = sys.stderr)
    terminal = Terminal()
    with ThreadPoolExecutor() as executor:
        futures = []
        for soakconfig in soakconfigs:
            for dest in soakconfig.context.resolved(soakkey).resolvables.keys():
                futures.append(executor.submit(soakconfig.process, partial(terminal.log, upcount), dest))
                upcount -= 1
        for f in futures:
            f.result()
    tput.rc(stdout = sys.stderr)
    if config.d:
        for f in futures:
            p, q = f.result()
            with git.show.bg(f"master:./{p}") as gitshow:
                diff.print('-u', '--color=always', gitshow, q, check = False)
