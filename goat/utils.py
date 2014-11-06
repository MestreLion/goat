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

'''Utility functions'''

import os
import sys
import subprocess

import globals as g

def datadirs(dirname):
    '''Return a list of game relevant data directories, useful for finding data
        files such as games
    '''
    return [os.path.join(g.APPDIR,  dirname),
            os.path.join(g.DATADIR, dirname),
            os.path.join(g.USERDIR, dirname)]


def safemakedirs(path):
    try:
        os.makedirs(path, 0700)
    except OSError as e:
        if e.errno != 17:  # File exists
            raise


def launchfile(filename):
    if sys.platform.startswith('darwin'):
        subprocess.call(('open', filename))
    elif os.name == 'nt':  # works for sys.platform 'win32' and 'cygwin'
        os.system("start %s" % filename)  # could be os.startfile() too
    else:  # Assume POSIX (Linux, BSD, etc)
        subprocess.call(('xdg-open', filename))
