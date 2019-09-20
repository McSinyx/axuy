# pico.py - game characters
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

__doc__ = 'Axuy module for character class'

from itertools import combinations
from math import log10, pi, sqrt
from random import random

import numpy as np
from pyrr import matrix33

from .misc import norm, normalized, placeable

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

PICO_SPEED = 1 + sqrt(5)        # in unit/s
SHARD_SPEED = PICO_SPEED * 2    # in unit/s
SHARD_LIFE = 3  # bounces
RPS = 6     # rounds per second


class Shard:
    """Fragment broken or shot out of a Picobot, which is a regular
    octahedron whose circumscribed sphere's radius is RSHARD.

    Parameters
    ----------
    address : (str, int)
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
    addr : (str, int)
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
    def pos(self):
        """Position in a NumPy array."""
        return np.float32([self.x, self.y, self.z])

    @pos.setter
    def pos(self, position):
        x, y, z = position
        self.x = x % 12
        self.y = y % 12
        self.z = z % 9

    @property
    def forward(self):
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
        x, y, z = self.pos + self.forward/fps*SHARD_SPEED
        bounced = False
        if self.should_bounce(x=x):
            self.rot = self.rot @ INVX
            bounced = True
        if self.should_bounce(y=y):
            self.rot = self.rot @ INVY
            bounced = True
        if self.should_bounce(z=z):
            self.rot = self.rot @ INVZ
            bounced = True
        self.pos += self.forward / fps * SHARD_SPEED
        self.power -= bounced

        for pico in picos:
            distance = norm(pico.pos - self.pos)
            if distance < RCOLL:
                pico.health -= self.power * RCOLL
                self.power = 0

    def sync(self, position, rotation, power) -> None:
        """Synchronize state received from other peers."""
        self.pos, self.rot, self.power = position, rotation, power


class Picobot:
    """Game character, which is represented as a regular tetrahedron
    whose circumscribed sphere's radius is RPICO.

    Parameters
    ----------
    address : (str, int)
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
    addr : (str, int)
        IP address (host, port).
    space : np.ndarray of shape (12, 12, 9) of bools
        3D array of occupied space.
    health : float
        Pico relative health.
    x, y, z : floats
        Position.
    rot : np.ndarray of shape (3, 3) of np.float32
        Rotational matrix.
    shards : dict of Shard
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
    def forward(self):
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
        """Synchronize state received from other peers."""
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

    def rotate(self, yaw, pitch):
        """Rotate yaw radians around y-axis
        and pitch radians around x-axis.
        """
        self.rot = (matrix33.create_from_x_rotation(pitch, dtype=np.float32)
                    @ matrix33.create_from_y_rotation(yaw, dtype=np.float32)
                    @ self.rot)

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

    def shoot(self, backward=False):
        """Shoot in the forward direction unless specified otherwise."""
        if self.recoil_t or self.dead: return
        self.recoil_t = 1.0 / RPS
        index = max(self.shards, default=0) + 1
        if backward:
            self.recoil_u = self.forward
            self.shards[index] = Shard(self.addr, self.space,
                                       -self.pos - self.recoil_u*RPICO,
                                       -self.rot)
        else:
            self.recoil_u = -self.forward
            self.shards[index] = Shard(self.addr, self.space,
                                       self.pos - self.recoil_u*RPICO,
                                       self.rot)
