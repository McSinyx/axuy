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

from configparser import ConfigParser
from itertools import product
from os.path import join as pathjoin, pathsep
from math import degrees, log2, radians, sqrt
from random import randint
from re import IGNORECASE, match
from warnings import warn

import glfw
import moderngl
import numpy as np
from appdirs import AppDirs
from PIL import Image
from pyrr import Matrix44

from .pico import SHARD_LIFE, Picobot
from .misc import abspath, color, neighbors

CONTROL_ALIASES = (('Move left', 'left'), ('Move right', 'right'),
                   ('Move forward', 'forward'), ('Move backward', 'backward'),
                   ('Primary', '1st'))
MOUSE_PATTERN = 'MOUSE_BUTTON_[1-{}]'.format(glfw.MOUSE_BUTTON_LAST + 1)
INVALID_CONTROL_ERR = '{}: {} is not recognized as a valid control key'
GLFW_VER_WARN = 'Your GLFW version appear to be lower than 3.3, '\
                'which might cause stuttering camera rotation.'

ZMIN, ZMAX = -1.0, 1.0
CONWAY = 1.303577269034
EDGE_BRIGHTNESS = 1/3

QUAD = np.float32([-1, -1, 1, -1, -1, 1, -1, 1, 1, -1, 1, 1]).tobytes()
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
with open(abspath('shaders/pico.vert')) as f: PICO_VERTEX = f.read()
with open(abspath('shaders/line.geom')) as f: LINE_GEOMETRY = f.read()
with open(abspath('shaders/triangle.geom')) as f: TRIANGLE_GEOMETRY = f.read()
with open(abspath('shaders/world.frag')) as f: WORLD_FRAGMENT = f.read()

with open(abspath('shaders/tex.vert')) as f: TEX_VERTEX = f.read()
with open(abspath('shaders/sat.frag')) as f: SAT_FRAGMENT = f.read()
with open(abspath('shaders/gaussh.vert')) as f: GAUSSH_VERTEX = f.read()
with open(abspath('shaders/gaussv.vert')) as f: GAUSSV_VERTEX = f.read()
with open(abspath('shaders/gauss.frag')) as f: GAUSS_FRAGMENT = f.read()
with open(abspath('shaders/comb.frag')) as f: COMBINE_FRAGMENT = f.read()


class ConfigReader:
    """Object reading and processing command-line arguments
    and INI configuration file for Axuy.

    Attributes
    ----------
    config : ConfigParser
        INI configuration file parser.
    host : str
        Host to bind the peer to.
    port : int
        Port to bind the peer to.
    seeder : str
        Address of the peer that created the map.
    size : (int, int)
        GLFW window resolution.
    vsync : bool
        Vertical synchronization.
    zmlvl : float
        Zoom level.
    key, mouse : dict of (str, int)
        Input control.
    mouspeed : float
        Relative camera rotational speed.
    zmspeed : float
        Zoom speed, in scroll steps per zoom range.
    """

    def __init__(self):
        dirs = AppDirs(appname='axuy', appauthor=False, multipath=True)
        parents = dirs.site_config_dir.split(pathsep)
        parents.append(dirs.user_config_dir)
        filenames = [pathjoin(parent, 'settings.ini') for parent in parents]

        self.config = ConfigParser()
        self.config.read(abspath('settings.ini'))    # default configuration
        self.config.read(filenames)

    # Fallback to None when attribute is missing
    def __getattr__(self, name): return None

    @property
    def fov(self) -> float:
        """Horizontal field of view in degrees."""
        if self.zmlvl is None: return None
        return degrees(2 ** self.zmlvl)

    @fov.setter
    def fov(self, value):
        rad = radians(value)
        if rad < 0.5:
            warn('Too narrow FOV, falling back to the minimal value.')
            self.zmlvl = -1.0
            return
        elif rad > 2:
            warn('Too wide FOVm falling back to the maximal value.')
            self.zmlvl = 1.0
            return
        self.zmlvl = log2(rad)

    @property
    def mouspeed(self) -> float:
        """Relative mouse speed."""
        # Standard to radians per inch for a 800 DPI mouse, at FOV of 60
        return self._mouspeed / 800

    @mouspeed.setter
    def mouspeed(self, value):
        self._mouspeed = value

    def parse(self):
        """Parse configurations."""
        self.size = (self.config.getint('Graphics', 'Screen width'),
                     self.config.getint('Graphics', 'Screen height'))
        self.vsync = self.config.getboolean('Graphics', 'V-sync')
        self.fov = self.config.getfloat('Graphics', 'FOV')
        self.host = self.config.get('Peer', 'Host')
        self.port = self.config.getint('Peer', 'Port')
        self.mouspeed = self.config.getfloat('Control', 'Mouse speed')
        self.zmspeed = self.config.getfloat('Control', 'Zoom speed')

        self.key, self.mouse = {}, {}
        for cmd, alias in CONTROL_ALIASES:
            i = self.config.get('Control', cmd)
            if match(MOUSE_PATTERN, i, flags=IGNORECASE):
                self.mouse[alias] = getattr(glfw, i.upper())
                continue
            try:
                self.key[alias] = getattr(glfw, 'KEY_{}'.format(i.upper()))
            except AttributeError:
                raise ValueError(INVALID_CONTROL_ERR.format(cmd, i))

    def read_args(self, arguments):
        """Read and parse a argparse.ArgumentParser.Namespace."""
        for option in ('size', 'vsync', 'fov', 'mouspeed', 'zmspeed',
                       'host', 'port', 'seeder'):
            value = getattr(arguments, option)
            if value is not None: setattr(self, option, value)


