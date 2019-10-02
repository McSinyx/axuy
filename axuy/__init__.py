"""Axuy is a minimalist first-person shooter."""

from .misc import *
from .pico import *
from .peer import *
from .display import *
from .control import *

__all__ = (misc.__all__ + pico.__all__ + peer.__all__
           + display.__all__ + control.__all__)
