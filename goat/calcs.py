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

'''Calculation hooks'''

import os
import logging
import json

import matplotlib.pyplot as plt  # Debian: python-matplotlib
import numpy  # Debian: python-numpy
import scipy.stats  # Debian: python-scipy

import globals as g
import ascii
import gogame
import utils

log = logging.getLogger(__name__)

def board_points(size):
    points = []
    limits = (0, size - 1)

    for i in xrange(size):
        for j in xrange(size):
            neighs = []
            for neigh in [(i, j-1),
                          (i, j+1),
                          (i-1, j),
                          (i+1, j)]:
                if (limits[0] <= neigh[0] <= limits[1] and
                    limits[0] <= neigh[1] <= limits[1]):
                    neighs.append(neigh)
            points.append(((i, j), neighs))
    return points


class Chart(object):
    def __init__(self):
        self.fig = plt.figure()
        self.ax = self.fig.add_subplot(111)

    def plot(self, *args, **kwargs):
        self.ax.plot(*args, **kwargs)

    def set(self, title="", xlabel="", ylabel="", loc=0, grid=True, semilog=False, loglog=False, legend=True):
        if legend:  self.ax.legend(loc=loc, labelspacing=0.2, prop={'size': 8})
        if xlabel:  self.ax.set_xlabel(xlabel, size=10)
        if ylabel:  self.ax.set_ylabel(ylabel, size=10)
        if title:
            size = 12 if title.count('\n') < 2 else 11
            self.ax.set_title(title, size=size)
        if grid:    self.ax.grid()
        if semilog: self.ax.semilogy()
        if loglog:  self.ax.loglog()
        self.ax.tick_params(axis='both', which='major', labelsize=8)

    def save(self, name):
        for ext in ['png', 'eps', 'svg']:
            path = os.path.join(g.RESULTSDIR, "%s.%s" % (name, ext))
            self.fig.savefig(path, dpi=240)
        #launchfile(path)

    def close(self):
        plt.close(self.fig)


class Hook(object):
    def __init__(self, size):
        pass
    def gamestart(self, game, board, chart=False):
        pass
    def move(self, game, board, move):
        pass
    def gameover(self, game, board, chart=False):
        pass
    def end(self):
        pass
    def display(self):
        pass


class MoveHistogram(Hook):
    '''Histogram of number of moves moves per game'''

    def __init__(self, size):
        self.data = {}

    def gameover(self, game, board, chart=False):
        if not game.id:
            game.setup()
        moves = len(game.moves)
        self.data[game.id] = moves

    def end(self):
        datafile = os.path.join(g.USERDIR, 'hooks', self.__class__.__name__.lower(), 'data.json')
        utils.safemakedirs(os.path.dirname(datafile))
        with open(datafile, 'w') as fp:
            json.dump(self.data, fp, sort_keys=True, separators=(',', ': '), indent=0)

        moves = sorted(self.data.values())
        games = len(moves)
        self._save_result(games, moves)

    def display(self):
        datafile = os.path.join(g.USERDIR, 'hooks', self.__class__.__name__.lower(), 'data.json')
        with open(datafile, 'r') as fp:
            self.data = json.load(fp)

        moves = sorted(self.data.values())
        games = len(moves)

        self._save_result(games, moves)

        array = numpy.array(moves)
        minmoves = numpy.min(array)
        maxmoves = numpy.max(array)
        mode, count = scipy.stats.mode(array)
        numpy.std(array)
        title = ("Moves per Game - Histogram of %d games\n"
                "Min=%d, Avg=%.01f, Mode=%d (x %d), Max=%d\n"
                "Std=%.01f, Skew=%.03f, Kurtosis=%.03f" % (
                    games,
                    minmoves,
                    numpy.mean(array),
                    mode, count,
                    maxmoves,
                    numpy.std(array),
                    scipy.stats.skew(array),
                    scipy.stats.kurtosis(array),
                    ))
        log.info(title)

        binwidth = 1
        bins = range(minmoves, maxmoves + binwidth + 1, binwidth)

        chart = Chart()
        chart.ax.hist(moves, bins=bins, label="Histogram")
        chart.set(xlabel="Moves", ylabel="Games of n moves", loc=2, title=title)

        survivors = []
        gamesleft = games
        i = 0
        for m in xrange(max(moves) + 1):
            while i < games and m == moves[i]:
                gamesleft -= 1
                i += 1
            survivors.append(gamesleft)

        chart.ax = chart.ax.twinx()
        chart.plot(survivors, label="Games left",  color="red")
        chart.set(loc=3, ylabel="Games of at least n moves")

        chart.save("move_histogram_%s" % games)
        chart.close()

    def _save_result(self, games, moves):
        resultsfile = os.path.join(g.RESULTSDIR, "move_histogram_%s.json" % games)
        with open(resultsfile, 'w') as fp:
            json.dump(moves, fp, separators=(',', ': '), indent=0)


