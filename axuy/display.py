# graphical display of the game world using GLFW and ModernGL
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

__doc__ = 'Axuy graphical display using GLFW and ModernGL'
__all__ = ['DispConfig', 'Display']

from abc import abstractmethod
from collections import deque
from math import degrees, log2, radians
from random import randint
from statistics import mean
from warnings import warn

import glfw
import moderngl
import numpy as np
from PIL import Image
from pyrr import matrix44

from .misc import abspath, color, mirror
from .peer import Peer, PeerConfig
from .pico import OCTOVERTICES, SHARD_LIFE, TETRAVERTICES

CONWAY = 1.303577269034
ABRTN_MAX = 0.42069

QUAD = np.float32([-1, -1, 1, -1, -1, 1, -1, 1, 1, -1, 1, 1])
TETRAINDECIES = np.int32([0, 1, 2, 3, 1, 2, 0, 3, 2, 0, 3, 1])
OCTOINDECIES = np.int32([0, 1, 2, 0, 1, 3, 4, 0, 2, 4, 0, 3,
                         2, 1, 5, 3, 1, 5, 2, 5, 4, 3, 5, 4])

with open(abspath('shaders/map.vert')) as f: MAP_VERTEX = f.read()
with open(abspath('shaders/map.frag')) as f: MAP_FRAGMENT = f.read()
with open(abspath('shaders/pico.vert')) as f: PICO_VERTEX = f.read()
with open(abspath('shaders/pico.geom')) as f: PICO_GEOMETRY = f.read()
with open(abspath('shaders/pico.frag')) as f: PICO_FRAGMENT = f.read()

with open(abspath('shaders/tex.vert')) as f: TEX_VERTEX = f.read()
with open(abspath('shaders/sat.frag')) as f: SAT_FRAGMENT = f.read()
with open(abspath('shaders/gaussh.vert')) as f: GAUSSH_VERTEX = f.read()
with open(abspath('shaders/gaussv.vert')) as f: GAUSSV_VERTEX = f.read()
with open(abspath('shaders/gauss.frag')) as f: GAUSS_FRAGMENT = f.read()
with open(abspath('shaders/comb.frag')) as f: COMBINE_FRAGMENT = f.read()


class DispConfig(PeerConfig):
    """Graphical display configurations.

    Attributes
    ----------
    size : Tuple[int, int]
        GLFW window resolution.
    vsync : bool
        Vertical synchronization.
    zmlvl : float
        Zoom level.
    """

    def __init__(self) -> None:
        PeerConfig.__init__(self)
        self.options.add_argument(
            '--size', type=int, nargs=2, metavar=('X', 'Y'),
            help='the desired screen size (fallback: {}x{})'.format(
                *self.size))
        self.options.add_argument(
            '--vsync', action='store_true', default=None,
            help='enable vertical synchronization (fallback: {})'.format(
                self.vsync))
        self.options.add_argument(
            '--no-vsync', action='store_false', dest='vsync',
            help='disable vertical synchronization')
        self.options.add_argument(
            '--fov', type=float, metavar='DEGREES',
            help='horizontal field of view (fallback: {:})'.format(
                round(self.fov)))

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
            warn('Too wide FOV, falling back to the maximal value.')
            self.zmlvl = 1.0
            return
        self.zmlvl = log2(rad)

    def fallback(self) -> None:
        """Parse fallback configurations."""
        PeerConfig.fallback(self)
        self.size = (self.config.getint('Graphics', 'Screen width'),
                     self.config.getint('Graphics', 'Screen height'))
        self.vsync = self.config.getboolean('Graphics', 'V-sync')
        self.fov = self.config.getfloat('Graphics', 'FOV')

    def read(self, arguments):
        """Read and parse a argparse.ArgumentParser.Namespace."""
        PeerConfig.read(self, arguments)
        for option in 'size', 'vsync', 'fov':
            value = getattr(arguments, option)
            if value is not None: setattr(self, option, value)


