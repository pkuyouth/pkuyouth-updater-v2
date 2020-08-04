#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ---------------------------------------
# Project: PKUYouth Webserver v2
# File: const.py
# Created Date: 2020-08-03
# Author: Xinghong Zhong
# ---------------------------------------
# Copyright (c) 2020 PKUYouth

import os
from ._internal import absp, mkdir

CACHE_DIR = absp("../cache/")
CONFIG_INI = absp("../config.ini")

mkdir(CACHE_DIR)
