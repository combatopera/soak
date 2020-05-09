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

from .util import Snapshot
from aridity import Context, Repl
from aridimpl.model import Directive, Function, Text
from aridimpl.util import NoSuchPathException
from importlib import import_module
from lagoon import git
from pathlib import Path
import os, re, yaml

singledigit = re.compile('[0-9]')
zeroormorespaces = re.compile(' *')
linefeed = '\n'

def plugin(prefix, phrase, context):
    modulename, globalname = (obj.cat() for obj in phrase.resolve(context, aslist = True))
    if modulename.startswith('.'):
        relpath = str(Path(context.resolved('here').cat()).resolve().relative_to(context.resolved('toplevel').cat()))
        if '.' == relpath:
            raise NoSuchPathException('package')
        package = relpath.replace(os.sep, '.')
    else:
        package = None
    getattr(import_module(modulename, package), globalname)(context)

def xmlquote(context, resolvable):
    from xml.sax.saxutils import escape
    return Text(escape(resolvable.resolve(context).cat()))

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
    # TODO: Stop resolving once path is absolute.
    return Text(str(Path(context.resolved('toplevel').cat(), *(r.resolve(context).cat() for r in resolvables))))

def _toplevel(anydir):
    toplevel, = git.rev_parse.__show_toplevel(cwd = anydir).splitlines()
    return Text(toplevel)

def createparent(soakroot):
    parent = Context()
    parent['plugin',] = Directive(plugin)
    parent['xml"',] = Function(xmlquote)
    parent['|',] = Function(blockliteral)
    parent['//',] = Function(rootpath)
    parent['toplevel',] = Snapshot(lambda: _toplevel(soakroot))
    with Repl(parent) as repl:
        repl('data = $processtemplate$(from)') # XXX: Too easy to accidentally override?
        repl.printf("indentunit = %s", 4 * ' ')
    return parent
