#!/usr/bin/env python
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

'''Main module and entry point'''

import sys
import os
import xdg.BaseDirectory
import logging
import json
import zipfile
import tarfile
import subprocess

import matplotlib.pyplot as plt  # Debian: python-matplotlib
import progressbar  # Debian: python-progressbar
import pygame  # Debian: python-pygame

# Pypi: gomill
from gomill import ascii_boards
from gomill import sgf
from gomill import sgf_moves
from gomill import boards



log = logging.getLogger(__name__)

# General
VERSION = "0.1"
APPNAME = 'goat'
BOARD_SIZE = 19
GAMES = 3000

# Paths
APPDIR    = os.path.abspath(os.path.dirname(__file__) or '.')
DATADIR   = os.path.join(APPDIR, 'data')
USERDIR   = xdg.BaseDirectory.save_data_path(APPNAME)
CONFIGDIR = xdg.BaseDirectory.save_config_path(APPNAME)
CACHEDIR  = os.path.join(xdg.BaseDirectory.xdg_cache_home, APPNAME)
WINDOWFILE = os.path.join(CONFIGDIR, 'window.json')

# Options
full_screen = False
window_size = (960, 640)
debug = False
profile = False


class CustomError(Exception):
    pass

def safemakedirs(path):
    try:
        os.makedirs(path, 0700)
    except OSError as e:
        if e.errno != 17:  # File exists
            raise


def datadirs(dirname):
    '''Return a list of game relevant data directories, useful for finding data
        files such as themes and images
    '''
    return [os.path.join(APPDIR,  dirname),
            os.path.join(DATADIR, dirname),
            os.path.join(USERDIR, dirname)]


def load_options(args):
    '''Load all global options from config file and command line arguments'''
    global window_size, full_screen, debug, profile, gamespath
    try:
        log.debug("Loading window size from: %s", WINDOWFILE)
        with open(WINDOWFILE) as fp:
            # Read in 2 steps to guarantee a valid (w, h) numeric 2-tuple
            width, height = json.load(fp)
            window_size = (int(width),
                           int(height))
    except (IOError, ValueError) as e:
        log.warn("Error reading window size, using factory default: %s", e)

    # Too lazy for argparse right now
    if args is None:
        args = sys.argv[1:]
    if "--fullscreen" in args: full_screen = True
    if "--debug"      in args: debug = True
    if "--profile"    in args: profile = True

    if debug:
        logging.getLogger(__package__).setLevel(logging.DEBUG)


def save_options():
    try:
        log.debug("Saving window size to: %s", WINDOWFILE)
        with open(WINDOWFILE, 'w') as fp:
            json.dump(window_size, fp)
    except IOError as e:
        log.warn("Could not write window size: %s", e)


def find_games(paths):

    def extract(filepath):
        basename = os.path.basename(filepath)
        path = os.path.join(CACHEDIR, basename)

        if os.path.exists(path):
            return path

        driver = None
        if   zipfile.is_zipfile(filepath): driver = zipfile.ZipFile
        elif tarfile.is_tarfile(filepath): driver = tarfile.open

        if not driver:
            raise CustomError("Invalid archive format")

        log.debug("Extracting %s to %s", os.path.basename(filepath), path)
        archive = driver(filepath, 'r')
        archive.extractall(path)
        return path

    for path in paths:
        log.info("Searching for games in %s", path)

        for root, dirs, files in os.walk(path):
            for name in files:
                filepath = os.path.join(root, name)
                ext = os.path.splitext(name)[1][1:].lower()

                if ext == "sgf":
                    yield filepath

                elif ext in ['zip', 'gz', 'bz2']:
                    try:
                        dirs.append(extract(filepath))
                    except CustomError as e:
                        log.warn("Error extracting %s: %s", filepath, e)


