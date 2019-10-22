# game characters and bullets
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

__doc__ = 'Axuy module for character and bullet class'
__all__ = ['TETRAVERTICES', 'OCTOVERTICES', 'RPICO', 'RSHARD', 'RCOLL', 'INV',
           'PICO_SPEED', 'SHARD_SPEED', 'SHARD_LIFE', 'RPS', 'Pico', 'Shard']

from itertools import combinations
from math import acos, atan2, log10, pi, sqrt
from random import random

import numpy as np
from numpy.linalg import norm

from .misc import normalized, placeable, rot33

TETRAVERTICES = np.float32([[0, sqrt(8), -1], [sqrt(6), -sqrt(2), -1],
                            [0, 0, 3], [-sqrt(6), -sqrt(2), -1]]) / 18
OCTOVERTICES = np.float32([(a + b) / 2.0
                           for a, b in combinations(TETRAVERTICES, 2)])
RPICO = norm(TETRAVERTICES[0])
RSHARD = norm(OCTOVERTICES[0])
RCOLL = RPICO * 2/3

INVX = np.float32([[-1, 0, 0], [0, 1, 0], [0, 0, 1]])
INVY = np.float32([[1, 0, 0], [0, -1, 0], [0, 0, 1]])
INVZ = np.float32([[1, 0, 0], [0, 1, 0], [0, 0, -1]])
INV = {'x': INVX, 'y': INVY, 'z': INVZ}

PICO_SPEED = 1 + sqrt(5)        # unit/s
SHARD_SPEED = PICO_SPEED * 2    # unit/s
SHARD_LIFE = 3  # bounces
RPS = pi    # rounds per second


class Shard:
    """Fragment broken or shot out of a Pico, which is a regular
    octahedron whose circumscribed sphere's radius is RSHARD.

    Parameters
    ----------
    address : Tuple[str, int]
        IP address (host, port).
    space : np.ndarray of shape (12, 12, 9) of bools
        3D array of occupied space.
    position : iterable of length 3 of floats
        Position.
    rotation : np.ndarray of shape (3, 3) of np.float32
        Rotational matrix.
    power : int, optional
        Relative destructive power.

    Attributes
    ----------
    addr : Tuple[str, int]
        IP address (host, port).
    power : int
        Relative destructive power.
    space : np.ndarray of shape (12, 12, 9) of bools
        3D array of occupied space.
    x, y, z : floats
        Position.
    rot : np.ndarray of shape (3, 3) of np.float32
        Rotational matrix.
    """
    def __init__(self, address, space, position, rotation, power=SHARD_LIFE):
        self.addr = address
        self.power = power
        self.space = space
        self.pos = position
        self.rot = rotation

    @property
    def pos(self) -> np.float32:
        """Position in a NumPy array."""
        return np.float32([self.x, self.y, self.z])

    @pos.setter
    def pos(self, position):
        x, y, z = position
        self.x = x % 12
        self.y = y % 12
        self.z = z % 9

    @property
    def forward(self) -> np.float32:
        """Direction in a NumPy array."""
        return self.rot[-1]

    def should_bounce(self, x=None, y=None, z=None) -> bool:
        """Return whether it should bounce at (x, y, z)."""
        if x is None: x = self.x
        if y is None: y = self.y
        if z is None: z = self.z
        return not placeable(self.space, x, y, z, r=RSHARD)

    def update(self, fps, picos):
        """Update states."""
        bounced = False
        for axis, value in zip('xyz', self.pos+self.forward/fps*SHARD_SPEED):
            if self.should_bounce(**{axis: value}):
                self.rot = self.rot @ INV[axis]
                bounced = True
        self.pos += self.forward / fps * SHARD_SPEED
        self.power -= bounced

        for pico in picos:
            if norm(pico.pos - self.pos) < RCOLL:
                pico.health -= self.power / SHARD_LIFE / RPS
                self.power = 0

    def sync(self, position, rotation, power) -> None:
        """Synchronize states received from other peers."""
        self.pos, self.rot, self.power = position, rotation, power


