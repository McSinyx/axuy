# view.py - maintain view on game world
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

__doc__ = 'Axuy module for map class'

from itertools import product
from math import sqrt

import glfw
import moderngl
import numpy as np
from pyrr import Matrix44

from .misc import abspath, color, neighbors, sign

FOV_MIN = 30
FOV_MAX = 120
FOV_INIT = (FOV_MIN+FOV_MAX) / 2

OXY = np.float32([[0, 0, 0], [1, 0, 0], [1, 1, 0],
                  [1, 1, 0], [0, 1, 0], [0, 0, 0]])
OYZ = np.float32([[0, 0, 0], [0, 1, 0], [0, 1, 1],
                  [0, 1, 1], [0, 0, 1], [0, 0, 0]])
OZX = np.float32([[0, 0, 0], [1, 0, 0], [1, 0, 1],
                  [1, 0, 1], [0, 0, 1], [0, 0, 0]])

TETRAVERTICES = np.float32([[0, sqrt(8), -1], [sqrt(6), -sqrt(2), -1],
                            [0, 0, 3], [-sqrt(6), -sqrt(2), -1]]) / 12
TETRAINDECIES = np.int32([0, 1, 2, 3, 1, 2, 0, 3, 2, 0, 3, 1])

OCTOVERTICES = np.float32([[-1, 0, 0], [0, -1, 0], [0, 0, -1],
                           [0, 1, 0], [0, 0, 1], [1, 0, 0]]) / 12
OCTOINDECIES = np.int32([0, 1, 2, 0, 1, 4, 3, 0, 2, 3, 0, 4,
                         2, 1, 5, 4, 1, 5, 2, 5, 3, 4, 5, 3])

with open(abspath('shaders/map.vert')) as f: MAP_VERTEX = f.read()
with open(abspath('shaders/map.frag')) as f: MAP_FRAGMENT = f.read()
with open(abspath('shaders/pico.vert')) as f: PICO_VERTEX = f.read()
with open(abspath('shaders/pico.frag')) as f: PICO_FRAGMENT = f.read()


