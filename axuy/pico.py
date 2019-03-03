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

from math import pi, sqrt
from random import random

import numpy as np
from pyrr import matrix33

from .misc import normalized, placeable

INVX = np.float32([[-1, 0, 0], [0, 1, 0], [0, 0, 1]])
INVY = np.float32([[1, 0, 0], [0, -1, 0], [0, 0, 1]])
INVZ = np.float32([[1, 0, 0], [0, 1, 0], [0, 0, -1]])

# Magic numbers. Do not try to figure out what they mean.
PICO_SPEED = (1+sqrt(5)) / 2            # in unit/s
SHARD_SPEED = PICO_SPEED * 243**0.25    # in unit/s
SHARD_LIFE = 3  # bounces


class Shard:
    """Fragment broken or shot out of a Picobot, which is a regular
    octahedron whose circumscribed sphere's radius is 1/12 unit.

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
        return not placeable(self.space, x, y, z, r=1/12)

    def update(self, fps):
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

    def sync(self, position, rotation, power) -> None:
        """Synchronize state received from other peers."""
        self.pos, self.rot, self.power = position, rotation, power


class Picobot:
    """Game character, which is represented as a regular tetrahedron
    whose circumscribed sphere's radius is 1/4 unit.

    Parameters
    ----------
    address : (str, int)
        IP address (host, port).
    space : np.ndarray of shape (12, 12, 9) of bools
        3D array of occupied space.
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
    x, y, z : floats
        Position.
    rot : np.ndarray of shape (3, 3) of np.float32
        Rotational matrix.
    shards : dict of Shard
        Active shards.
    fps : float
        Currently rendered frames per second.
    """
    def __init__(self, address, space, position=None, rotation=None):
        self.addr = address
        self.space = space

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
        self.fps = 60.0

    @property
    def pos(self):
        """Position in a NumPy array."""
        return np.float32([self.x, self.y, self.z])

    @pos.setter
    def pos(self, position):
        self.x, self.y, self.z = position

    def sync(self, position, rotation, shards) -> None:
        """Synchronize state received from other peers."""
        self.pos, self.rot = position, rotation
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
        return placeable(self.space, x, y, z, 1/4)

    def rotate(self, yaw, pitch):
        """Rotate yaw radians around y-axis
        and pitch radians around x-axis.
        """
        self.rot = (matrix33.create_from_x_rotation(pitch)
                    @ matrix33.create_from_y_rotation(yaw) @ self.rot)

    def move(self, right=0, upward=0, forward=0):
        """Try to move in the given direction."""
        direction = normalized(right, upward, forward) @ self.rot
        x, y, z = self.pos + direction/self.fps*PICO_SPEED
        if self.placeable(x=x): self.x = x % 12
        if self.placeable(y=y): self.y = y % 12
        if self.placeable(z=z): self.z = z % 9

    def shoot(self):
        self.shards[max(self.shards, default=0) + 1] = Shard(
            self.addr, self.space, self.pos, self.rot)
