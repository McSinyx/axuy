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

BASE = np.float32([[1, 0, 0], [0, 1, 0], [0, 0, -1]])
SPEED = 2
MOUSE_SPEED = 1/8


class Picobot:
    """Game character.

    Parameters
    ----------
    space : np.ndarray of shape (12, 12, 9) of bools
        3D array of occupied space.
    pos : iterable of length 3 of floats
        Position.
    rotation : np.ndarray of shape (3, 3) of np.float32
        Rotational matrix.

    Attributes
    ----------
    space : np.ndarray of shape (12, 12, 9) of bools
        3D array of occupied space.
    x, y, z : floats
        Position.
    rotation : np.ndarray of shape (3, 3) of np.float32
        Rotational matrix.
    fps : float
        Currently rendered frames per second.
    """

    def __init__(self, space, pos=None, rotation=None):
        self.space = space
        if pos is None:
            x, y, z = random()*12, random()*12, random()*9
            while not self.empty(x, y, z):
                x, y, z = random()*12, random()*12, random()*9
            self.x, self.y, self.z = x, y, z
        else:
            self.x, self.y, self.z = pos

        if rotation is None:
            self.rotation = BASE
            self.rotate(random()*pi*2, random()*pi*2)
        else:
            self.rotation = rotation

        self.fps = 60.0

    def empty(self, x, y, z) -> bool:
        """Return weather a Picobot can be placed at (x, y, z)."""
        if self.space[int((x-1/4) % 12)][int(y % 12)][int(z % 9)]: return False
        if self.space[int((x+1/4) % 12)][int(y % 12)][int(z % 9)]: return False
        if self.space[int(x % 12)][int((y-1/4) % 12)][int(z % 9)]: return False
        if self.space[int(x % 12)][int((y+1/4) % 12)][int(z % 9)]: return False
        if self.space[int(x % 12)][int(y % 12)][int((z-1/4) % 9)]: return False
        if self.space[int(x % 12)][int(y % 12)][int((z+1/4) % 9)]: return False
        return True

    def rotate(self, yaw, pitch):
        """Rotate yaw radians around y-axis
        and pitch radians around x-axis.
        """
        self.rotation = (matrix33.create_from_x_rotation(pitch)
                         @ matrix33.create_from_y_rotation(yaw) @ self.rotation)

    def move(self, right=0, upward=0, forward=0):
        """Try to move in the given direction."""
        dr = [right, upward, forward] @ self.rotation / self.fps * SPEED
        x, y, z = [self.x, self.y, self.z] + dr
        if self.empty(x, self.y, self.z): self.x = x % 12
        if self.empty(self.x, y, self.z): self.y = y % 12
        if self.empty(self.x, self.y, z): self.z = z % 9

    def look(self, window, xpos, ypos):
        """Look according to cursor position.

        Present as a callback for GLFW CursorPos event.
        """
        center = np.float32(glfw.get_window_size(window)) / 2
        self.rotate(*((center - [xpos, ypos]) / self.fps * MOUSE_SPEED))
