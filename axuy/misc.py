# misc.py - miscellaneous functions
# Copyright (C) 2019  Nguyễn Gia Phong
#
# This file is part of Axuy
#
# Axuy is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Axuy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with Axuy.  If not, see <https://www.gnu.org/licenses/>.

from itertools import chain, combinations_with_replacement, permutations

import numpy
import pkg_resources

TANGO = {'Background': '2e3436',
         'Butter': 'fce94f',
         'Orange': 'fcaf3e',
         'Chocolate': 'e9b96e',
         'Chameleon': '8ae234',
         'Sky Blue': '729fcf',
         'Plum': 'ad7fa8',
         'Scarlet Red': 'ef2929',
         'Aluminium': 'eeeeec'}


def color(name):
    """Return numpy float32 array of RGB colors from color name."""
    return numpy.float32([i / 255 for i in bytes.fromhex(TANGO[name])])


def neighbors(x, y, z):
    """Return a generator of coordinates of images point (x, y, z)
    in neighbor universes.
    """
    for i, j, k in set(chain.from_iterable(
        map(permutations, combinations_with_replacement((-1, 0, 1), 3)))):
        yield x + i*12, y + j*12, z + k*9


def resource_filename(resource_name):
    """Return a true filesystem path for the specified resource."""
    return pkg_resources.resource_filename('axuy', resource_name)
