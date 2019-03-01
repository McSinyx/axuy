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

from math import pi
from random import random

import glfw
import numpy as np
from pyrr import matrix33

from .misc import normalized, placeable

INVX = np.float32([[-1, 0, 0], [0, 1, 0], [0, 0, 1]])
INVY = np.float32([[1, 0, 0], [0, -1, 0], [0, 0, -1]])
INVZ = np.float32([[1, 0, 0], [0, 1, 0], [0, 0, -1]])

PICO_SPEED = 2                          # in unit/s
SHARD_SPEED = PICO_SPEED * 243**0.25    # in unit/s
SHARD_LIFE = 11 / SHARD_SPEED   # in seconds


class Picobot:
    """Game character, which is represented as a regular tetrahedron
    whose circumscribed sphere's radius is 1/4 unit.

    Parameters
    ----------
    space : np.ndarray of shape (12, 12, 9) of bools
        3D array of occupied space.
    position : iterable of length 3 of floats, optional
        Position.
    rotation : np.ndarray of shape (3, 3) of np.float32, optional
        Rotational matrix.

    Attributes
    ----------
    space : np.ndarray of shape (12, 12, 9) of bools
        3D array of occupied space.
    x, y, z : floats
        Position.
    rot : np.ndarray of shape (3, 3) of np.float32
        Rotational matrix.
    fps : float
        Currently rendered frames per second.
    """
    def __init__(self, space, position=None, rotation=None):
        self.space = space
        if position is None:
            x, y, z = random()*12, random()*12, random()*9
            while not self.empty(x, y, z):
                x, y, z = random()*12, random()*12, random()*9
            self.x, self.y, self.z = x, y, z
        else:
            self.x, self.y, self.z = position

        if rotation is None:
            self.rot = INVZ
            self.rotate(random()*pi*2, random()*pi*2)
        else:
            self.rot = rotation

        self.fps = 60.0

    @property
    def pos(self):
        """Position in a NumPy array."""
        return np.float32([self.x, self.y, self.z])

    @pos.setter
    def pos(self, position):
        self.x, self.y, self.z = position

    @property
    def state(self):
        """Position and rotation."""
        return self.pos, self.rot

    def sync(self, position, rotation) -> None:
        """Synchronize state received from other peers."""
        self.pos = position
        self.rot = rotation

    def placeable(self, x, y, z) -> bool:
        """Return whether it can be placed at (x, y, z)."""
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
        if self.placeable(x, self.y, self.z): self.x = x % 12
        if self.placeable(self.x, y, self.z): self.y = y % 12
        if self.placeable(self.x, self.y, z): self.z = z % 9


class Shard:
    """Fragment broken or shot out of a Picobot, which is a regular
    octahedron whose circumscribed sphere's radius is 1/12 unit.

    Parameters
    ----------
    space : np.ndarray of shape (12, 12, 9) of bools
        3D array of occupied space.
    position : iterable of length 3 of floats
        Position.
    rotation : np.ndarray of shape (3, 3) of np.float32
        Rotational matrix.
    fps : float, optional
        Currently rendered frames per second.

    Attributes
    ----------
    space : np.ndarray of shape (12, 12, 9) of bools
        3D array of occupied space.
    x, y, z : floats
        Position.
    rot : np.ndarray of shape (3, 3) of np.float32
        Rotational matrix.
    power : float
        Relative destructive power to the original.
    fps : float
        Currently rendered frames per second.
    """
    def __init__(self, space, position, rotation, fps=60.0):
        self.space = space
        self.x, self.y, self.z = position
        self.rot = rotation
        self.fps = fps

    @property
    def pos(self):
        """Position in a NumPy array."""
        return np.float32([self.x, self.y, self.z])

    @pos.setter
    def pos(self, position):
        self.x, self.y, self.z = position

    @property
    def forward(self):
        """Direction in a NumPy array."""
        return self.rot[-1]

    def placeable(self, x, y, z) -> bool:
        """Return whether it can be placed at (x, y, z)."""
        return placeable(self.space, x, y, z, r=1/12)

    def update(self):
        """Update states."""
        x, y, z = self.pos + self.forward/self.fps*SHARD_SPEED
        if not self.placeable(x, self.y, self.z): self.rot = self.rot @ INVX
        if not self.placeable(self.x, y, self.z): self.rot = self.rot @ INVY
        if not self.placeable(self.x, self.y, z): self.rot = self.rot @ INVZ
        self.pos += self.forward / self.fps * SHARD_SPEED
        return self
