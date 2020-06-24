# handling of user control using GLFW
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

__doc__ = 'Axuy handling of user control using GLFW'
__all__ = ['CtlConfig', 'Control']

from cmath import polar
from re import IGNORECASE, match
from warnings import warn

import glfw
import numpy

from .display import DispConfig, Display

CONTROL_ALIASES = (('Move left', 'left'), ('Move right', 'right'),
                   ('Move forward', 'forward'), ('Move backward', 'backward'),
                   ('Primary', '1st'), ('Secondary', '2nd'))
MOUSE_PATTERN = 'MOUSE_BUTTON_[1-{}]'.format(glfw.MOUSE_BUTTON_LAST + 1)
INVALID_CONTROL_ERR = '{}: {} is not recognized as a valid control key'
GLFW_VER_WARN = 'Your GLFW version appear to be lower than 3.3, '\
                'which might cause stuttering camera rotation.'
ZMIN, ZMAX = -1.0, 1.0


class CtlConfig(DispConfig):
    """User control configurations.

    Attributes
    ----------
    key, mouse : Dict[str, int]
        Input control.
    mouspeed : float
        Relative camera rotational speed.
    zmspeed : float
        Zoom speed, in scroll steps per zoom range.
    """

    def __init__(self) -> None:
        DispConfig.__init__(self)
        self.options.add_argument(
            '--mouse-speed', type=float, dest='mouspeed',
            help='camera rotational speed (fallback: {:.1f})'.format(
                self.__mouspeed))
        self.options.add_argument(
            '--zoom-speed', type=float, dest='zmspeed',
            help='zoom speed (fallback: {:.1f})'.format(self.zmspeed))

    @property
    def mouspeed(self) -> float:
        """Relative mouse speed."""
        # Standard to radians per inch for a 800 DPI mouse, at FOV of 60
        return self.__mouspeed / 800

    @mouspeed.setter
    def mouspeed(self, value: float) -> None:
        self.__mouspeed = value

    def fallback(self) -> None:
        """Parse fallback configurations."""
        DispConfig.fallback(self)
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

    def read(self, arguments):
        """Read and parse a argparse.ArgumentParser.Namespace."""
        DispConfig.read(self, arguments)
        for option in 'fov', 'mouspeed', 'zmspeed':
            value = getattr(arguments, option)
            if value is not None: setattr(self, option, value)


class Control(Display):
    """User control.

    Parameters
    ----------
    config : CtlConfig
        User control configurations.

    Attributes
    ----------
    key, mouse : Dict[str, int]
        Input control.
    zmspeed : float
        Scroll steps per zoom range.
    mouspeed : float
        Relative camera rotational speed.
    """

    def __init__(self, config):
        Display.__init__(self, config)
        self.key, self.mouse = config.key, config.mouse
        self.mouspeed = config.mouspeed
        self.zmspeed = config.zmspeed

        glfw.set_input_mode(self.window, glfw.CURSOR, glfw.CURSOR_DISABLED)
        glfw.set_input_mode(self.window, glfw.STICKY_KEYS, True)
        glfw.set_cursor_pos_callback(self.window, self.look)
        glfw.set_scroll_callback(self.window, self.zoom)
        glfw.set_mouse_button_callback(self.window, self.shoot)
        try:
            if glfw.raw_mouse_motion_supported():
                glfw.set_input_mode(self.window, glfw.RAW_MOUSE_MOTION, True)
        except AttributeError:
            warn(GLFW_VER_WARN, category=RuntimeWarning)

    def look(self, window, xpos, ypos):
        """Look according to cursor position.

        Present as a callback for GLFW CursorPos event.
        """
        center = numpy.array(glfw.get_window_size(window)) / 2
        glfw.set_cursor_pos(window, *center)
        yaw, pitch = (center - [xpos, ypos]) * self.mouspeed * 2**self.zmlvl
        self.camera.rotate(*polar(complex(yaw, pitch)))

    def zoom(self, window, xoffset, yoffset):
        """Adjust FOV according to vertical scroll."""
        self.zmlvl += yoffset * 2 / self.zmspeed
        self.zmlvl = max(self.zmlvl, ZMIN)
        self.zmlvl = min(self.zmlvl, ZMAX)

    def shoot(self, window, button, action, mods):
        """Shoot on click.

        Present as a callback for GLFW MouseButton event.
        """
        if action == glfw.PRESS:
            if button == self.mouse['1st']:
                self.camera.shoot()
            elif button == self.mouse['2nd']:
                self.camera.shoot(backward=True)

    def is_pressed(self, *keys) -> bool:
        """Return whether given keys are pressed."""
        return any(glfw.get_key(self.window, k) == glfw.PRESS for k in keys)

    def control(self) -> None:
        """Handle events controlling the protagonist."""
        Display.control(self)
        right, upward, forward = 0, 0, 0
        if self.is_pressed(self.key['forward']): forward += 1
        if self.is_pressed(self.key['backward']): forward -= 1
        if self.is_pressed(self.key['left']): right -= 1
        if self.is_pressed(self.key['right']): right += 1
        self.pico.update(right, upward, forward)
