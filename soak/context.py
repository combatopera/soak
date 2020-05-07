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
from aridimpl.model import Directive, Function, Text
from functools import partial
from importlib import import_module
from pathlib import Path
import os, yaml

def plugin(toplevel, prefix, phrase, context):
    modulename, globalname = phrase.resolve(context, aslist = True)
    package = str(Path(context.resolved('here').cat()).resolve().relative_to(toplevel)).replace(os.sep, '.')
    getattr(import_module(modulename.cat(), package), globalname.cat())(context)

def xmlquote(context, resolvable):
    from xml.sax.saxutils import escape
    return Text(escape(resolvable.resolve(context).cat()))

def blockliteral(context, textresolvable):
    indent = f"{context.resolved('indent').cat()}{context.resolved('indentunit').cat()}"
    text = yaml.dump(textresolvable.resolve(context).cat(), default_style = '|')
    header, *lines = text.splitlines() # For interpolation convenience we discard the (insignificant) trailing newline.
    if not lines:
        return Text(header)
    if '...' == lines[-1]:
        lines.pop()
    newline = '\n'
    return Text(f"""{header}\n{newline.join(f"{indent}{line[2:]}" for line in lines)}""")

def rootpath(toplevel, context, *resolvables):
    return Text(str(Path(toplevel, *(r.resolve(context).cat() for r in resolvables))))

def createparent(toplevel):
    parent = Context()
    parent['plugin',] = Directive(partial(plugin, toplevel))
    parent['xml"',] = Function(xmlquote)
    parent['|',] = Function(blockliteral)
    parent['//',] = Function(partial(rootpath, toplevel))
    with Repl(parent) as repl:
        repl('data = $processtemplate$(from)') # XXX: Too easy to accidentally override?
        repl.printf("indentunit = %s", 4 * ' ')
    return parent
