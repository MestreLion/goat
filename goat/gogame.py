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

'''Go Game, Board, Moves classes wrappers'''

import os
import logging

# Pypi: gomill
import gomill.sgf
import gomill.sgf_moves
import gomill.sgf_properties

import globals as g


log = logging.getLogger(__name__)

BLACK = 'b'
WHITE = 'w'


class GoGameError(Exception):
    pass


class GoGame(object):
    def __init__(self, sgffile, autosetup=True, autoplay=True):
        self.sgffile = sgffile
        self.sgfgame = self._sgfgame(self.sgffile)
        self.header = self.sgfgame.get_root()
        self.size = self.sgfgame.get_size()

        try:
            self.winner = self.sgfgame.get_winner()
        except ValueError as e:
            raise GoGameError("No winner: %s" % e)

        self.initialboard = None
        self.sgfboard = None
        self.sgfplays = None
        self.id = ""
        if autosetup:
            self.setup()

        self.plays = []
        if autoplay:
            self.play()

    def _sgfgame(self, sgffile):
        with open(sgffile, 'r') as fp:
            try:
                return gomill.sgf.Sgf_game.from_string(fp.read())
            except ValueError as e:
                raise GoGameError(e)

    def _gameid(self, sgfplays, size):
        id = ""
        moves = len(sgfplays)
        for move in [20, 40, 60, 31, 51, 71]:
            if move <= moves:
                id += gomill.sgf_properties.serialise_go_point(sgfplays[move-1][1], size)
            else:
                id += "--"
        return id

    def setup(self):
        try:
            self.sgfboard, self.sgfplays = gomill.sgf_moves.get_setup_and_moves(self.sgfgame)
            self.initialboard = Board(self.size, self.sgfboard.copy())
            self.id = self._gameid(self.sgfplays, self.size)
            self.description = "%s(%s) vs %s(%s) %s %s" % (self.header.get("PB"),
                                                           self.header.get("BR"),
                                                           self.header.get("PW"),
                                                           self.header.get("WR"),
                                                           self.header.get("RE"),
                                                           self.header.get("DT"),)
        except ValueError as e:
            raise GoGameError(e)

    def play(self):
        del self.plays[:]
        if not self.id:
            self.setup()
        boardfile = os.path.join(g.USERDIR, 'boards', self.id[:2], "%s.json" % self.id)
        if not os.path.exists(boardfile):
            sgfboard = self.sgfboard.copy()
            for i, move in enumerate(self.sgfplays):
                color, coord = move
                if coord is not None:
                    row, col = coord
                    try:
                        sgfboard.play(row, col, color)
                    except Exception:
                        raise GoGameError("Invalid move #%d: %s[%s]" % (
                            i+1,
                            color.upper(),
                            gomill.sgf_properties.serialise_go_point(coord, self.size)))
                board = sgfboard.copy()  # Board(self.size, sgfboard.copy())
                self.plays.append((move, board))


class Board(object):

    _ascii = {
        None  : " ",
        'b'   : "#",
        'w'   : "o",
    }

    _mapping = {
        None  : None,
        'b'   : BLACK,
        'w'   : WHITE,
    }

    def __init__(self, size, sgfboard=None):
        self.size = size
        self.board = sgfboard.board

#         cols = [None] * self.size
#         for _ in xrange(self.size):
#             self.board.append(cols)

    def get(self, row, col):
        return self.board[row][col]

    def set(self, row, col, value):
        self.board[row][col] = value

    def points(self):
        for row in xrange(self.size):
            for col in xrange(self.size):
                yield self.board[row][col]

    def ascii(self):
        lines = []
        for row in xrange(self.size - 1, -1, -1):
            line = ""
            for col in xrange(self.size):
                line += self._ascii[self.board[row][col]]
            lines.append(line)
        return "\n".join(lines)