class TimeLine(object):
    '''Game evolution of stones in board and accumulated prisoners per move'''

    def __init__(self, size):
        self.data = {}
        self.gamedata = {}
        self.points = board_points(size)
        self.games = 0

        self.totalblacks = []
        self.totalwhites = []
        self.totalblackscaptured = []
        self.totalwhitescaptured = []

    def gamestart(self, game, board, chart=False):
        # assuming there is no handicap!
        self.gamedata = dict(blackstones = [0],
                             whitestones = [0],
                             blackcap = [0],
                             whitecap = [0],)
        if not game.boards:
            game.play()

    def move(self, game, board, move):
        blacks = 0
        whites = 0
        for point, _ in self.points:
            color = board.get(*point)
            if   color == gogame.BLACK: blacks += 1
            elif color == gogame.WHITE: whites += 1

        color, _ = move
        if   color == gogame.BLACK:
            blackscaptured = 0
            whitescaptured = self.gamedata['whitestones'][-1] - whites
        elif color == gogame.WHITE:
            blackscaptured = self.gamedata['blackstones'][-1] - blacks
            whitescaptured = 0
        else:  # pass
            blackscaptured = whitescaptured = 0

        self.gamedata['blackcap'].append(self.gamedata['blackcap'][-1] + blackscaptured)
        self.gamedata['whitecap'].append(self.gamedata['whitecap'][-1] + whitescaptured)

        self.gamedata['blackstones'].append(blacks)
        self.gamedata['whitestones'].append(whites)

    def gameover(self, game, board, chart=False):
        self.data[game.id] = self.gamedata
        if chart:
            chart = Chart()
            chart.plot(self.gamedata['blackstones'], color="red",  lw=2, label="Black stones")
            chart.plot(self.gamedata['whitestones'], color="blue", lw=2, label="White stones")
            chart.plot(self.gamedata['blackcap'], color="red",  label="Black captured")
            chart.plot(self.gamedata['whitecap'], color="blue", label="White captured")
            chart.set(title="Stones per Move\n%s" % game.description, xlabel="Moves", ylabel="Stones", loc=2)
            chart.save("timeline_%s" % game.id)
            chart.close()
            self.end()

    def prettydict(self, obj, indent=1, _lvl=0):
        sep = " " * indent
        if isinstance(obj, dict):
            return ('{\n%s%s\n%s}') % (
                sep * _lvl,
                (",\n%s" % (sep * _lvl)).join(['"%s": %s' % (k, self.prettydict(v, indent, _lvl+1))
                                        for k, v in sorted(obj.iteritems())]),
                sep * (_lvl-1))
        else:
            result = json.dumps(obj, separators=(',',':')).replace('],[', '],\n%s[' % (sep * _lvl))
            return result.replace('[[', '[\n%s[' % (sep * _lvl)).replace(']]', ']\n%s]' % (sep * (_lvl-1)))

    def end(self):
        datafile = os.path.join(g.USERDIR, 'hooks', self.__class__.__name__.lower(), 'data.json')
        utils.safemakedirs(os.path.dirname(datafile))
        with open(datafile, 'w') as fp:
            fp.write(self.prettydict(self.data) + '\n')
            #json.dump(self.data, fp, sort_keys=True)

        games = len(self.data)
        result = {key: tuple(gamedata[key] for gamedata in self.data.itervalues()) for key in self.gamedata}

        self._save_result(games, result)

    def display(self):
        datafile = os.path.join(g.USERDIR, 'hooks', self.__class__.__name__.lower(), 'data.json')
        with open(datafile, 'r') as fp:
            self.data = json.load(fp)

        games = len(self.data)
        result = {key: tuple(gamedata[key] for gamedata in self.data.itervalues())
                  for key in self.data[self.data.iterkeys().next()]}
        self._save_result(games, result)

        plots = [
            dict(color="red",  lw=1.0, ls="-", label="Black stones",   source=result['blackstones']),
            dict(color="blue", lw=1.0, ls="-", label="White stones",   source=result['whitestones']),
            dict(color="red",  lw=0.5, ls="-", label="Black captured", source=result['blackcap']),
            dict(color="blue", lw=0.5, ls="-", label="White captured", source=result['whitecap']),
        ]

        chart = Chart()
        for plot in plots:
            maxmoves = len(sorted(plot['source'], key=len, reverse=True)[0])
            data = numpy.array([game + [numpy.nan] * (maxmoves - len(game)) for game in plot['source']])
            data = numpy.ma.masked_array(data, numpy.isnan(data))
            chart.plot(numpy.mean(data, axis=0), color=plot['color'], lw=plot['lw'], label=plot['label'] + " - avg", ls=plot['ls'])
            chart.plot(numpy.max( data, axis=0), color=plot['color'], lw=plot['lw'], label=plot['label'] + " - max", ls=':')
            chart.plot(numpy.min( data, axis=0), color=plot['color'], lw=plot['lw'], label=plot['label'] + " - min", ls=':')
        chart.set(title="Stones per Move - %d games" % games,
                  xlabel="Move", ylabel="Stones", loc=2)
        chart.save("timeline_%d" % games)
        chart.close()


    def _save_result(self, games, data):
        resultsfile = os.path.join(g.RESULTSDIR, "timeline_%s.json" % games)
        with open(resultsfile, 'w') as fp:
            fp.write(self.prettydict(data) + '\n')