class Pico:
    """Game character, which is represented as a regular tetrahedron
    whose circumscribed sphere's radius is RPICO.

    Parameters
    ----------
    address : Tuple[str, int]
        IP address (host, port).
    space : np.ndarray of shape (12, 12, 9) of bools
        3D array of occupied space.
    health : float, optional
        Pico relative health.
    position : iterable of length 3 of floats, optional
        Position.
    rotation : np.ndarray of shape (3, 3) of np.float32, optional
        Rotational matrix.

    Attributes
    ----------
    addr : Tuple[str, int]
        IP address (host, port).
    space : np.ndarray of shape (12, 12, 9) of bools
        3D array of occupied space.
    health : float
        Pico relative health.
    x, y, z : floats
        Position.
    rot : np.ndarray of shape (3, 3) of np.float32
        Rotational matrix.
    shards : Dict[int, Shard]
        Active shards.
    recoil_u : np.ndarray of length 3 of np.float32
        Recoil direction (unit vector).
    recoil_t : float
        Recoil time left in seconds.
    fps : float
        Currently rendered frames per second.
    """
    def __init__(self, address, space,
                 health=1.0, position=None, rotation=None):
        self.addr = address
        self.space = space
        self.health = health

        if position is None:
            x, y, z = random()*12, random()*12, random()*9
            while not self.placeable(x, y, z):
                x, y, z = random()*12, random()*12, random()*9
            self.x, self.y, self.z = x, y, z
        else:
            self.x, self.y, self.z = position

        if rotation is None:
            self.rot = INVZ
            self.rotate(random()*pi*2, random()*pi*2)
        else:
            self.rot = rotation

        self.shards = {}
        self.recoil_u, self.recoil_t = np.float32([0, 0, 0]), 0.0
        self.fps = 60.0

    @property
    def dead(self) -> bool:
        """Whether the pico is dead."""
        return self.health < 0

    @property
    def forward(self) -> np.float32:
        """Direction in a NumPy array."""
        return self.rot[-1]

    @property
    def pos(self) -> np.float32:
        """Position in a NumPy array."""
        return np.float32([self.x, self.y, self.z])

    @pos.setter
    def pos(self, position):
        self.x, self.y, self.z = position

    def sync(self, health, position, rotation, shards):
        """Synchronize states received from other peers."""
        self.health, self.pos, self.rot = health, position, rotation
        for i, t in shards.items():
            pos, rot, power = t
            try:
                self.shards[i].sync(pos, rot, power)
            except KeyError:
                self.shards[i] = Shard(self.addr, self.space, pos, rot, power)

    def placeable(self, x=None, y=None, z=None) -> bool:
        """Return whether it can be placed at (x, y, z)."""
        if x is None: x = self.x
        if y is None: y = self.y
        if z is None: z = self.z
        return placeable(self.space, x, y, z, RPICO)

    def rotate(self, magnitude, direction):
        """Rotate by the given magnitude and direction."""
        self.rot = rot33(magnitude, direction) @ self.rot

    def lookat(self, target):
        """Look at the given target."""
        # The matrix multiplication is in the following order
        # because matrices are perceived differently by numpy and glsl.
        right, upward, forward = normalized(*(self.rot @ (target - self.pos)))
        # I don't understand why we need to flip
        # the right coordinate here, but since it works...
        self.rotate(acos(forward), atan2(upward, -right))

    def update(self, right=0, upward=0, forward=0):
        """Recover health point and try to move in the given direction."""
        if self.dead: return self.__init__(self.addr, self.space)   # respawn
        dt = 1.0 / self.fps
        self.health = min(1.0, self.health + log10(self.health+1)*dt)

        direction = normalized(right, upward, forward) @ self.rot
        if self.recoil_t:
            direction += self.recoil_u * self.recoil_t * RPS
            self.recoil_t = max(self.recoil_t - dt, 0.0)
        x, y, z = self.pos + direction*dt*PICO_SPEED
        if self.placeable(x=x): self.x = x % 12
        if self.placeable(y=y): self.y = y % 12
        if self.placeable(z=z): self.z = z % 9

    def add_shard(self, pos, rot):
        """Add a shard at pos with rotation rot."""
        self.shards[max(self.shards, default=0) + 1] = Shard(
            self.addr, self.space, pos-self.recoil_u*RPICO, rot)

    def shoot(self, backward=False):
        """Shoot in the forward direction unless specified otherwise."""
        if self.recoil_t or self.dead: return
        self.recoil_t = 1.0 / RPS
        if backward:
            self.recoil_u = self.forward
            self.add_shard(-self.pos, -self.rot)
        else:
            self.recoil_u = -self.forward
            self.add_shard(self.pos, self.rot)
