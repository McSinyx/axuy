# main.py - start game and main loop
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

from random import shuffle

import glfw
import moderngl

from .misc import hex2f4
from .view import View

FOV_INIT = 90
FOV_MIN = 30
FOV_MAX = 120


def main():
    """Create window, OpenGL context and start main loop."""
    if not glfw.init():
        print('Failed to initialize glfw!')
        return

    glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
    glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
    glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
    glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, True)
    window = glfw.create_window(640, 480, 'Axuy', None, None)
    if not window:
        print('Failed to create glfw window!')
        glfw.terminate()
        return

    glfw.make_context_current(window)
    glfw.swap_interval(1)
    glfw.set_input_mode(window, glfw.CURSOR, glfw.CURSOR_DISABLED)
    glfw.set_input_mode(window, glfw.STICKY_KEYS, True)

    context = moderngl.create_context()
    context.enable(moderngl.BLEND)

    fov = FOV_INIT
    def zoom(window, xoffset, yoffset):
        """Adjust FOV according to vertical scroll."""
        nonlocal fov
        fov += yoffset
        if fov < FOV_MIN: fov = FOV_MIN
        if fov > FOV_MAX: fov = FOV_MAX
    glfw.set_scroll_callback(window, zoom)

    mapid = list(range(48))
    shuffle(mapid)
    view = View(mapid, context)
    mypico = view.camera
    glfw.set_cursor_pos_callback(window, mypico.look)

    last_time = glfw.get_time()
    while not glfw.window_should_close(window):
        next_time = glfw.get_time()
        mypico.fps = 1 / (next_time-last_time)
        last_time = next_time

        if glfw.get_key(window, glfw.KEY_UP) == glfw.PRESS:
            mypico.move(forward=1)
        if glfw.get_key(window, glfw.KEY_DOWN) == glfw.PRESS:
            mypico.move(forward=-1)
        if glfw.get_key(window, glfw.KEY_LEFT) == glfw.PRESS:
            mypico.move(right=-1)
        if glfw.get_key(window, glfw.KEY_RIGHT) == glfw.PRESS:
            mypico.move(right=1)

        width, height = glfw.get_window_size(window)
        context.viewport = 0, 0, width, height
        context.clear(*hex2f4('2e3436'))
        view.render(width, height, fov)

        glfw.swap_buffers(window)
        glfw.set_cursor_pos(window, width/2, height/2)
        glfw.poll_events()

    glfw.terminate()
