#!/usr/bin/env python

#    Copyright (C) 2006  Andrew Straw  <strawman@astraw.com>
#
#    This program can be distributed under the terms of the GNU LGPL.
#    See the file COPYING.
#

import os, stat, errno
import fuse
from json import loads
from fuse import Fuse
from plyvel import DB


if not hasattr(fuse, '__version__'):
    raise RuntimeError, \
        "your fuse-py doesn't know of fuse.__version__, probably it's too old."

fuse.fuse_python_api = (0, 2)

db = DB('/home/cujo/nfs/db/db1')


class LWStat(fuse.Stat):
    def __init__(self):
        self.st_mode = 0
        self.st_ino = 0
        self.st_dev = 0
        self.st_nlink = 0
        self.st_uid = 0
        self.st_gid = 0
        self.st_size = 0
        self.st_atime = 0
        self.st_mtime = 0
        self.st_ctime = 0


class LWFS(Fuse):

    def getattr(self, path):
        st = LWStat()
        if path == '/':
            st.st_mode = stat.S_IFDIR | 0755
            st.st_nlink = 2
        elif db.get(path[1:].encode()):
            st.st_mode = stat.S_IFREG | 0444
            st.st_nlink = 1
            st.st_size = len(db.get(path[1:].encode()))
        else:
            return -errno.ENOENT
        return st

    def readdir(self, path, offset):
        yield fuse.Direntry('.')
        yield fuse.Direntry('..')
        for name, _ in db.iterator(prefix=b'f_'):
            yield fuse.Direntry(name)

    def open(self, path, flags):
        accmode = os.O_RDONLY | os.O_WRONLY | os.O_RDWR
        if (flags & accmode) != os.O_RDONLY:
            return -errno.EACCES

    def read(self, path, size, offset):
        content = db.get(path[1:].encode())
        if not content:
            return -errno.ENOENT
        slen = len(content)
        if offset < slen:
            if offset + size > slen:
                size = slen - offset
            buf = content[offset:offset+size]
        else:
            buf = ''
        return buf

    def statfs(self):
        return fuse.StatVfs(**loads(db.get(b'vfs')))


def main():
    usage = """ Userspace hello example""" + Fuse.fusage
    server = LWFS(version="%prog " + fuse.__version__, usage=usage)
    server.parse(errex=1)
    server.main()

if __name__ == '__main__':
    main()