class StonesPerSquare(Hook):
    def __init__(self, size):
        self.size = size
        self.games = 0
        limits = (0, self.size - 1)
        self.points = (StoneCountCenterPoint((limits[0], limits[0]), "Lower Left",  "red",    limits),
                       StoneCountCenterPoint((limits[0], limits[1]), "Lower Right", "green",  limits),
                       StoneCountCenterPoint((limits[1], limits[0]), "Upper Left",  "blue",   limits),
                       StoneCountCenterPoint((limits[1], limits[1]), "Upper Right", "orange", limits),
                       StoneCountCenterPoint(2*(limits[1]/2,), "Center", "black", limits),
                       )

        for center in self.points:
            center.gamestones = []
            center.gameblacks = []
            center.gamewhites = []
            center.gamewiners = []
            center.gamelosers = []

    def gameover(self, game, board, chart=False, discard=False):
        if discard:
            return

        self.games += 1
        if self.games % 101 == 0:
            chart = True

        if game.winner == gogame.BLACK:
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

            for i, perimeter in enumerate(center.perimeters):
                if center.corner:
                    for point in perimeter:
                        color = board.get(*point)
                        if   color == gogame.BLACK: blacks += 1
                        elif color == gogame.WHITE: whites += 1
                    center.stones.append(blacks + whites)
                    center.blacks.append(blacks)
                    center.whites.append(whites)
                else:
                    if i % 2 == 0:
                        for point in center.perimeters[i/2]:
                            color = board.get(*point)
                            if   color == gogame.BLACK: blacks += 1
                            elif color == gogame.WHITE: whites += 1
                        center.stones.append(blacks + whites)
                        center.blacks.append(blacks)
                        center.whites.append(whites)
                    else:
                        center.stones.append(center.stones[-1])
                        center.blacks.append(center.blacks[-1])
                        center.whites.append(center.whites[-1])

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

            log.info("Games processed: %d", self.games)
            self.end()

    def end(self):
        chartlin = Chart()
        chartlog = Chart()
        for center in self.points:
            games = len(center.gamestones)
            if games ==0:
                return
            areaavg = []
            areamin = []
            areamax = []
            for n, _ in enumerate(center.perimeters):
                sum = 0
                min = g.BOARD_SIZE**2 + 1
                max = -1
                for _, game in enumerate(center.gamestones):
                    v = game[n]
                    sum += v
                    if v < min: min = v
                    if v > max: max = v

                areaavg.append(float(sum / games))
                areamin.append(min)
                areamax.append(max)

            for chart in [chartlin, chartlog]:
                chart.plot(areaavg, label=center.label + " - Avg", color=center.color)
                chart.plot(areamin, label=center.label + " - Min", color=center.color, ls=':')
                chart.plot(areamax, label=center.label + " - Max", color=center.color, ls='--')

        chartlin.set(loc=2, xlabel="Area (distance from point to edge)", ylabel="Stones",
                     title="Stones per increasing areas - Average of %d games" % games)
        chartlin.save("stones_average_%d" % games)

        chartlog.set(loc=2, xlabel="Area (distance from point to edge)", ylabel="Stones (log)",
                     title="Stones per increasing areas - Semilog - Average of %d games" % games,
                     loglog=True)
        chartlog.save("stones_average_%d_log" % games)


