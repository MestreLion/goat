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

import progressbar

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

    archivecachedir = os.path.join(g.USERDIR, 'sources')
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
        'date': 0,
        'error': 0,
        'duplicate': 0,
    }

    library = [_ for _ in walk()]
    librarysize = len(library)
    if g.options.games and librarysize >= g.options.games:
        log.info("Library already has %d games. No games imported", librarysize)
        return

    filelist = list(find_games(g.options.sources))
    listsize = len(filelist)

    class ImportedGameProgress(progressbar.ProgressBarWidget):
        '''Custom Widget for ProgressBar to track imported games'''
        def update(self, pbar):
            return str(games)

    class LibraryProgress(progressbar.ProgressBarWidget):
        '''Custom Widget for ProgressBar to track Library size'''
        def update(self, pbar):
            size = games + librarysize
            return '%d of %d (%.01f%%)' % (size, g.options.games, 100. * size / g.options.games)

    pbar = progressbar.ProgressBar(widgets=[
        ' ', progressbar.Percentage(),
        ' File ', progressbar.SimpleProgress(),
        ', ', ImportedGameProgress(), ' imported.',
        ' Library: ', LibraryProgress(),
        ' ', progressbar.Bar('.'),
        ' ', progressbar.ETA(),
        ' '], maxval=listsize).start()

    try:
        for files, filename in enumerate(filelist, 1):
            pbar.update(files)

            try:
                game = gogame.GoGame(filename, autosetup=False, autoplay=False)
            except gogame.GoGameError as e:
                log.error("Game %s: %s", filename, e)
                skip['error'] += 1
                continue

            # Header filters (that do not depend on setup or plays)
            if not filter_game_header(game, skip):
                continue

            # Populate Game ID and moves
            try:
                game.setup()
            except gogame.GoGameError as e:
                log.error("Game %s: %s", filename, e)
                skip['error'] += 1
                continue

            # Duplicate game
            gamepath = os.path.join(g.LIBRARYDIR, game.id[:2], "%s.sgf" % game.id)
            if os.path.exists(gamepath):
                skip['duplicate'] += 1
                continue

            # Few moves
            if len(game.sgfplays) < 50:
                log.warn("Game %s: only %d moves", filename, len(game.sgfplays))
                skip['fewmoves'] += 1
                continue

            try:
                game.play()
            except gogame.GoGameError as e:
                log.error("Game %s: %s", filename, e)
                skip['error'] += 1
                continue

            log.debug("Importing '%s' from %s", game.id, filename)
            utils.safemakedirs(os.path.dirname(gamepath))
            shutil.copyfile(filename, gamepath)

            games += 1
            if g.options.games and games + librarysize >= g.options.games:
                break

    except KeyboardInterrupt:
        log.warn("Import aborted by user")

    pbar.finish()
    log.info("Files processed: %d", files)
    log.info("Ignored games: %r", skip)
    log.info("Games imported: %d (%.01f%%)", games, 100. * games / files)
    log.info("Games in Library: %d", games + librarysize)


def filter_game_header(game, skip):
    # Rules
    if not game.header.has_property("RU") or game.header.get("RU").lower() != "japanese":
        skip['rules'] += 1
        return

    # Handicap
    if game.header.has_property("HA"):
        skip['handicap'] += 1
        return

    # Result
    try:
        result = game.header.get("RE").split('+')[1].lower()
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
        for rank in [game.header.get("BR"), game.header.get("WR")]:
            level, grade = int(rank[:-1]), rank[-1]
            if grade not in ['d', 'p'] or (grade == 'd' and level < 6):
                skip['nopro'] += 1
                return
    except (KeyError, ValueError):
        skip['rank'] += 1
        return

    # Date
    if not game.header.has_property("DT"):
        skip['date'] += 1
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


def games(maxgames = 0):
    for i, filename in enumerate(walk(), 1):
        yield gogame.GoGame(filename)
        if maxgames and i >= maxgames:
            break
