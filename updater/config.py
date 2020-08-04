#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ---------------------------------------
# Project: PKUYouth Webserver v2
# File: config.py
# Created Date: 2020-08-03
# Author: Xinghong Zhong
# ---------------------------------------
# Copyright (c) 2020 PKUYouth

from configparser import RawConfigParser
from .const import CONFIG_INI
from .utils import Singleton

class BaseConfig(object):

    def __init__(self, config_file=None):
        self._config = RawConfigParser()
        self._config.read(config_file, encoding="utf-8-sig")

    def get(self, section, key):
        return self._config.get(section, key)

    def getint(self, section, key):
        return self._config.getint(section, key)

    def getfloat(self, section, key):
        return self._config.getfloat(section, key)

    def getboolean(self, section, key):
        return self._config.getboolean(section, key)


class UpdaterConfig(BaseConfig, metaclass=Singleton):

    def __init__(self, config_file=CONFIG_INI):
        super().__init__(config_file=config_file)

    @property
    def mpwx_username(self):
        return self._config.get('mpwx', 'username')

    @property
    def mpwx_password(self):
        return self._config.get('mpwx', 'password')

    @property
    def mysql_host(self):
        return self._config.get('mysql', 'host')

    @property
    def mysql_port(self):
        return self._config.getint('mysql', 'port')

    @property
    def mysql_user(self):
        return self._config.get('mysql', 'user')

    @property
    def mysql_password(self):
        return self._config.get('mysql', 'password')

    @property
    def mysql_database(self):
        return self._config.get('mysql', 'database')

    @property
    def mysql_charset(self):
        return self._config.get('mysql', 'charset')

    @property
    def qiniu_access_key(self):
        return self._config.get('qiniu', 'access_key')

    @property
    def qiniu_secret_key(self):
        return self._config.get('qiniu', 'secret_key')

    @property
    def qiniu_bucket(self):
        return self._config.get('qiniu', 'bucket')
