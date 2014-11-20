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

import logging
import argparse
import sys
import os.path
import ConfigParser
import shutil
import time

import globals as g
import calcs
import gogame
import library


log = logging.getLogger(__name__)


def main(argv=None):
    '''App entry point
        <args> is a list of command line arguments, defaults to sys.argv[1:]
    '''

    configbasename = "%s.conf" % g.APPNAME
    configfilename = os.path.join(g.CONFIGDIR, configbasename)
    configtemplate = os.path.join(g.DATADIR,   configbasename)

    if not os.path.exists(configfilename):
        shutil.copyfile(configtemplate, configfilename)

    config = ConfigParser.SafeConfigParser()
    config.readfp(open(configtemplate))
    config.read(configfilename)

    board_size = config.getint('general', 'board_size')

    parser = argparse.ArgumentParser(description="Go Analysis Tool")

    parser.add_argument('--quiet', '-q', dest='loglevel', action="store_const", const=logging.WARNING, default=logging.INFO,
                        help="Suppress informative messages and summary statistics")

    parser.add_argument('--debug', '-d', dest='loglevel', action="store_const", const=logging.DEBUG,
                        help="Enable debugging mode")

    subparsers = parser.add_subparsers(dest="command")

    subparser = subparsers.add_parser('import')

    subparser.add_argument('--board-size', '-b', dest='board_size', default=board_size, type=int,
                           help="Board size. Default: %d" % board_size)

    subparser.add_argument('--games', '-g', dest='games', default=0, type=int, metavar="NUM",
                           help="Import games until library has at least NUM games. 0 for no library size limit.")

    subparser.add_argument(dest='sources', nargs="+",metavar="SOURCEDIR",
                           help="Paths containing game sources to import to Library. "
                                "Sources are SGF files or archives in ZIP and TAR.{BZ2,GZ} format")

    subparser = subparsers.add_parser('compute')

    subparser.add_argument('--games', '-g', dest='games', default=0, type=int, metavar="NUM",
                           help="Compute at most NUM games from library. 0 for all games in library.")



    if argv is None:
        argv = sys.argv[1:]
    g.options = parser.parse_args(argv)
    g.options.debug = g.options.loglevel==logging.DEBUG

    logging.basicConfig(
        format="[%(levelname)-8s] %(asctime)s %(module)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=g.options.loglevel
    )

    start = time.time()  # Wall time
    log.info("Options: %s", g.options)

    if g.options.command == "import":
        library.import_sources()

    elif g.options.command == "compute":
        compute()

    log.info("Finished in %s", time.strftime('%H:%M:%S', time.gmtime(time.time()-start)))


def compute():

    hooks = [
#        calcs.StonesPerSquare(g.BOARD_SIZE),
#        calcs.LibertiesPerMove(g.BOARD_SIZE),
#        calcs.Territories(g.BOARD_SIZE),
#        calcs.FractalDimension(g.BOARD_SIZE),
#        calcs.MoveHistogram(),
#        calcs.TimeLine(g.BOARD_SIZE)
    ]

    games = 0

    for filename in library.walk():

        chart = False # games % 10 == 0
        game = gogame.GoGame.from_sgf(filename)
        game.load_moves()
        games += 1
        discard = False

        for hook in hooks:
            hook.gamestart(game, game.initial, chart=chart)

        # @@ try/except temporary until oldplays() is replaced
        try:
            for move, board in game.oldplays():
                for hook in hooks:
                    hook.move(game, board, move)
        except Exception as e:
            log.error("Ignoring game %s: %s", filename, e)
            games -= 1
            board = move = None
            discard = True

        for hook in hooks:
            hook.gameover(game, board, chart=chart, discard=discard)

        if games % 1000 == 0:
            log.info("Games processed: %d", games)

    for hook in hooks:
        hook.end()
