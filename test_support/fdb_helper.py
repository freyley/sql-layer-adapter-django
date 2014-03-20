#!/usr/bin/env python -u

CHUNK_SIZE = 4

import os
import sys
import subprocess

import runtests

from django import VERSION as DJANGO_VERSION
FULL_MODULE = DJANGO_VERSION[0:2] >= (1,6)

def chunk(l, n):
    for i in xrange(0, len(l), n):
        yield [(FULL_MODULE and (m[0] and m[0].find('.') != -1)) and '.'.join(m) or m[1] for m in l[i:i+n]]

failed = False
modules = runtests.get_test_modules()
for c in chunk(modules, CHUNK_SIZE):
    print 'Running', ' '.join(c)
    args = ['./runtests.py', '--noinput', '--settings=test_fdbsql'] + c
    try:
        p = subprocess.Popen(args, stdout=sys.stdout, stderr=sys.stderr)
        ret = p.wait()
        failed |= (ret != 0)
    except KeyboardInterrupt:
        print 'interrupted'
        p.kill()
        p.wait()
        break
    print ''

if failed:
    sys.exit(1)

