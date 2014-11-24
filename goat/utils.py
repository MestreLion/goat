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
import json


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


def prettyjson(obj, indent=1, _lvl=0):
    '''Serialize <obj> to JSON in a compact yet human-friendly format
        Dictionaries and lists of lists are formated one key/item per line
        Ordinary lists and other singletons are packed in a single line
    '''
    sep = " " * indent

    # Handle dictionaries
    if isinstance(obj, dict):
        return ('{\n%s%s\n%s}') % (
            sep * _lvl,
            (",\n%s" % (sep * _lvl)).join(['"%s": %s' % (k, prettyjson(v, indent, _lvl+1))
                                           for k, v in sorted(obj.iteritems())]),
            sep * (_lvl-1))

    # Handle lists of lists
    # Plain text replace is not robust and will break strings that contains "[[", "]]" or "],["
    # But it's faster than properly iterating each item
    return json.dumps(obj, separators=(',',':')
        ).replace('],[', '],\n%s[' % (sep * _lvl)
        ).replace('[[' , '[\n%s['  % (sep * _lvl)
        ).replace(']]' , ']\n%s]'  % (sep * (_lvl-1)))