class View:
    """World map and camera placement.

    Parameters
    ----------
    address : (str, int)
        IP address (host, port).
    camera : Picobot
        Protagonist whose view is the camera.
    space : np.ndarray of shape (12, 12, 9) of bools
        3D array of occupied space.
    size : (int, int)
        GLFW window resolution.
    vsync : bool
        Vertical synchronization.
    ctl : dict of (str, int)
        Input control.
    lock : RLock
        Compound data lock to avoid size change during iteration.

    Attributes
    ----------
    addr : (str, int)
        IP address (host, port).
    space : np.ndarray of shape (12, 12, 9) of bools
        3D array of occupied space.
    camera : Picobot
        Protagonist whose view is the camera.
    picos : dict of (address, Picobot)
        Enemies characters.
    colors : dict of (address, str)
        Color names of enemies.
    lock : RLock
        Compound data lock to avoid size change during iteration.
    window : GLFW window
    zmlvl : float
        Zoom level (from ZMIN to ZMAX).
    zmspeed : float
        Scroll steps per zoom range.
    mouspeed : float
        Relative camera rotational speed.
    context : moderngl.Context
        OpenGL context from which ModernGL objects are created.
    maprog : moderngl.Program
        Processed executable code in GLSL for map rendering.
    mapva : moderngl.VertexArray
        Vertex data of the map.
    prog2, prog3 : moderngl.Program
        Processed executable code in GLSL
        for rendering picobots and their shards.
    pva2, pva3 : moderngl.VertexArray
        Vertex data of picobots.
    sva2, sva3 : moderngl.VertexArray
        Vertex data of shards.
    pfilter : moderngl.VertexArray
        Vertex data for filtering highly saturated colors.
    gaussh, gaussv : moderngl.Program
        Processed executable code in GLSL for Gaussian blur.
    gausshva, gaussvva : moderngl.VertexArray
        Vertex data for Gaussian blur.
    fringe : moderngl.Program
        Processed executable code in GLSL for final combination
        of the bloom effect with additional chromatic aberration.
    combine : moderngl.VertexArray
        Vertex data for final combination of the bloom effect.
    fb, ping, pong : moderngl.Framebuffer
        Frame buffers for bloom-effect post-processing.
    last_time : float
        timestamp in seconds of the previous frame.
    """

    def __init__(self, address, camera, space, config, lock):
        # Create GLFW window
        if not glfw.init(): raise RuntimeError('Failed to initialize GLFW')
        glfw.window_hint(glfw.CLIENT_API, glfw.OPENGL_API)
        glfw.window_hint(glfw.CONTEXT_CREATION_API, glfw.NATIVE_CONTEXT_API)
        glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
        glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
        glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
        glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, True)
        glfw.window_hint(glfw.DEPTH_BITS, 24)
        width, height = config.size
        self.window = glfw.create_window(width, height, 'Axuy', None, None)
        if not self.window:
            glfw.terminate()
            raise RuntimeError('Failed to create GLFW window')
        self.key, self.mouse = config.key, config.mouse

        # Attributes for event-handling
        self.camera = camera
        self.picos = {address: camera}
        self.colors = {address: randint(0, 5)}
        self.last_time = glfw.get_time()
        self.lock = lock

        # Window's rendering and event-handling configuration
        glfw.set_window_icon(self.window, 1, Image.open(abspath('icon.png')))
        glfw.make_context_current(self.window)
        glfw.swap_interval(config.vsync)
        glfw.set_window_size_callback(self.window, self.resize)
        glfw.set_input_mode(self.window, glfw.CURSOR, glfw.CURSOR_DISABLED)
        glfw.set_input_mode(self.window, glfw.STICKY_KEYS, True)
        self.mouspeed = config.mouspeed
        glfw.set_cursor_pos_callback(self.window, self.look)
        self.zmspeed, self.zmlvl = config.zmspeed, config.zmlvl
        glfw.set_scroll_callback(self.window, self.zoom)
        glfw.set_mouse_button_callback(self.window, self.shoot)

        try:
            if glfw.raw_mouse_motion_supported():
                glfw.set_input_mode(self.window, glfw.RAW_MOUSE_MOTION, True)
        except AttributeError:
            warn(GLFW_VER_WARN, category=RuntimeWarning)

        # Create OpenGL context
        self.context = context = moderngl.create_context()
        context.enable_only(moderngl.DEPTH_TEST)

        # Map creation
        self.space, vertices = space, []
        for (x, y, z), occupied in np.ndenumerate(self.space):
            if self.space[x][y][z-1] ^ occupied:
                vertices.extend(i+j for i,j in product(neighbors(x,y,z), OXY))
            if self.space[x-1][y][z] ^ occupied:
                vertices.extend(i+j for i,j in product(neighbors(x,y,z), OYZ))
            if self.space[x][y-1][z] ^ occupied:
                vertices.extend(i+j for i,j in product(neighbors(x,y,z), OZX))

        # GLSL program and vertex array for map rendering
        self.maprog = context.program(vertex_shader=MAP_VERTEX,
                                      fragment_shader=WORLD_FRAGMENT)
        self.maprog['color'].write(bytes((0, 0, 128, 63) * 3))
        mapvb = context.buffer(np.stack(vertices).astype(np.float32).tobytes())
        self.mapva = context.simple_vertex_array(self.maprog, mapvb, 'in_vert')

        # GLSL programs and vertex arrays for picos and shards rendering
        pvb = [(context.buffer(TETRAVERTICES.tobytes()), '3f', 'in_vert')]
        pib = context.buffer(TETRAINDECIES.tobytes())
        svb = [(context.buffer(OCTOVERTICES.tobytes()), '3f', 'in_vert')]
        sib = context.buffer(OCTOINDECIES.tobytes())

        self.prog2 = context.program(vertex_shader=PICO_VERTEX,
                                     geometry_shader=LINE_GEOMETRY,
                                     fragment_shader=WORLD_FRAGMENT)
        self.pva2 = context.vertex_array(self.prog2, pvb, pib)
        self.sva2 = context.vertex_array(self.prog2, svb, sib)
        self.prog3 = context.program(vertex_shader=PICO_VERTEX,
                                     geometry_shader=TRIANGLE_GEOMETRY,
                                     fragment_shader=WORLD_FRAGMENT)
        self.pva3 = context.vertex_array(self.prog3, pvb, pib)
        self.sva3 = context.vertex_array(self.prog3, svb, sib)

        self.pfilter = context.simple_vertex_array(
            context.program(vertex_shader=TEX_VERTEX,
                            fragment_shader=SAT_FRAGMENT),
            context.buffer(QUAD), 'in_vert')
        self.gaussh = context.program(vertex_shader=GAUSSH_VERTEX,
                                      fragment_shader=GAUSS_FRAGMENT)
        self.gaussh['width'].value = 256
        self.gausshva = context.simple_vertex_array(
            self.gaussh, context.buffer(QUAD), 'in_vert')
        self.gaussv = context.program(vertex_shader=GAUSSV_VERTEX,
                                      fragment_shader=GAUSS_FRAGMENT)
        self.gaussv['height'].value = 256 * height / width
        self.gaussvva = context.simple_vertex_array(
            self.gaussv, context.buffer(QUAD), 'in_vert')
        self.fringe = context.program(vertex_shader=TEX_VERTEX,
                                      fragment_shader=COMBINE_FRAGMENT)
        self.fringe['la'].value = 0
        self.fringe['tex'].value = 1
        self.combine = context.simple_vertex_array(
            self.fringe, context.buffer(QUAD), 'in_vert')

        size, table = (width, height), (256, height * 256 // width)
        self.fb = context.framebuffer(context.texture(size, 4),
                                      context.depth_renderbuffer(size))
        self.fb.color_attachments[0].use(1)
        self.ping = context.framebuffer(context.texture(table, 3))
        self.pong = context.framebuffer(context.texture(table, 3))

    def resize(self, window, width, height):
        """Update viewport on resize."""
        context = self.context
        context.viewport = 0, 0, width, height
        self.gaussv['height'].value = 256 * height / width

        self.fb.depth_attachment.release()
        for fb in (self.fb, self.ping, self.pong):
            for texture in fb.color_attachments: texture.release()
            fb.release()

        size, table = (width, height), (256, height * 256 // width)
        self.fb = context.framebuffer(context.texture(size, 4),
                                      context.depth_renderbuffer(size))
        self.fb.color_attachments[0].use(1)
        self.ping = context.framebuffer(context.texture(table, 3))
        self.pong = context.framebuffer(context.texture(table, 3))

    def look(self, window, xpos, ypos):
        """Look according to cursor position.

        Present as a callback for GLFW CursorPos event.
        """
        center = np.array(glfw.get_window_size(window)) / 2
        glfw.set_cursor_pos(window, *center)
        self.camera.rotate(*((center - [xpos, ypos]) * self.rotspeed))

    def zoom(self, window, xoffset, yoffset):
        """Adjust FOV according to vertical scroll."""
        self.zmlvl += yoffset * 2 / self.zmspeed
        self.zmlvl = max(self.zmlvl, ZMIN)
        self.zmlvl = min(self.zmlvl, ZMAX)

    def shoot(self, window, button, action, mods):
        """Shoot on click.

        Present as a callback for GLFW MouseButton event.
        """
        if button == self.mouse['1st'] and action == glfw.PRESS:
            self.camera.shoot()

    @property
    def width(self) -> int:
        """Viewport width."""
        return self.context.viewport[2]

    @property
    def height(self) -> int:
        """Viewport height."""
        return self.context.viewport[3]

    @property
    def pos(self) -> np.float32:
        """Camera position in a NumPy array."""
        return self.camera.pos

    @property
    def right(self) -> np.float32:
        """Camera right direction."""
        return self.camera.rot[0]

    @property
    def upward(self) -> np.float32:
        """Camera upward direction."""
        return self.camera.rot[1]

    @property
    def forward(self) -> np.float32:
        """Camera forward direction."""
        return self.camera.rot[2]

    @property
    def is_running(self) -> bool:
        """GLFW window status."""
        return not glfw.window_should_close(self.window)

    @property
    def fov(self) -> float:
        """Horizontal field of view in degrees."""
        return degrees(2 ** self.zmlvl)

    @property
    def rotspeed(self) -> float:
        """Camera rotational speed, calculated from FOV and mouse speed."""
        return 2**self.zmlvl * self.mouspeed

    @property
    def visibility(self) -> np.float32:
        """Camera visibility."""
        return np.float32(3240 / (self.fov + 240))

    @property
    def fps(self) -> float:
        """Currently rendered frames per second."""
        return self.camera.fps

    @fps.setter
    def fps(self, fps):
        self.camera.fps = fps
        #print(fps)

    def is_pressed(self, *keys) -> bool:
        """Return whether given keys are pressed."""
        return any(glfw.get_key(self.window, k) == glfw.PRESS for k in keys)

    def prender(self, obj, va2, va3, col, bright=1.0):
        """Render the obj and its images in bounded 3D space."""
        rotation = Matrix44.from_matrix33(obj.rot).astype(np.float32).tobytes()
        position = obj.pos.astype(np.float32).tobytes()
        self.prog2['rot'].write(rotation)
        self.prog3['rot'].write(rotation)
        self.prog2['pos'].write(position)
        self.prog3['pos'].write(position)
        self.prog2['color'].write(color(col, bright*EDGE_BRIGHTNESS).tobytes())
        self.prog3['color'].write(color(col, bright).tobytes())
        va2.render(moderngl.LINES)
        va3.render(moderngl.TRIANGLES)

    def render_pico(self, pico):
        """Render pico and its images in bounded 3D space."""
        self.prender(pico, self.pva2, self.pva3, self.colors[pico.addr])

    def render_shard(self, shard):
        """Render shard and its images in bounded 3D space."""
        self.prender(shard, self.sva2, self.sva3,
                     self.colors[shard.addr], shard.power/SHARD_LIFE)

    def add_pico(self, address, position, rotation):
        """Add picobot from addr at pos with rot."""
        self.picos[address] = Picobot(address, self.space, position, rotation)
        self.colors[address] = randint(0, 5)

    def render(self):
        """Render the scene before post-processing."""
        visibility = self.visibility
        projection = Matrix44.perspective_projection(
            self.fov, self.width/self.height, 3E-3, visibility)
        view = Matrix44.look_at(self.pos, self.pos + self.forward, self.upward)
        vp = (view @ projection).astype(np.float32).tobytes()

        # Render map
        self.maprog['visibility'].value = visibility
        self.maprog['camera'].write(self.pos.tobytes())
        self.maprog['mvp'].write(vp)
        self.mapva.render(moderngl.TRIANGLES)

        # Render picos and shards
        self.prog2['visibility'].value = visibility
        self.prog3['visibility'].value = visibility
        self.prog2['camera'].write(self.pos.tobytes())
        self.prog3['camera'].write(self.pos.tobytes())
        self.prog2['vp'].write(vp)
        self.prog3['vp'].write(vp)

        self.lock.acquire(blocking=False)
        for pico in self.picos.values():
            shards = {}
            for index, shard in pico.shards.items():
                if not shard.power: continue
                shard.update(self.fps)
                self.render_shard(shard)
                shards[index] = shard
            pico.shards = shards
            if pico is not self.camera: self.render_pico(pico)
        self.lock.release()

    def update(self):
        """Handle input, update GLSL programs and render the map."""
        # Update instantaneous FPS
        next_time = glfw.get_time()
        self.fps = 1 / (next_time-self.last_time)
        self.last_time = next_time

        # Character movements
        right, upward, forward = 0, 0, 0
        if self.is_pressed(self.key['forward']): forward += 1
        if self.is_pressed(self.key['backward']): forward -= 1
        if self.is_pressed(self.key['left']): right -= 1
        if self.is_pressed(self.key['right']): right += 1
        self.camera.move(right, upward, forward)

        self.fb.use()
        self.fb.clear()
        self.render()
        self.fb.color_attachments[0].use()
        self.ping.use()
        self.ping.clear()
        self.pfilter.render(moderngl.TRIANGLES)
        self.ping.color_attachments[0].use()

        self.pong.use()
        self.pong.clear()
        self.gausshva.render(moderngl.TRIANGLES)
        self.pong.color_attachments[0].use()
        self.ping.use()
        self.ping.clear()
        self.gaussvva.render(moderngl.TRIANGLES)
        self.ping.color_attachments[0].use()

        self.context.screen.use()
        self.context.clear()
        self.fringe['invfov'].value = 1.0 / self.fov**CONWAY
        self.combine.render(moderngl.TRIANGLES)
        glfw.swap_buffers(self.window)
        glfw.poll_events()

    def close(self):
        """Close window."""
        glfw.terminate()