class View:
    """World map and camera placement.
    (Documentation below is not completed.)

    Parameters
    ----------
    mapid : iterable of length 48 of ints
        order of nodes to sort map.npy.
    context : moderngl.Context
        OpenGL context from which ModernGL objects are created.

    Attributes
    ----------
    space : np.ndarray of shape (12, 12, 9) of bools
        3D array of occupied space.
    maprog : moderngl.Program
        Processed executable code in GLSL.
    mapva : moderngl.VertexArray
        Vertex data of the map.
    camera : Picobot
        Protagonist whose view is the camera.
    """

    def __init__(self, pico, width, height, space):
        # Create GLFW window
        if not glfw.init(): raise RuntimeError('Failed to initialize GLFW!')
        glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
        glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
        glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
        glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, True)
        self.window = glfw.create_window(width, height, 'Axuy', None, None)
        if not self.window:
            glfw.terminate()
            raise RuntimeError('Failed to create glfw window!')

        self.camera = pico
        self.picos = {'self': pico}
        self.last_time = glfw.get_time()    # to keep track of FPS

        # Window's rendering and event-handling configuration
        glfw.make_context_current(self.window)
        glfw.swap_interval(1)
        glfw.set_input_mode(self.window, glfw.CURSOR, glfw.CURSOR_DISABLED)
        glfw.set_input_mode(self.window, glfw.STICKY_KEYS, True)
        glfw.set_cursor_pos_callback(self.window, self.camera.look)
        self.fov = FOV_INIT
        glfw.set_scroll_callback(self.window, self.zoom)

        # Create OpenGL context
        self.context = context = moderngl.create_context()
        context.enable(moderngl.BLEND)
        context.enable(moderngl.DEPTH_TEST)

        self.space, vertices = space, []
        for (x, y, z), occupied in np.ndenumerate(self.space):
            if self.space[x][y][z-1] ^ occupied:
                vertices.extend(i+j for i,j in product(neighbors(x,y,z), OXY))
            if self.space[x-1][y][z] ^ occupied:
                vertices.extend(i+j for i,j in product(neighbors(x,y,z), OYZ))
            if self.space[x][y-1][z] ^ occupied:
                vertices.extend(i+j for i,j in product(neighbors(x,y,z), OZX))

        self.maprog = context.program(vertex_shader=MAP_VERTEX,
                                      fragment_shader=MAP_FRAGMENT)
        self.maprog['bg'].write(color('Background').tobytes())
        self.maprog['color'].write(color('Aluminium').tobytes())
        mapvb = context.buffer(np.stack(vertices).astype(np.float32).tobytes())
        self.mapva = context.simple_vertex_array(self.maprog, mapvb, 'in_vert')

        self.prog = context.program(vertex_shader=PICO_VERTEX,
                                    fragment_shader=PICO_FRAGMENT)
        pvb = [(context.buffer(TETRAVERTICES.tobytes()), '3f', 'in_vert')]
        pib = context.buffer(TETRAINDECIES.tobytes())
        self.pva = context.vertex_array(self.prog, pvb, pib)

        self.should_close = None

    def zoom(self, window, xoffset, yoffset):
        """Adjust FOV according to vertical scroll."""
        self.fov += yoffset
        if self.fov < FOV_MIN: self.fov = FOV_MIN
        if self.fov > FOV_MAX: self.fov = FOV_MAX

    @property
    def pos(self):
        """Camera position in a NumPy array."""
        return self.camera.pos

    @property
    def right(self):
        """Camera right direction."""
        return self.camera.rotation[0]

    @property
    def upward(self):
        """Camera upward direction."""
        return self.camera.rotation[1]

    @property
    def forward(self):
        """Camera forward direction."""
        return self.camera.rotation[2]

    @property
    def is_running(self):
        """GLFW window status."""
        return not glfw.window_should_close(self.window)

    def is_pressed(self, *keys):
        """Return whether given keys are pressed."""
        return any(glfw.get_key(self.window, k) == glfw.PRESS for k in keys)

    def render(self, obj, va):
        """Render the obj and its images in bounded 3D space."""
        rotation = Matrix44.from_matrix33(obj.rotation)
        i, j, k = map(sign, self.pos - obj.pos)
        for position in product(*zip(obj.pos, obj.pos + [i*12, j*12, k*9])):
            model = rotation @ Matrix44.from_translation(position)
            self.prog['model'].write(model.astype(np.float32).tobytes())
            self.prog['color'].write(color('Background').tobytes())
            va.render(moderngl.LINES)
            self.prog['color'].write(color('Plum').tobytes())
            va.render(moderngl.TRIANGLES)

    def render_pico(self, pico):
        """Render the pico and its images in bounded 3D space."""
        rotation = Matrix44.from_matrix33(pico.rotation)
        i, j, k = map(sign, self.pos - pico.pos)
        for position in product(*zip(pico.pos, pico.pos + [i*12, j*12, k*9])):
            model = rotation @ Matrix44.from_translation(position)
            self.prog['model'].write(model.astype(np.float32).tobytes())
            self.prog['color'].write(color('Background').tobytes())
            self.pva.render(moderngl.LINES)
            self.prog['color'].write(color('Plum').tobytes())
            self.pva.render(moderngl.TRIANGLES)

    def update(self):
        """Handle input, update GLSL programs and render the map."""
        # Character movements
        right, upward, forward = 0, 0, 0
        if self.is_pressed(glfw.KEY_UP): forward += 1
        if self.is_pressed(glfw.KEY_DOWN): forward -= 1
        if self.is_pressed(glfw.KEY_LEFT): right -= 1
        if self.is_pressed(glfw.KEY_RIGHT): right += 1
        self.camera.move(right, upward, forward)

        # Renderings
        width, height = glfw.get_window_size(self.window)
        self.context.viewport = 0, 0, width, height
        self.context.clear(*color('Background'))

        visibility = sqrt(1800 / self.fov)
        projection = Matrix44.perspective_projection(self.fov, width/height,
                                                     3E-3, visibility)
        view = Matrix44.look_at(self.pos, self.pos + self.forward, self.upward)
        vp = (view @ projection).astype(np.float32).tobytes()

        self.maprog['visibility'].write(np.float32(visibility).tobytes())
        self.maprog['camera'].write(self.pos.tobytes())
        self.maprog['mvp'].write(vp)
        self.mapva.render(moderngl.TRIANGLES)

        self.prog['visibility'].write(np.float32(visibility).tobytes())
        self.prog['camera'].write(self.pos.tobytes())
        self.prog['vp'].write(vp)
        for pico in self.picos.copy().values():
            if pico is not self.camera: self.render_pico(pico)
        glfw.swap_buffers(self.window)

        # Resetting cursor position and event queues
        glfw.set_cursor_pos(self.window, width/2, height/2)
        glfw.poll_events()

    def close(self):
        """Close window."""
        glfw.terminate()
