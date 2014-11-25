# -*- coding: utf-8 -*-
#
#    Copyright (C) 2014 Rodrigo Silva (MestreLion) <linux@rodrigosilva.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program. See <http://www.gnu.org/licenses/gpl.html>

'''Global constants and options handling'''

import os
import xdg.BaseDirectory
import logging
import time


log = logging.getLogger(__name__)


# General
VERSION = "0.1"
APPNAME = 'goat'
BOARD_SIZE = 19

# Paths
APPDIR     = os.path.abspath(os.path.dirname(__file__) or '.')
DATADIR    = os.path.join(APPDIR, 'data')
USERDIR    = xdg.BaseDirectory.save_data_path(APPNAME)
LIBRARYDIR = os.path.join(USERDIR, 'library')
RESULTSDIR = os.path.join(os.path.expanduser("~"), APPNAME, "results_%s" % time.strftime('%Y-%m-%d_%H.%M.%S'))
CONFIGDIR  = xdg.BaseDirectory.save_config_path(APPNAME)
CACHEDIR   = os.path.join(xdg.BaseDirectory.xdg_cache_home, APPNAME)
WINDOWFILE = os.path.join(CONFIGDIR, 'window.json')

# Options
options = None
