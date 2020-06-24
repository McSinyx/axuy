# package initialization
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

"""Axuy is a minimalist peer-to-peer first-person shooter.

This package provides abstractions for writing custom front-ends and AIs.
All classes and helper functions are exposed at the package level.

Some superclasses may define abstract methods which must be overridden
in derived classes.  Subclasses only document newly introduced attributes.
"""

from .control import *
from .display import *
from .misc import *
from .peer import *
from .pico import *

__all__ = (misc.__all__ + pico.__all__ + peer.__all__
           + display.__all__ + control.__all__)
__version__ = peer.__version__
