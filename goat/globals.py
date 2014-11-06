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
import sys
import xdg.BaseDirectory
import logging
import argparse
import json

log = logging.getLogger(__name__)


# General
VERSION = "0.1"
APPNAME = 'goat'
BOARD_SIZE = 19

# Paths
APPDIR    = os.path.abspath(os.path.dirname(__file__) or '.')
DATADIR   = os.path.join(APPDIR, 'data')
USERDIR   = xdg.BaseDirectory.save_data_path(APPNAME)
CONFIGDIR = xdg.BaseDirectory.save_config_path(APPNAME)
CACHEDIR  = os.path.join(xdg.BaseDirectory.xdg_cache_home, APPNAME)
WINDOWFILE = os.path.join(CONFIGDIR, 'window.json')

# Options
options = None
full_screen = False
window_size = (960, 640)
debug = False
profile = False


def parseargs(argv=None):
    parser = argparse.ArgumentParser(
        description="Go Analisys Tool",)

    loglevels = ['debug', 'info', 'warn', 'error', 'critical']
    logdefault = 'info'
    parser.add_argument('--loglevel', '-l', dest='loglevel',
                        default=logdefault, choices=loglevels,
                        help="set verbosity level. [default: '%s']" % logdefault)

    parser.add_argument('--replay', '-P', dest='replay',
                        default=False,
                        action='store_true',
                        help='replay the games, rebuilding the boards cache. Implies --recalc')

    parser.add_argument('--recalc', '-C', dest='recalc',
                        default=False,
                        action='store_true',
                        help='force data recalculation, rebuilding the hooks cache.')

    parser.add_argument('--fullscreen', '-f', dest='fullscreen',
                        default=False,
                        action='store_true',
                        help='Enable Fullscreen.')

    parser.add_argument('--games', '-g', dest='games',
                        default=0,
                        type=int,
                        help="How many games to process. 0, the default, means all games.")

    parser.add_argument(dest='gamefiles',
                        #default="brave",
                        nargs="?",  # @@
                        help="Game to play, either an .SGF full path or a Game ID")

    if argv is None:
        argv = sys.argv[1:]
    args = parser.parse_args(argv)
    args.debug = args.loglevel=='debug'
    return args


def load_options(argv=None):
    '''Load all global options from config file and command line arguments'''
    global options, window_size, debug, profile, gamespath
    try:
        log.debug("Loading window size from: %s", WINDOWFILE)
        with open(WINDOWFILE) as fp:
            # Read in 2 steps to guarantee a valid (w, h) numeric 2-tuple
            width, height = json.load(fp)
            window_size = (int(width),
                           int(height))
    except (IOError, ValueError) as e:
        log.warn("Error reading window size, using factory default: %s", e)

    options = parseargs(argv)

    if options.debug:
        logging.getLogger(__package__).setLevel(logging.DEBUG)


def save_options():
    try:
        log.debug("Saving window size to: %s", WINDOWFILE)
        with open(WINDOWFILE, 'w') as fp:
            json.dump(window_size, fp)
    except IOError as e:
        log.warn("Could not write window size: %s", e)
