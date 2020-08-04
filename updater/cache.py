#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ---------------------------------------
# Project: PKUYouth Webserver v2
# File: cache.py
# Created Date: 2020-08-03
# Author: Xinghong Zhong
# ---------------------------------------
# Copyright (c) 2020 PKUYouth

import time

class MPWXClientCache(object):

    def __init__(self, cookies, token, expires=3600):
        self._token = token
        self._cookies = cookies
        self._expired_time = int(time.time()) + expires

    @property
    def token(self):
        return self._token

    @property
    def cookies(self):
        return self._cookies

    def is_expired(self):
        return self._expired_time < int(time.time())

