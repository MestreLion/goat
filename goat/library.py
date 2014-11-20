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

'''Import and handle Game Library'''

import os
import logging
import zipfile
import tarfile
import shutil

import globals as g
import gogame
import utils

log = logging.getLogger(__name__)


class ExtractError(Exception):
    pass


def extract(filepath, destdir=""):
    '''Extract a <filepath> archive to a <destdir>
        Raise ExtractError if <filepath> is not an archive of a supported format
    '''

    if os.path.exists(destdir):
        return

    driver = None
    if   zipfile.is_zipfile(filepath): driver = zipfile.ZipFile
    elif tarfile.is_tarfile(filepath): driver = tarfile.open

    if not driver:
        raise ExtractError("Invalid archive format")

    log.debug("Extracting %s to %s", os.path.basename(filepath), destdir)
    archive = driver(filepath, 'r')
    archive.extractall(destdir)


def find_games(paths):
    '''Search for SGF files and archives in <paths>'''

    archivecachedir = os.path.join(g.CACHEDIR, 'sources')
    utils.safemakedirs(archivecachedir)

    for path in paths:
        log.info("Searching for games in %s", os.path.abspath(path))

        for root, dirs, files in os.walk(path):
            for name in files:
                filepath = os.path.join(root, name)
                ext = os.path.splitext(name)[1][1:].lower()

                if ext == "sgf":
                    yield filepath

                elif ext in ['zip', 'gz', 'bz2']:
                    try:
                        destdir = os.path.join(archivecachedir, name)
                        extract(filepath, destdir)
                        dirs.append(destdir)
                    except ExtractError as e:
                        log.warn("Error extracting %s: %s", filepath, e)


def import_sources():
    '''Import source SGF files/archives/folders to the Library'''

    files = 0
    games = 0
    skip = {
        'size': 0,
        'result': 0,
        'rank': 0,
        'handicap': 0,
        'fewmoves': 0,
        'rules': 0,
        'error': 0,
        'duplicate': 0,
    }

    for filename in find_games(g.options.sources):
        log.debug("Processing file %s", filename)
        files += 1

        if files % 10000 == 0:
            log.info("Files processed: %d", files)

        try:
            game = gogame.GoGame.from_sgf(filename)
        except gogame.GoGameError as e:
            log.error("Ignoring game %s: %s", filename, e)
            skip['error'] += 1
            continue

        # Header filters (that do not depend on setup or moves)
        if not filter_game_header(game, skip):
            continue

        # Populate Game ID and moves
        try:
            game.load_moves()
        except gogame.GoGameError as e:
            log.error("Ignoring game %s: %s", filename, e)
            skip['error'] += 1
            continue

        # Duplicate game
        gamepath = os.path.join(g.LIBRARYDIR, game.id[:2], "%s.sgf" % game.id)
        if os.path.exists(gamepath):
            skip['duplicate'] += 1
            continue

        # Few moves
        if len(game.plays) <= 50:
            log.warn("Ignoring game %s: only %d moves", filename, len(game.plays))
            skip['fewmoves'] += 1
            continue

        log.debug("Importing as game %s", game.id)
        utils.safemakedirs(os.path.dirname(gamepath))
        shutil.copyfile(filename, gamepath)

        games += 1
        if g.options.games and games >= g.options.games:
            break

        if games % 1000 == 0:
            log.info("Games imported: %d (%.01f%%)", games, 100. * games / files)

    log.info("Files processed: %d", files)
    log.info("Ignored games: %r", skip)
    log.info("Games imported: %d (%.01f%%)", games, 100. * games / files)


def filter_game_header(game, skip):
    root = game.sgfgame.get_root()

    # Rules
    if not root.has_property("RU") or root.get("RU").lower() != "japanese":
        skip['rules'] += 1
        return

    # Handicap
    if root.has_property("HA"):
        skip['handicap'] += 1
        return

    # Result
    try:
        result = root.get("RE").split('+')[1].lower()
        if result:
            if result[0] in ['r', 't', 'f']:
                # Resign, Timeout, Forfeit
                skip['result'] += 1
                return
            result = float(result)
    except (KeyError,    # No 'RE'sult
            IndexError,  # No '+', might be 'V[oid]', '?', or malformed
            ValueError,  # A comment in result
            ):
        skip['result'] += 1
        return

    # Player Rank
    try:
        for rank in [root.get("BR"), root.get("WR")]:
            level, grade = int(rank[:-1]), rank[-1]
            if grade not in ['d', 'p'] or (grade == 'd' and level < 6):
                skip['nopro'] += 1
                return
    except (KeyError, ValueError):
        skip['rank'] += 1
        return

    # Board Size
    if not game.size == g.options.board_size:
        skip['size'] += 1
        return

    return True

def walk():
    for root, _, files in os.walk(g.LIBRARYDIR):
        for name in files:
            filepath = os.path.join(root, name)
            if os.path.splitext(name)[1][1:].lower() == "sgf":
                yield filepath