class FractalDimension(Hook):
    def __init__(self, size):
        self.size = size
        self.games = 0
        limits = (0, self.size - 1)
        self.corners = (StoneCountCenterPoint((limits[0], limits[0]), "Lower Left",  "red",    limits),
                       StoneCountCenterPoint((limits[0], limits[1]), "Lower Right", "green",  limits),
                       StoneCountCenterPoint((limits[1], limits[0]), "Upper Left",  "blue",   limits),
                       StoneCountCenterPoint((limits[1], limits[1]), "Upper Right", "orange", limits),
                       #StoneCountCenterPoint(2*(limits[1]/2,), "Center", "black", limits),
                       )
        self.totalstones = []


    def gameover(self, game, board, chart=False, discard=False):
        if discard:
            return

        self.games += 1
        if self.games % 10000 == 0:
            chart = True

        for corner in self.corners:
            stones = 0
            corner.stones = []
            for perimeter in corner.perimeters:
                for point in perimeter:
                    if board.get(*point) is not None:
                        stones += 1
                corner.stones.append(stones)

        gamestones = []
        corners = float(len(self.corners))
        for perimeter in xrange(self.size):
            stones = 0
            for corner in self.corners:
                stones += corner.stones[perimeter]
            if stones > 0:
                gamestones.append(stones / corners)

        samples = len(gamestones)
        squaresides = list(xrange(1 + self.size - samples, self.size + 1))
        logx = numpy.log(squaresides)
        logy = numpy.log(gamestones)
        coeffs = numpy.polyfit(logx, logy, deg=1)
        poly = numpy.poly1d(coeffs)
        yfit = lambda x: numpy.exp(poly(numpy.log(x)))

        self.totalstones.append(coeffs[0])

        if chart:
            figavg = Chart()
            figavg.plot(squaresides, gamestones, 'bo', label="Game Data")
            figavg.plot(squaresides, yfit(squaresides), 'r-', label="Linear Regression")
            figavg.set(loc=2, xlabel="Square Side", ylabel="Stones", loglog=True,
                       title="Stones per increasing squares - Game %s, m = %.2f" % (game.name, coeffs[0]))
            figavg.save("fractal_%s_log" % game.name)
            figavg.close()

            figlin = Chart()
            figlin.plot(squaresides, gamestones, label="Stones", color="red")
            figlin.set(loc=2, xlabel="Square Side", ylabel="Stones",
                       title="Stones per increasing squares - Game %s" % game.name)
            figlin.save("fractal_%s" % game.name)
            figlin.close()

            log.info("Games processed: %d", self.games)
            self.end()

    def end(self):
        games = len(self.totalstones)
        chart = Chart()
        chart.ax.hist(self.totalstones, bins=20)
        chart.set(xlabel="Exponent", ylabel="Games", legend=False,
                   title="Stones per increasing squares - Histogram of %d games" % games)
        chart.save("fractal_histogram_%s" % games)
        chart.close()