def main(args=None):
    '''App entry point
        <args> is a list of command line arguments, defaults to sys.argv[1:]
    '''

    logging.basicConfig(
        format="[%(levelname)-8s] %(asctime)s %(module)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=logging.INFO
    )

    safemakedirs(CACHEDIR)
    load_options(args)
    #pygame.display.init()
    #pygame.font.init()

    hooks = [StonesPerSquare(BOARD_SIZE),]

    games = 0
    i = 0
    for filename in find_games(datadirs('games')):
        log.debug("Loading game %s", filename)
        with open(filename, 'r') as fp:
            game = sgf.Sgf_game.from_string(fp.read())
            game.name = os.path.splitext(os.path.basename(filename))[0]

        if not game.get_size() == BOARD_SIZE:
            log.warn("Ignoring game %s: size is %d", filename, game.get_size())
            continue

        i += 1
        if not i % 10 == 0:
            continue

        board, plays = sgf_moves.get_setup_and_moves(game)

        if len(plays) <= 50:
            log.warn("Ignoring game %s: only %d moves", filename, len(plays))
            continue

        for hook in hooks:
            hook.gamestart(game, board)

        for colour, move in plays:
            if move is not None:
                row, col = move
                board.play(row, col, colour)
            for hook in hooks:
                hook.move(game, board, move)

        for hook in hooks:
            chart = games % 10 == 0
            hook.gameover(game, board, chart=chart)
            if chart:
                print ascii_boards.render_board(board)

        games += 1
        if games == GAMES:
            break

    for hook in hooks:
        hook.end()

    log.info("%d games loaded", games)

    pygame.quit()
    save_options()


class LibertiesPerMove(object):
    def __init__(self):
        self.black = []
        self.white = []


def count_liberties(board, game):
    pass


class StoneCountCenterPoint(object):
    def __init__(self, point, label, color, limits):
        self.point = point
        self.label = label
        self.color = color

        self.perimeters = []
        for i in xrange(limits[1] - limits[0] + 1):
            self.perimeters.append(self.square_perimeter_points(i, limits))

    def square_perimeter_points(self, distance, limits):
        points = []

        def append(point):
            if (limits[0] <= point[0] <= limits[1] and
                limits[0] <= point[1] <= limits[1]):
                points.append(point)

        if distance == 0:
            append(self.point)
            return points

        # Bottom and Top rows
        for x in xrange(self.point[0] - distance,
                        self.point[0] + distance + 1):
            append((x, self.point[1] - distance))
            append((x, self.point[1] + distance))

        # Left and Right columns (excluding corners)
        for y in xrange(self.point[1] - distance + 1,
                        self.point[1] + distance - 1 + 1):
            append((self.point[0] - distance, y))
            append((self.point[0] + distance, y))

        return points


def launchfile(filename):
    if sys.platform.startswith('darwin'):
        subprocess.call(('open', filename))
    elif os.name == 'nt':  # works for sys.platform 'win32' and 'cygwin'
        os.system("start %s" % filename)  # could be os.startfile() too
    else:  # Assume POSIX (Linux, BSD, etc)
        subprocess.call(('xdg-open', filename))


class Hook(object):
    def __init__(self, size):
        pass
    def gamestart(self, game, board):
        pass
    def move(self, game, board, move):
        pass
    def gameover(self, game, board, chart=False):
        pass
    def end(self):
        pass

class Chart(object):
    def __init__(self):
        self.fig = plt.figure()
        self.ax = self.fig.add_subplot(111)

    def plot(self, *args, **kwargs):
        self.ax.plot(*args, **kwargs)

    def set(self, title="", xlabel="", ylabel="", loc=0):
        self.ax.legend(loc=loc, labelspacing=0.2, prop={'size': 10})
        if xlabel: self.ax.set_xlabel(xlabel)
        if ylabel: self.ax.set_ylabel(ylabel)
        if title:  self.ax.set_title(title)
        self.ax.grid()

    def save(self, name):
        path = os.path.join(CACHEDIR, "%s.png" % name)
        self.fig.savefig(path, dpi=300)
        launchfile(path)

    def close(self):
        plt.close(self.fig)

