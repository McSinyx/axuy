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

from itertools import (chain, combinations_with_replacement,
                       permutations, product)
from random import choices, shuffle

import numpy
from pkg_resources import resource_filename

TANGO = {'Butter': ('fce94f', 'edd400', 'c4a000'),
         'Orange': ('fcaf3e', 'f57900', 'ce5c00'),
         'Chocolate': ('e9b96e', 'c17d11', '8f5902'),
         'Chameleon': ('8ae234', '73d216', '4e9a06'),
         'Sky Blue': ('729fcf', '3465a4', '204a87'),
         'Plum': ('ad7fa8', '75507b', '5c3566'),
         'Scarlet Red': ('ef2929', 'cc0000', 'a40000'),
         'Aluminium': ('eeeeec', 'd3d7cf', 'babdb6',
                       '888a85', '555753', '2e3436'),
         'Background': ('000000',)}
COLOR_NAMES = ['Butter', 'Orange', 'Chocolate', 'Chameleon',
               'Sky Blue', 'Plum', 'Scarlet Red']
NEIGHBORS = set(chain.from_iterable(
    map(permutations, combinations_with_replacement((-1, 0, 1), 3))))
# map.npy is generated by ../tools/mapgen
SPACE = numpy.load(resource_filename('axuy', 'map.npy'))


def abspath(resource_name):
    """Return a true filesystem path for the specified resource."""
    return resource_filename('axuy', resource_name)


def color(name, idx=0):
    """Return NumPy float32 array of RGB colors from color name."""
    return numpy.float32([i / 255 for i in bytes.fromhex(TANGO[name][idx])])


def mapidgen(replacement=False):
    """Return a randomly generated map ID."""
    mapid = list(range(48))
    if replacement: return choices(mapid, k=48)
    shuffle(mapid)
    return mapid


def mapgen(mapid):
    """Return the NumPy array of shape (12, 12, 9) of bools
    generated from the given ID.
    """
    base = numpy.stack([SPACE[i] for i in mapid]).reshape(4, 4, 3, 3, 3, 3)
    space = numpy.zeros([12, 12, 9], dtype=bool)
    for (i, j, k, x, y, z), occupied in numpy.ndenumerate(base):
        if occupied: space[i*3 + x][j*3 + y][k*3 + z] = 1
    return space


def neighbors(x, y, z):
    """Return a generator of coordinates of images point (x, y, z)
    in neighbor universes.
    """
    for i, j, k in NEIGHBORS: yield x + i*12, y + j*12, z + k*9


def normalized(*vector):
    """Return normalized vector as a NumPy array of float32."""
    v = numpy.float32(vector)
    if not any(v): return v
    return v / sum(v**2)


def sign(x) -> int:
    """Return the sign of number x."""
    if x > 0: return 1
    if x: return -1
    return 0


def twelve(x) -> int:
    """Shorthand for int(x % 12)."""
    return int(x % 12)


def nine(x) -> int:
    """Shorthand for int(x % 9)."""
    return int(x % 9)


def placeable(space, x, y, z, r):
    """Return whether a sphere of radius r
    can be placed at (x, y, z) in given space."""
    return not any(space[i][j][k] for i, j, k in product(
        {twelve(x-r), twelve(x), twelve(x+r)},
        {twelve(y-r), twelve(y), twelve(y+r)},
        {nine(z-r), nine(z), nine(z+r)}))
