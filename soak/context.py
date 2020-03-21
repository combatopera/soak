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

from aridity import Context
from aridimpl.model import Directive, Function, Text
from importlib import import_module
from lagoon import git
from pathlib import Path
import sys, yaml

toplevel, = git.rev_parse.__show_toplevel().splitlines()
sys.path.append(toplevel) # XXX: Or prepend?

def plugin(prefix, phrase, context):
    modulename, globalname = phrase.resolve(context, aslist = True)
    getattr(import_module(modulename.cat()), globalname.cat())(context)

def xmlquote(context, resolvable):
    from xml.sax.saxutils import escape
    return Text(escape(resolvable.resolve(context).cat()))

def blockliteral(context, indentresolvable, textresolvable):
    indent = (indentresolvable.resolve(context).value - 2) * ' '
    text = yaml.dump(textresolvable.resolve(context).cat(), default_style = '|')
    return Text('\n'.join(f"{indent if i else ''}{line}" for i, line in enumerate(text.splitlines())))

def rootpath(context, *resolvables):
    return Text(str(Path(toplevel, *(r.resolve(context).cat() for r in resolvables))))

def createparent():
    parent = Context()
    parent['plugin',] = Directive(plugin)
    parent['xml"',] = Function(xmlquote)
    parent['|',] = Function(blockliteral)
    parent['//',] = Function(rootpath)
    return parent