class StonesPerSquare(Hook):
    def __init__(self, size):
        self.size = size
        limits = (0, self.size - 1)
        self.points = (StoneCountCenterPoint((limits[0], limits[0]), "Lower Left",  "red",    limits),
                       StoneCountCenterPoint((limits[0], limits[1]), "Lower Right", "green",  limits),
                       StoneCountCenterPoint((limits[1], limits[0]), "Upper Left",  "blue",   limits),
                       StoneCountCenterPoint((limits[1], limits[1]), "Upper Right", "orange", limits),
                       StoneCountCenterPoint(2*(limits[1]/2,), "Center", "black", limits))

        for center in self.points:
            center.gamestones = []
            center.gameblacks = []
            center.gamewhites = []
            center.gamewiners = []
            center.gamelosers = []

    def gameover(self, game, board, chart=False):
        if game.get_winner() == 'b':
            blackwinner = True
            bw = 1; ww = 1
            bs = '-'; ws = '--'
        else:
            blackwinner = False
            bw = 1; ww = 1
            bs = '--'; ws = '-'

        if chart:
            figtotal = Chart()
            figcolor = Chart()

        for center in self.points:
            blacks = 0
            whites = 0
            center.stones = []
            center.blacks = []
            center.whites = []

            for perimeter in center.perimeters:
                for point in perimeter:
                    color = board.get(*point)
                    if   color == 'b': blacks += 1
                    elif color == 'w': whites += 1
                center.stones.append(blacks + whites)
                center.blacks.append(blacks)
                center.whites.append(whites)

            center.gamestones.append(center.stones)
            center.gameblacks.append(center.blacks)
            center.gamewhites.append(center.whites)
            if blackwinner:
                center.gamewiners.append(center.blacks)
                center.gamelosers.append(center.whites)
            else:
                center.gamewiners.append(center.whites)
                center.gamelosers.append(center.blacks)

            if chart:
                figcolor.plot(center.blacks, label=center.label + " - Black", color=center.color, lw=bw, ls=bs)
                figcolor.plot(center.whites, label=center.label + " - White", color=center.color, lw=ww, ls=ws)
                figtotal.plot(center.stones, label=center.label,  color=center.color)

            del center.stones
            del center.blacks
            del center.whites

        if chart:
            figcolor.set(loc=2, xlabel="Area (distance from point to edge)", ylabel="Stones",
                         title="Stones per increasing areas - Colors - Game %s" % game.name)  # loc=2: legend on upper left
            figtotal.set(loc=2, xlabel="Area (distance from point to edge)", ylabel="Stones",
                         title="Stones per increasing areas - Total - Game %s" % game.name)

            #plt.show()
            figcolor.save("stones_color_%s" % game.name)
            figtotal.save("stones_total_%s" % game.name)
            figcolor.close()
            figtotal.close()

    def end(self):
        chart = Chart()
        for center in self.points:
            games = len(center.gamestones)
            areaavg = []
            areamin = []
            areamax = []
            for n, _ in enumerate(center.perimeters):
                sum = 0
                min = BOARD_SIZE**2 + 1
                max = -1
                for i, game in enumerate(center.gamestones):
                    v = game[n]
                    sum += v
                    if v < min: min = v
                    if v > max: max = v

                areaavg.append(float(sum / games))
                areamin.append(min)
                areamax.append(max)

            chart.plot(areaavg, label=center.label + " - Avg", color=center.color)
            chart.plot(areamin, label=center.label + " - Min", color=center.color, ls=':')
            chart.plot(areamax, label=center.label + " - Max", color=center.color, ls='--')

        chart.set(loc=2, xlabel="Area (distance from point to edge)", ylabel="Stones",
                  title="Stones per increasing areas - Average of %d games" % games)
        chart.save("stones_average_%d" % games)




if __name__ == "__main__":
    main(sys.argv[1:])
