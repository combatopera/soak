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

from .util import PathResolvable, Snapshot
from aridity import Context, NoSuchPathException, Repl
from aridity.context import slashfunction
from aridity.model import Directive, Function, Text
from lagoon import git
from pathlib import Path
import os, re, subprocess, yaml

singledigit = re.compile('[0-9]')
zeroormorespaces = re.compile(' *')
zeroormoredots = re.compile('[.]*')
linefeed = '\n'
dotpy = '.py'
toplevelres = PathResolvable('toplevel')

def plugin(prefix, suffix, context):
    modulename, globalname = (obj.cat() for _, obj in suffix.tophrase().resolve(context, aslist = True).itero())
    leadingdots = len(zeroormoredots.match(modulename).group())
    words = modulename[leadingdots:].split('.')
    relpath = Path(*words[:-1]) / f"{words[-1]}{dotpy}"
    if leadingdots:
        modulepath = Path(context.resolved('here').cat(), *['..'] * (leadingdots - 1), relpath)
        try:
            modulename = str(modulepath.relative_to(toplevelres.resolve(context).cat()))[:-len(dotpy)].replace(os.sep, '.')
        except NoSuchPathException:
            modulename = None # It won't be able to do its own relative imports.
    else:
        modulepath = Path(toplevelres.resolve(context).cat(), relpath)
    g = {} if modulename is None else dict(__name__ = modulename)
    with modulepath.open() as f:
        exec(f.read(), g)
    g[globalname](context)

def blockliteral(context, textresolvable):
    text = yaml.dump(textresolvable.resolve(context).cat(), default_style = '|')
    header, *lines = text.splitlines() # For template interpolation convenience we discard the (insignificant) trailing newline.
    if not lines:
        return Text(header)
    if '...' == lines[-1]:
        lines.pop() # XXX: Could this result in no remaining lines?
    indentunit = context.resolved('indentunit').cat()
    m = singledigit.search(header)
    if m is None:
        pyyamlindent = len(zeroormorespaces.match(lines[0]).group())
    else:
        pyyamlindent = int(m.group())
        header = f"{header[:m.start()]}{len(zeroormorespaces.fullmatch(indentunit).group())}{header[m.end():]}"
    contextindent = context.resolved('indent').cat()
    return Text(f"""{header}\n{linefeed.join(f"{contextindent}{indentunit}{line[pyyamlindent:]}" for line in lines)}""")

def rootpath(context, *resolvables):
    return slashfunction(context, toplevelres, *resolvables)

def _toplevel(anydir):
    try:
        toplevel, = git.rev_parse.__show_toplevel(cwd = anydir).splitlines()
        return Text(toplevel)
    except subprocess.CalledProcessError:
        raise NoSuchPathException('Git property: toplevel')

def createparent(soakroot):
    parent = Context()
    parent['plugin',] = Directive(plugin)
    parent['|',] = Function(blockliteral)
    parent['//',] = Function(rootpath)
    parent['toplevel',] = Snapshot(lambda: _toplevel(soakroot))
    with Repl(parent) as repl:
        repl('data = $processtemplate$(from)') # XXX: Too easy to accidentally override?
        repl.printf("indentunit = %s", 4 * ' ')
    return parent
