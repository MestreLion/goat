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

import matplotlib.pyplot as plt  # Debian: python-matplotlib
import numpy  # Debian: python-numpy

import globals as g
import utils
import ascii
import gogame

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
        if legend:  self.ax.legend(loc=loc, labelspacing=0.2, prop={'size': 10})
        if xlabel:  self.ax.set_xlabel(xlabel)
        if ylabel:  self.ax.set_ylabel(ylabel)
        if title:   self.ax.set_title(title)
        if grid:    self.ax.grid()
        if semilog: self.ax.semilogy()
        if loglog:  self.ax.loglog()

    def save(self, name):
        for ext in ['png', 'eps', 'svg']:
            path = os.path.join(g.CACHEDIR, "%s.%s" % (name, ext))
            self.fig.savefig(path, dpi=300)
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
    def gameover(self, game, board, chart=False, discard=False):
        pass
    def end(self):
        pass

class MoveHistogram(Hook):
    pass

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
                for i, game in enumerate(center.gamestones):
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