class Display(Peer):
    """World map and camera placement.

    Parameters
    ----------
    config : DispConfig
        Display configurations.

    Attributes
    ----------
    camera : Pico
        Protagonist whose view is the camera.
    colors : Dict[Tuple[str, int], str]
        Color names of enemies.
    window : GLFW window
    zmlvl : float
        Zoom level (from ZMIN to ZMAX).
    context : moderngl.Context
        OpenGL context from which ModernGL objects are created.
    maprog : moderngl.Program
        Processed executable code in GLSL for map rendering.
    mapva : moderngl.VertexArray
        Vertex data of the map.
    prog : moderngl.Program
        Processed executable code in GLSL
        for rendering picos and their shards.
    pva : moderngl.VertexArray
        Vertex data of picos.
    sva : moderngl.VertexArray
        Vertex data of shards.
    pfilter : moderngl.VertexArray
        Vertex data for filtering highly saturated colors.
    gaussh, gaussv : moderngl.Program
        Processed executable code in GLSL for Gaussian blur.
    gausshva, gaussvva : moderngl.VertexArray
        Vertex data for Gaussian blur.
    edge : moderngl.Program
        Processed executable code in GLSL for final combination
        of the bloom effect with additional chromatic aberration
        and barrel distortion.
    combine : moderngl.VertexArray
        Vertex data for final combination of the bloom effect.
    fb, ping, pong : moderngl.Framebuffer
        Frame buffers for bloom-effect post-processing.
    fpses : Deque[float]
        FPS during the last 5 seconds to display the average.
    """

    def __init__(self, config):
        # Create GLFW window
        if not glfw.init(): raise RuntimeError('Failed to initialize GLFW')
        glfw.window_hint(glfw.CLIENT_API, glfw.OPENGL_API)
        glfw.window_hint(glfw.CONTEXT_CREATION_API, glfw.NATIVE_CONTEXT_API)
        glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
        glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
        glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
        glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, True)

        Peer.__init__(self, config)
        self.camera, self.colors = self.pico, {self.addr: randint(0, 5)}
        width, height = config.size
        self.zmlvl = config.zmlvl
        self.window = glfw.create_window(
            width, height, 'axuy@{}:{}'.format(*self.addr), None, None)
        if not self.window:
            glfw.terminate()
            raise RuntimeError('Failed to create GLFW window')
        self.fpses = deque()

        # Window's rendering and event-handling configuration
        glfw.set_window_icon(self.window, 1, Image.open(abspath('icon.png')))
        glfw.make_context_current(self.window)
        glfw.swap_interval(config.vsync)
        glfw.set_window_size_callback(self.window, self.resize)

        # Create OpenGL context
        self.context = context = moderngl.create_context()
        context.enable_only(context.DEPTH_TEST)

        # GLSL program and vertex array for map rendering
        self.maprog = context.program(vertex_shader=MAP_VERTEX,
                                      fragment_shader=MAP_FRAGMENT)
        mapvb = context.buffer(mirror(self.space))
        self.mapva = context.simple_vertex_array(self.maprog, mapvb, 'in_vert')

        # GLSL programs and vertex arrays for picos and shards rendering
        pvb = [(context.buffer(TETRAVERTICES), '3f', 'in_vert')]
        pib = context.buffer(TETRAINDECIES)
        svb = [(context.buffer(OCTOVERTICES), '3f', 'in_vert')]
        sib = context.buffer(OCTOINDECIES)

        self.prog = context.program(vertex_shader=PICO_VERTEX,
                                    geometry_shader=PICO_GEOMETRY,
                                    fragment_shader=PICO_FRAGMENT)
        self.pva = context.vertex_array(self.prog, pvb, pib)
        self.sva = context.vertex_array(self.prog, svb, sib)

        quad_buffer = context.buffer(QUAD)
        self.pfilter = context.simple_vertex_array(
            context.program(vertex_shader=TEX_VERTEX,
                            fragment_shader=SAT_FRAGMENT),
            quad_buffer, 'in_vert')
        self.gaussh = context.program(vertex_shader=GAUSSH_VERTEX,
                                      fragment_shader=GAUSS_FRAGMENT)
        self.gaussh['width'].value = 256
        self.gausshva = context.simple_vertex_array(
            self.gaussh, quad_buffer, 'in_vert')
        self.gaussv = context.program(vertex_shader=GAUSSV_VERTEX,
                                      fragment_shader=GAUSS_FRAGMENT)
        self.gaussv['height'].value = 256 * height / width
        self.gaussvva = context.simple_vertex_array(
            self.gaussv, quad_buffer, 'in_vert')
        self.edge = context.program(vertex_shader=TEX_VERTEX,
                                    fragment_shader=COMBINE_FRAGMENT)
        self.edge['la'].value = 0
        self.edge['tex'].value = 1
        self.combine = context.simple_vertex_array(
            self.edge, quad_buffer, 'in_vert')

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

    @property
    def width(self) -> int:
        """Viewport width."""
        return self.context.viewport[2]

    @property
    def height(self) -> int:
        """Viewport height."""
        return self.context.viewport[3]

    @property
    def health(self) -> float:
        """Camera relative health point."""
        return self.camera.health

    @property
    def pos(self) -> np.float32:
        """Camera position in a NumPy array."""
        return self.camera.pos

    @property
    def postr(self) -> str:
        """Pretty camera position representation."""
        return '[{:4.1f} {:4.1f} {:3.1f}]'.format(*self.pos)

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
    def visibility(self) -> np.float32:
        """Camera visibility."""
        return np.float32(3240 / (self.fov + 240))

    @property
    def fpstr(self) -> str:
        """Pretty string for displaying average FPS."""
        # Average over 5 seconds, like how glxgears do it, but less efficient
        while len(self.fpses) > mean(self.fpses) * 5 > 0: self.fpses.pop()
        return '{} fps'.format(round(mean(self.fpses)))

    def get_time(self) -> float:
        """Return the current time in seconds."""
        return glfw.get_time()

    def prender(self, obj, va, col, bright):
        """Render the obj and its images in bounded 3D space."""
        self.prog['rot'].write(
            matrix44.create_from_matrix33(obj.rot, dtype=np.float32))
        self.prog['pos'].write(obj.pos)
        self.prog['color'].write(color(col, bright))
        va.render(moderngl.TRIANGLES)

    def render_pico(self, pico):
        """Render pico and its images in bounded 3D space."""
        self.prender(pico, self.pva, self.colors[pico.addr], pico.health)

    def render_shard(self, shard):
        """Render shard and its images in bounded 3D space."""
        self.prender(shard, self.sva,
                     self.colors[shard.addr], shard.power/SHARD_LIFE)

    def add_pico(self, address):
        """Add pico from given address."""
        Peer.add_pico(self, address)
        self.colors[address] = randint(0, 5)

    def render(self) -> None:
        """Render the scene before post-processing."""
        visibility = self.visibility
        projection = matrix44.create_perspective_projection(
            self.fov, self.width/self.height, 3E-3, visibility,
            dtype=np.float32)
        view = matrix44.create_look_at(
            self.pos, self.pos+self.forward, self.upward, dtype=np.float32)
        vp = view @ projection

        # Render map
        self.maprog['visibility'].value = visibility
        self.maprog['mvp'].write(vp)
        self.mapva.render(moderngl.TRIANGLES)

        # Render picos and shards
        self.prog['visibility'].value = visibility
        self.prog['camera'].write(self.pos)
        self.prog['vp'].write(vp)
        for pico in self.picos.values():
            for shard in pico.shards.values(): self.render_shard(shard)
            if pico is not self.camera: self.render_pico(pico)

    def update(self) -> None:
        """Update and render the map."""
        # Update states
        Peer.update(self)
        self.fpses.appendleft(self.fps)

        # Render to framebuffer
        self.fb.use()
        self.fb.clear()
        self.render()
        self.fb.color_attachments[0].use()
        self.ping.use()
        self.ping.clear()
        self.pfilter.render(moderngl.TRIANGLES)
        self.ping.color_attachments[0].use()

        # Gaussian blur
        self.pong.use()
        self.pong.clear()
        self.gausshva.render(moderngl.TRIANGLES)
        self.pong.color_attachments[0].use()
        self.ping.use()
        self.ping.clear()
        self.gaussvva.render(moderngl.TRIANGLES)
        self.ping.color_attachments[0].use()

        # Combine for glow effect, chromatic aberration and barrel distortion
        self.context.screen.use()
        self.context.clear()
        if self.camera.dead:
            abrtn = ABRTN_MAX
        else:
            abrtn = min(ABRTN_MAX, (self.fov*self.health) ** -CONWAY)
        self.edge['abrtn'].value = abrtn
        self.edge['zoom'].value = (self.zmlvl + 1.0) / 100
        self.combine.render(moderngl.TRIANGLES)
        glfw.swap_buffers(self.window)
        glfw.set_window_title(self.window, '{} - axuy@{}:{} ({})'.format(
            self.postr, *self.addr, self.fpstr))

    @abstractmethod
    def control(self) -> None:
        """Poll resizing and closing events."""
        glfw.poll_events()

    def __exit__(self, exc_type, exc_value, traceback):
        Peer.__exit__(self, exc_type, exc_value, traceback)
        glfw.terminate()
