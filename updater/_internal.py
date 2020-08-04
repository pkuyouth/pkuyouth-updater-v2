#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ---------------------------------------
# Project: PKUYouth Webserver v2
# File: _internal.py
# Created Date: 2020-08-03
# Author: Xinghong Zhong
# ---------------------------------------
# Copyright (c) 2020 PKUYouth

import os

def mkdir(path):
    if not os.path.exists(path):
        os.mkdir(path)

def absp(*path):
    return os.path.normpath(os.path.abspath(
            os.path.join(os.path.dirname(__file__), *path)))
