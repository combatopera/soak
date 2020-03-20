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

from aridity import Context, Repl
from aridimpl.grammar import templateparser
from aridimpl.model import Concat, Function, Text
from functools import lru_cache
from lagoon import bash, git
from pathlib import Path
import subprocess, sys, tempfile, yaml

sops = bash._ic.partial('sops -d "$@"', 'sops', start_new_session = True)

@lru_cache()
def _unsopsimpl(path, unyaml):
    if unyaml:
        return yaml.safe_load(_unsopsimpl(path, False))
    completed = sops(path, stderr = subprocess.PIPE, check = False)
    if completed.returncode:
        sys.stderr.write(completed.stderr)
        completed.check_returncode()
    return completed.stdout

def _unsops(context, resolvable):
    return _unsopsimpl(resolvable.resolve(context).cat(), True)

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

def processtemplate(context, resolvable):
    with open(resolvable.resolve(context).cat()) as f:
        return Text(Concat(templateparser(f.read())).resolve(context).cat()) # TODO: There should be an easier way.

def xmlquote(context, resolvable):
    from xml.sax.saxutils import escape
    return Text(escape(resolvable.resolve(context).cat()))

def blockliteral(context, indentresolvable, textresolvable):
    indent = (indentresolvable.resolve(context).value - 2) * ' '
    text = yaml.dump(textresolvable.resolve(context).cat(), default_style = '|')
    return Text('\n'.join(f"{indent if i else ''}{line}" for i, line in enumerate(text.splitlines())))

def rootpath(context, *resolvables):
    root, = git.rev_parse.__show_toplevel().splitlines()
    return Text(str(Path(root, *(r.resolve(context).cat() for r in resolvables))))

def master(context, resolvable):
    path = Path(context.resolved('cwd').value, resolvable.resolve(context).cat())
    obj = Text(git.show(f"master:./{path}"))
    obj.suffix = path.suffix # Bit of a hack.
    return obj

def unsops(context, resolvable):
    with tempfile.NamedTemporaryFile('w', suffix = resolvable.suffix) as f:
        f.write(resolvable.resolve(context).cat())
        f.flush()
        return Text(_unsopsimpl(f.name, False))

def createparent():
    parent = Context()
    with Repl(parent) as repl:
        repl('plain = false')
    # TODO: Migrate some of these to plugin(s).
    for f in sops2arid, sopsget, readfile, processtemplate, master, unsops:
        parent[f.__name__,] = Function(f)
    parent['xml"',] = Function(xmlquote)
    parent['|',] = Function(blockliteral)
    parent['//',] = Function(rootpath)
    return parent
