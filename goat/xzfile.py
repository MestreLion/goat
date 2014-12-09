# -*- coding: utf-8 -*-

'''Wrapper to make LZMA module (backported from Python 3.3) work with tarfile
    Taken directly from Python 3 tarfile module latest source code
    https://hg.python.org/cpython/file/tip/Lib/tarfile.py
    See commit https://hg.python.org/cpython/rev/899a8c7b2310
    Copyright (C) 2011 Lars Gustaebel <lars@gustaebel.de>
'''

import tarfile

def is_xzfile(name):
    try:
        t = xzopen(name)
        t.close()
        return True
    except tarfile.TarError:
        return False

def xzopen(name, mode="r", fileobj=None, preset=None, **kwargs):
    """Open lzma compressed tar archive name for reading or writing.
       Appending is not allowed.
    """
    if mode not in ("r", "w"):
        raise ValueError("mode must be 'r' or 'w'")

    try:
        import lzma
    except ImportError:
        # Pypi: backports.lzma, also requires Debian's liblzma-dev
        import backports.lzma as lzma

    fileobj = lzma.LZMAFile(fileobj or name, mode, preset=preset)

    try:
        t = tarfile.TarFile.taropen(name, mode, fileobj, **kwargs)
    except (lzma.LZMAError, EOFError):
        fileobj.close()
        if mode == 'r':
            raise tarfile.ReadError("not an lzma file")
        raise
    except:
        fileobj.close()
        raise
    t._extfileobj = False
    return t
