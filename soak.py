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

def process(log, context, targetpath):
    cwd = Path(context.resolved('cwd').value)
    dest = cwd / targetpath
    partial = dest.parent / f"{dest.name}.part"
    log(f"{tput.rev()}{dest}")
    with Repl(context) as repl:
        repl.printf("redirect %s", partial.resolve())
        repl.printf("< %s", context.resolved('soak', targetpath, 'from').value)
    partial.rename(dest)
    log(dest)
    return cwd / context.resolved('soak', targetpath, 'diff').value, dest

def main_soak():
    parser = ArgumentParser()
    parser.add_argument('-d', action = 'store_true')
    config = parser.parse_args()
    configpaths = list(Path('.').rglob('deploy.arid'))
    for _ in configpaths:
        print(file = sys.stderr)
    tput.sc(stdout = sys.stderr)
    upcount = len(configpaths)
    terminal = Terminal()
    with ThreadPoolExecutor() as executor:
        futures = []
        for configpath in configpaths:
            context = Context()
            context['sops2arid', ] = Function(sops2arid)
            context['sopsget', ] = Function(sopsget)
            context['readfile', ] = Function(readfile)
            with Repl(context) as repl:
                repl.printf("cwd = %s", configpath.parent)
                repl.printf(". %s", configpath.name)
            for targetpath in context.resolved('soak').resolvables.keys():
                futures.append(executor.submit(process, partial(terminal.log, upcount), context, targetpath))
                upcount -= 1
        for f in futures:
            f.result()
    tput.rc(stdout = sys.stderr)
    if config.d:
        for f in futures:
            p, q = f.result()
            with git.show.bg(f"master:./{p}") as gitshow:
                diff.print('-u', '--color=always', gitshow, q, check = False)
