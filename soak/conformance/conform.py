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

from aridity.model import Binary
from pathlib import Path
import subprocess, sys

def bdist_wheel(scope, resolvable):
    projectdir = Path(scope.resolved('cwd').cat(), resolvable.resolve(scope).cat())
    subprocess.check_call([sys.executable, 'setup.py', 'bdist_wheel'], cwd = projectdir, stdout = subprocess.DEVNULL)
    # TODO LATER: Instead of reading the file, add a type representing a path and return that.
    whlpath, = (projectdir / 'dist').glob('*.whl')
    with whlpath.open('rb') as f:
        return Binary(f.read())
