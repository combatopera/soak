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

from aridimpl.model import Resolvable
from threading import Lock

class Snapshot(Resolvable):

    def __init__(self, factory):
        self.lock = Lock()
        self.factory = factory

    def _loadobj(self):
        with self.lock:
            try:
                self.obj
            except AttributeError:
                self.obj = self.factory()

    def resolve(self, context):
        try:
            return self.obj
        except AttributeError:
            self._loadobj()
            return self.obj

class PathResolvable(Resolvable):

    def __init__(self, *path):
        self.path = path

    def resolve(self, context):
        return context.resolved(*self.path)
