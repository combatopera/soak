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

from .soak import soak
from lagoon import git, unzip
from pathlib import Path
from pkg_resources import resource_filename # TODO: Port to new API.
from shutil import copytree
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import TestCase
import json, yaml

class TestConformance(TestCase):

    def test_works(self):
        source = Path(resource_filename(__name__, 'conformance'))
        with TemporaryDirectory() as tempdir:
            conformance = Path(tempdir, source.name)
            # TODO LATER: Ideally do not copy git-ignored files.
            copytree(source, conformance)
            git.init[print](conformance)
            soak(SimpleNamespace(n = None, d = None, v = None), conformance)
            with (conformance / 'conf.json').open() as f:
                self.assertEqual(dict(mydata = 'hello there'), json.load(f))
            self.assertEqual('Bad example.', (conformance / 'readme.txt').read_text())
            self.assertTrue(' testing: mylib.py ' in unzip._t(conformance / 'mylib.whl'))
            infotext = (conformance / 'info.yaml').read_text()
            self.assertEqual('''root:
    x:
        block: |
            first line
            second line
    noeol: |-
        1st line
        2nd line
    empty: ""
    d:
        doubleeol: |+
            w
            
        doubleeolonly: |4+
            
            
    noeol1: |-
        only line
    indentedeol: |4
         x
    linear: " "
''', infotext)
            info = yaml.safe_load(infotext)
            self.assertEqual('first line\nsecond line\n', info['root']['x']['block'])
            self.assertEqual('1st line\n2nd line', info['root']['noeol'])
            self.assertEqual('', info['root']['empty'])
            self.assertEqual('w\n\n', info['root']['d']['doubleeol'])
            self.assertEqual('\n\n', info['root']['d']['doubleeolonly'])
            self.assertEqual('only line', info['root']['noeol1'])
            self.assertEqual(' x\n', info['root']['indentedeol']) # TODO LATER: Also test non-space in indentunit.
            self.assertEqual(' ', info['root']['linear'])
            self.assertEqual('Can report relplug OK and veryrelplug OK.\n', (conformance / 'subdir' / 'verysubdir' / 'report.txt').read_text())
