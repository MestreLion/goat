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

import os
import logging
import zipfile
import tarfile

import progressbar  # Debian: python-progressbar
import pygame  # Debian: python-pygame

# Pypi: gomill
from gomill import ascii_boards
from gomill import sgf
from gomill import sgf_moves

import globals as g
import utils
import calcs

log = logging.getLogger(__name__)

class CustomError(Exception):
    pass

def find_games(paths):

    def extract(filepath):
        basename = os.path.basename(filepath)
        path = os.path.join(g.CACHEDIR, basename)

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


def main(argv=None):
    '''App entry point
        <args> is a list of command line arguments, defaults to sys.argv[1:]
    '''

    logging.basicConfig(
        format="[%(levelname)-8s] %(asctime)s %(module)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=logging.INFO
    )

    utils.safemakedirs(g.CACHEDIR)
    g.load_options(argv)
    #pygame.display.init()
    #pygame.font.init()


    hooks = [calcs.StonesPerSquare(g.BOARD_SIZE),
             calcs.LibertiesPerMove(g.BOARD_SIZE)]
    hooks = []

    games = 0
    files = 0
    skip = {
        'noend': 0,
        'nopro': 0,
        'handicap': 0,
        'nodoublepass': 0,
        'fewmoves': 0,
        'error': 0,
    }
    for filename in find_games(utils.datadirs('games')):
        log.debug("Loading game %s", filename)
        files += 1
        with open(filename, 'r') as fp:
            try:
                game = sgf.Sgf_game.from_string(fp.read())
            except ValueError as e:
                log.error("Ignoring game %s: %s", filename, e)
                skip['error'] += 1
                continue
            game.name = os.path.splitext(os.path.basename(filename))[0]
            root = game.get_root()

        if files % 1000 == 0:
            log.info("Files processed: %d", files)

        def validate():
            try:
                result = root.get("RE").split('+')[1].lower()
                if result:
                    if result[0] in ['r', 't', 'f']:
                        # Resign, Timeout, Forfeit
                        skip['noend'] += 1
                        return
                    result = float(result)
            except (KeyError,    # No 'RE'
                    IndexError,  # No '+', might be 'V[oid]', '?', or malformed
                    ValueError,  # A comment in result
                    ):
                skip['noend'] += 1
                return

            try:
                for rank in [root.get("BR"), root.get("WR")]:
                    level, grade = int(rank[:-1]), rank[-1]
                    if grade not in ['d', 'p'] or (grade == 'd' and level < 6):
                        skip['nopro'] += 1
                        return
            except (KeyError, ValueError):
                skip['nopro'] += 1
                return

            if root.has_property("HA"):
                skip['handicap'] += 1
                return

            if not game.get_size() == g.BOARD_SIZE:
                log.warn("Ignoring game %s: board size is not %d: %d",
                         filename, g.BOARD_SIZE, game.get_size())
                return

            return True

        if not validate():
            continue

        chart = False # games % 10 == 0

        try:
            board, plays = sgf_moves.get_setup_and_moves(game)
        except ValueError as e:
            log.error("Error in game %s: %s", filename, e)
            skip['error'] += 1
            continue

        # Sanity checks:

        if len(plays) <= 50:
            log.warn("Ignoring game %s: only %d moves", filename, len(plays))
            skip['fewmoves'] += 1
            continue

        #if not (plays[-2][1], plays[-1][1]) == (None, None):
        #    log.warn("Ignoring game %s: does not end in double-pass: %s", filename, plays[-2:])
        #    skip['nodoublepass'] += 1
        #    continue

        # Valid game
        games += 1
        discard = False
        #continue

        for hook in hooks:
            hook.gamestart(game, board, chart=chart)

        for colour, move in plays:
            if move is not None:
                row, col = move
                try:
                    board.play(row, col, colour)
                except Exception as e:
                    log.error("Error in game %s, move (%s, %s): %s", filename, colour, move, e)
                    skip['error'] += 1
                    games -= 1
                    discard = True
                    break

            for hook in hooks:
                hook.move(game, board, move)

        for hook in hooks:
            hook.gameover(game, board, chart=chart, discard=discard)
            if chart:
                print ascii_boards.render_board(board)

        if g.options.games and games >= g.options.games:
            break

    for hook in hooks:
        hook.end()

    log.info("Ignored games: %r", skip)
    log.info("%d files loaded, %d games processed (%.0f%%)", files, games, 100. * games / files)

    pygame.quit()
    g.save_options()
