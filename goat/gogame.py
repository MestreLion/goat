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
import json

# Pypi: gomill
import gomill.sgf
import gomill.sgf_moves
import gomill.sgf_properties

import globals as g
import utils


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
            self.initialboard = Board(self.size, self.sgfboard.copy().board)
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
        if not self.id:
            self.setup()

        del self.plays[:]
        boardfile = os.path.join(g.USERDIR, 'boards', self.id[:2], "%s.json" % self.id)

        try:
            with open(boardfile, 'r') as fp:
                # id, board size, description, play size, initial board, play list
                _, size, _, _, initialboard, playlist = json.load(fp)

            self.initialboard = Board.from_ascii(size, initialboard)

            # play index, move, ascii board
            for _, move, asciiboard in playlist:
                board = Board.from_ascii(size, asciiboard)
                color, coord = move
                row, col = coord
                self.plays.append(((color, (row, col)), board))

        except IOError:
            # Play the SGF game
            jsonplays = []
            sgfboard = self.sgfboard.copy()

            for m, move in enumerate(self.sgfplays, 1):
                color, coord = move
                if coord is not None:
                    row, col = coord
                    try:
                        sgfboard.play(row, col, color)
                    except Exception:
                        raise GoGameError("Invalid move #%d: %s[%s]" % (
                            m,
                            color.upper(),
                            gomill.sgf_properties.serialise_go_point(coord, self.size)))

                board = Board(self.size, sgfboard.copy().board)
                self.plays.append((move, board))
                jsonplays.append('[%d, ["%s", %r], %s]' % (m,
                                                          color,
                                                          [row, col],
                                                          board.dumpjson()))

            # Save the boards to JSON
            utils.safemakedirs(os.path.dirname(boardfile))
            with open(boardfile, 'w') as fp:
                fp.write('["%s", %d, "%s", %d, %s, [\n%s\n]]\n' % (
                   self.id,
                   self.size,
                   self.description,
                   len(self.plays),
                   self.initialboard.dumpjson(),
                   ",\n".join(jsonplays)))


class Board(object):

    _to_ascii = {
        None  : " ",
        BLACK : "#",
        WHITE : "O",
    }

    _from_ascii = {
        " "   : None,
        "#"   : BLACK,
        "O"   : WHITE,
    }

    _mapping = {
        None  : None,
        'b'   : BLACK,
        'w'   : WHITE,
    }

    @classmethod
    def from_ascii(cls, size, asciiboard):
        board = []
        for row in reversed(asciiboard):
            board.append([cls._from_ascii[col] for col in row])
        return cls(size, board)

    def __init__(self, size=0, board=None):
        self.size = size

        if board is None:
            self.board = []
            for _ in range(self.size):
                self.board.append([None] * self.size)
        else:
            self.board = board

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

    def dumpjson(self, indent=0):
        spc = indent * " "
        sep = '",\n%s"' % spc
        return '[\n%s"%s"\n]' % (spc, sep.join(self.asciilines()))

    def asciilines(self):
        for row in xrange(self.size - 1, -1, -1):
            line = ""
            for col in xrange(self.size):
                line += self._to_ascii[self.board[row][col]]
            yield line
