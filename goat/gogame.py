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
import sys
import logging

import gomill.sgf

import globals as g
import utils


log = logging.getLogger(__name__)

BLACK = 'b'
WHITE = 'w'

class GoGameError(Exception):
    pass


class GoGame(object):

    @classmethod
    def from_sgf(cls, filename):
        with open(filename, 'r') as fp:
            try:
                sgfgame = gomill.sgf.Sgf_game.from_string(fp.read())
            except ValueError as e:
                raise GoGameError(e)

        gogame = GoGame()
        gogame.sgfgame = sgfgame
        gogame.sgffile = filename
        gogame.size = gogame.sgfgame.get_size()
        gogame.name = os.path.splitext(os.path.basename(filename))[0]
        gogame.winner = gogame.sgfgame.get_winner()

        return gogame

    def __init__(self):
        self.name = ""
        self.sgfgame = None
        self.sgffile = ""
        self.sgfboard = None
        self.sgfplays = None
        self.size = 0
        self.id = ""
        self.initial = None
        self.plays = []


    def get_setup_and_moves(self):
        try:
            self.sgfboard, self.sgfplays = gomill.sgf_moves.get_setup_and_moves(self.sgfgame)
            self.plays = self.sgfplays
        except ValueError as e:
            raise GoGameError(e)

    def oldplays(self):
        for color, move in self.sgfplays:
            if move is not None:
                row, col = move
                try:
                    self.sgfboard.play(row, col, color)
                    yield move, self.sgfboard
                except Exception:
                    raise

        # @@ for later...
#         self.initial = Board(self.size, sgfboard.copy())
#         self.id = self._gameid(sgfplays)
#
#         gamefile = os.path.join(g.CACHEDIR, 'boards', "%s.json" % self.id)
#         if not os.path.exists(gamefile):
#             for color, move in sgfplays:
#                 if move is not None:
#                     row, col = move
#                     try:
#                         sgfboard.play(row, col, color)
#                     except Exception as e:
#                         raise
#                 self.plays.append(((color, move), Board(self.size, sgfboard.copy())))





    def _gameid(self, plays):
        id = ""
        moves = len(plays)
        for move in [20, 40, 60, 31, 51, 71]:
            if move <= moves:
                id += gomill.sgf_properties.serialise_go_point(plays[move-1][1], self.size)
            else:
                id += "??"
        return id


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

    def __init__(self, size, board=None):
        self.size = size
        self.board = board.board

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
