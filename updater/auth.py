#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ---------------------------------------
# Project: PKUYouth Webserver v2
# File: auth.py
# Created Date: 2020-08-03
# Author: Xinghong Zhong
# ---------------------------------------
# Copyright (c) 2020 PKUYouth

import time
import random
from .utils import xMD5

def get_pwd(password):
    return xMD5(password)

def _tajs_r(c=''):
    d = int(round(2147483647 * (random.random() or 0.5)) * int(time.time() * 1000) % 1e10)
    return "%s%d" % (c, d)

def get_pgv_pvi():
    return _tajs_r()

def get_pgv_si():
    return _tajs_r("s")