class StoneCountCenterPoint(object):
    def __init__(self, point, label, color, limits):
        self.point = point
        self.label = label
        self.color = color

        self.corner = self.point[0] in limits and self.point[1] in limits

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


class LibertiesPerMove(Hook):
    def __init__(self, size):
        self.totalliberties = []
        self.gameliberties = []
        self.maxmoves = 0
        self.points = board_points(size)

    def gamestart(self, game, board, chart):
        self.gameliberties = []

    def move(self, game, board, move):
        liberties = 0
        for point, neighs in self.points:
            if board.get(*point) is not None:
                for neigh in neighs:
                    if board.get(*neigh) is None:
                        liberties += 1
        self.gameliberties.append(liberties)

    def gameover(self, game, board, chart=False, discard=False):
        if discard:
            return

        self.totalliberties.append(self.gameliberties)
        moves = len(self.gameliberties)
        if moves > self.maxmoves:
            self.maxmoves = moves

        if chart:
            chart = Chart()
            chart.plot(self.gameliberties, label="Liberties", color="red")
            chart.set(loc=2, xlabel="Moves", ylabel="Liberties", title="Liberties per move - Game %s" % game.name)  # loc=2: legend on upper left
            chart.save("liberties_%s" % game.name)
            chart.close()

    def end(self):
        libavg = []
        libmin = []
        libmax = []
        libgames = []
        for n in xrange(self.maxmoves):
            sum = 0
            games = 0
            min = g.BOARD_SIZE**2 + 1
            max = -1
            for game in self.totalliberties:
                if len(game) > n:
                    games += 1
                    v = game[n]
                    sum += v
                    if v < min: min = v
                    if v > max: max = v

            if games == 0:
                continue

            libavg.append(float(sum / games))
            libmin.append(min)
            libmax.append(max)
            libgames.append(games)

        if not libavg:
            return

        chart = Chart()
        chart.plot(libavg, label="Avgerage", color="red")
        chart.plot(libmin, label="Minimum",  color="red", ls=':')
        chart.plot(libmax, label="Maximum",  color="red", ls='--')

        games = len(self.totalliberties)
        chart.set(loc=2, xlabel="Moves", ylabel="Liberties",
                  title="Liberties per move - Average of %d games" % games)  # loc=2: legend on upper left

        chart.ax = chart.ax.twinx()
        chart.plot(libgames, label="Games",  color="blue", ls=':')
        chart.set(loc=3, ylabel="Games")  # loc=2: legend on upper left

        chart.save("liberties_average_%d" % games)
        chart.close()



class Territory(object):
    def __init__(self):
        self.points = []
        self.color = None

class Territories(Hook):
    def __init__(self, size):
        self.points = board_points(size)
        self.totalterritories = []
        self.gameterritories = []
        self.gameskip = False
        self.games = 0

    def gamestart(self, game, board, chart=False):
        self.gameskip = not game.get_root().get("RU") == "AGA"
        self.gameterritories = []

    def gameover(self, game, board, chart=False, discard=False):
        if discard or self.gameskip:
            return

        self.games += 1

        for point, neighs in self.points:
            color = board.get(*point)
            if color is None:
                for neigh in neighs:
                    for t in self.gameterritories:
                        if neigh in t.points:
                            t.points.append(point)
                            break
                    else:
                        continue
                    break
                else:
                    t = Territory()
                    t.points.append(point)
                    for neigh in neighs:
                        if board.get(*neigh) is None:
                            t.points.append(neigh)
                    self.gameterritories.append(t)

        print ascii.render_board(board)
        for territory in sorted(self.gameterritories, key=lambda x: len(x.points)):
            continue
            log.info("%d: %r",  len(territory.points), territory.points)
        print


    def end(self):
        log.info("Territories: %d", self.games)
        pass
