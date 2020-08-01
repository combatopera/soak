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

from aridity.model import Resolvable
from threading import Lock

class Snapshot(Resolvable):

    class Result:

        def __init__(self, eornone, obj):
            self.eornone = eornone
            self.obj = obj

        def get(self):
            if self.eornone is not None:
                raise self.eornone
            return self.obj

    def __init__(self, factory):
        self.lock = Lock()
        self.factory = factory

    def _loadresult(self):
        with self.lock:
            try:
                self.result
            except AttributeError:
                f = self.factory
                try:
                    obj = f()
                    eornone = None
                except Exception as e:
                    obj = None
                    eornone = e
                self.result = self.Result(eornone, obj)

    def resolve(self, context):
        try:
            r = self.result
        except AttributeError:
            self._loadresult()
            r = self.result
        return r.get()

class PathResolvable(Resolvable):

    def __init__(self, *path):
        self.path = path

    def resolve(self, context):
        return context.resolved(*self.path)
