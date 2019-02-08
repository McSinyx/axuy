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

from dataclasses import dataclass

import glfw
import numpy as np
from pyrr import matrix33

SPEED = 2
MOUSE_SPEED = 1


@dataclass
class Picobot:
    x: float
    y: float
    z: float
    space: np.ndarray
    rotation: np.ndarray = np.float32([[1, 0, 0], [0, 1, 0], [0, 0, -1]])
    fps: float = 60.0

    @property
    def pos(self):
        """Return position in a numpy array."""
        return np.float32([self.x, self.y, self.z])

    @pos.setter
    def pos(self, postion):
        """Set camera postion."""
        self.x, self.y, self.z = postion

    def move(self, right=0, upward=0, forward=0):
        """Move in the given direction."""
        dr = [right, upward, forward] @ self.rotation / self.fps * SPEED
        x, y, z = self.pos + dr
        if not self.space[int(x%12)][int(y%12)][int(z%9)]: self.pos += dr
        self.pos = self.x % 12, self.y % 12, self.z % 9

    def look(self, window, xpos, ypos):
        """Look according to cursor position.

        Present as a callback for GLFW CursorPos event.
        """
        center = np.float32(glfw.get_window_size(window)) / 2
        yaw, pitch = (center - [xpos, ypos]) / self.fps * MOUSE_SPEED
        self.rotation = (matrix33.create_from_y_rotation(yaw) @
                         matrix33.create_from_x_rotation(pitch) @ self.rotation)
