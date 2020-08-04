#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ---------------------------------------
# Project: PKUYouth Webserver v2
# File: utils.py
# Created Date: 2020-08-03
# Author: Xinghong Zhong
# ---------------------------------------
# Copyright (c) 2020 PKUYouth

import gzip
import pickle
import hashlib

try:
    import simplejson as json
except ImportError:
    import json

from ._internal import mkdir


def b(s, encoding="utf-8"):
    """ str/int/float to bytes """
    if isinstance(s, bytes):
        return s
    if isinstance(s, (str, int ,float)):
        return str(s).encode(encoding)
    raise TypeError("unsupported type %s of %r" % (s.__class__.__name__, s))

def u(s, encoding="utf-8"):
    """ bytes/int/float to str """
    if isinstance(s, (str, int, float)):
        return str(s)
    if isinstance(s, bytes):
        return s.decode(encoding)
    raise TypeError("unsupported type %s of %r" % (s.__class__.__name__, s))

def xMD5(s):
    return hashlib.md5(b(s)).hexdigest()

def pgz_dump(obj, file):
    with gzip.open(file, 'wb') as fp:
        pickle.dump(obj, fp)

def pgz_load(file):
    with gzip.open(file, 'rb') as fp:
        return pickle.load(fp)

def jgz_dump(obj, file):
    with gzip.open(file, 'wt') as fp:
        json.dump(obj, fp)

def jgz_load(file):
    with gzip.open(file, 'rt') as fp:
        return json.load(fp)

class Singleton(type):

    _inst = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._inst:
            cls._inst[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._inst[cls]
