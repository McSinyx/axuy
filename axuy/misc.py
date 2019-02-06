# misc.py - miscellaneous functions
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

import numpy
import pkg_resources


def hex2f4(hex_color):
    """Return numpy float32 array of RGB colors from given hex_color."""
    return numpy.float32([i / 255 for i in bytes.fromhex(hex_color)])


def resource_filename(resource_name):
    """Return a true filesystem path for the specified resource."""
    return pkg_resources.resource_filename('axuy', resource_name)
