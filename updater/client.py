#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ---------------------------------------
# Project: PKUYouth Webserver v2
# File: client.py
# Created Date: 2020-08-03
# Author: Xinghong Zhong
# ---------------------------------------
# Copyright (c) 2020 PKUYouth

import os
import re
import time
import calendar
import uuid
import math
import random
import base64
from urllib.parse import quote
from requests import Session
import qiniu
from .auth import get_pwd, get_pgv_pvi, get_pgv_si
from .cache import MPWXClientCache
from .utils import u, b, pgz_dump, pgz_load
from .const import CACHE_DIR

qiniu.config.set_default(
    default_zone=qiniu.zone.Zone(home_dir=CACHE_DIR)
)

class MPWXClient(object):

    def __init__(self, username, password, timeout=10):

        self._username = username
        self._password = password
        self._timeout = timeout

        self._token = None

        cache_key = u(base64.b64encode(b(username)).rstrip(b'='))
        self._cache_file = os.path.join(CACHE_DIR, "%s_session.gz" % cache_key)

        self._session = Session()
        self._session.headers.update({
            "accept": "*/*",
            "accept-encoding": "gzip, deflate, br",
            "accept-language": "en-US,en;q=0.9",
            "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Ubuntu Chromium/79.0.3945.79 Chrome/79.0.3945.79 Safari/537.36",
        })

        if os.path.exists(self._cache_file):
            cache = pgz_load(self._cache_file)
            if not cache.is_expired():
                self._token = cache.token
                self._session.cookies = cache.cookies
                return

        timestamp = 'Sun, 18 Jan 2038 00:00:00 GMT'
        gmt_format = '%a, %d %b %Y %H:%M:%S GMT'

        domain = "mp.weixin.qq.com"
        expires = calendar.timegm(time.strptime(timestamp, gmt_format))

        self._session.cookies.set("pgv_pvi", get_pgv_pvi(), domain=domain, expires=expires)
        self._session.cookies.set("pgv_si", get_pgv_si(), domain=domain)
        self._session.cookies.set("uuid", uuid.uuid4().hex, domain=domain)

    @property
    def logined(self):
        return self._token is not None

    def dump_session(self):
        if not self.logined:
            return
        cache = MPWXClientCache(self._session.cookies, self._token)
        pgz_dump(cache, self._cache_file)

    def close(self):
        self._session.close()

    def _request(self, method, url, params=None, data=None, **kwargs):
        kwargs.setdefault("timeout", self._timeout)
        return self._session.request(method, url, params=params, data=data, **kwargs)

    def _get(self, url, params=None, **kwargs):
        return self._request('GET', url, params=params, **kwargs)

    def _post(self, url, data=None, **kwargs):
        return self._request('POST', url, data=data, **kwargs)

    def homepage(self):
        r = self._get(
            url='https://mp.weixin.qq.com',
            headers={
                "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
                "cache-control": "max-age=0",
                "sec-fetch-mode": "navigate",
                "sec-fetch-site": "none",
                "sec-fetch-user": "?1",
                "upgrade-insecure-requests": "1",
            }
        )
        return r

    def bizlogin_prelogin(self):
        r = self._post(
            url='https://mp.weixin.qq.com/cgi-bin/bizlogin',
            headers={
                "origin": "https://mp.weixin.qq.com",
                "referer": "https://mp.weixin.qq.com/",
                "sec-fetch-mode": "cors",
                "sec-fetch-site": "same-origin",
                "x-requested-with": "XMLHttpRequest",
            },
            data={
                "action": "prelogin",
                "token": "",
                "lang": "zh_CN",
                "f": "json",
                "ajax": "1",
            }
        )
        return r

    def bizlogin_startlogin(self):
        r = self._post(
            url='https://mp.weixin.qq.com/cgi-bin/bizlogin',
            headers={
                "origin": "https://mp.weixin.qq.com",
                "referer": "https://mp.weixin.qq.com/",
                "sec-fetch-mode": "cors",
                "sec-fetch-site": "same-origin",
                "x-requested-with": "XMLHttpRequest",
            },
            params={
                "action": "startlogin",
            },
            data={
                "username": self._username,
                "pwd": get_pwd(self._password),
                "imgcode": "",
                "f": "json",
                "userlang": "zh_CN",
                "redirect_url": "",
                "token": "",
                "lang": "zh_CN",
                "ajax": "1",
            }
        )
        return r

    def bizlogin_validate(self):
        r = self._get(
            url='https://mp.weixin.qq.com/cgi-bin/bizlogin',
            headers={
                "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
                "referer": "https://mp.weixin.qq.com/",
                "sec-fetch-mode": "navigate",
                "sec-fetch-site": "same-origin",
                "sec-fetch-user": "?1",
                "upgrade-insecure-requests": "1",
            },
            params={
                "action": "validate",
                "lang": "zh_CN",
                "account": self._username,
                "token": "",
            }
        )
        return r

    def loginqrcode_ask(self):
        r = self._get(
            url='https://mp.weixin.qq.com/cgi-bin/loginqrcode',
            headers={
                "referer": "https://mp.weixin.qq.com/cgi-bin/bizlogin?action=validate&lang=zh_CN&account=%s&token=" % quote(self._username),
                "sec-fetch-mode": "cors",
                "sec-fetch-site": "same-origin",
            },
            params={
                "action": "ask",
                "token": "",
                "lang": "zh_CN",
                "f": "json",
                "ajax": "1",
            }
        )
        return r


    def loginqrcode_getqrcode(self):
        r = self._get(
            url='https://mp.weixin.qq.com/cgi-bin/loginqrcode',
            headers={
                "accept": "image/webp,image/apng,image/*,*/*;q=0.8",
                "referer": "https://mp.weixin.qq.com/cgi-bin/bizlogin?action=validate&lang=zh_CN&account=%s&token=" % quote(self._username),
                "sec-fetch-mode": "no-cors",
                "sec-fetch-site": "same-origin",
            },
            params={
                "action": "getqrcode",
                "param": "4300",
                "rd": str(math.floor(1e3 * random.random())),
            }
        )
        return r

    def bizlogin_login(self):
        r = self._post(
            url='https://mp.weixin.qq.com/cgi-bin/bizlogin',
            headers={
                "origin": "https://mp.weixin.qq.com",
                "referer": "https://mp.weixin.qq.com/cgi-bin/bizlogin?action=validate&lang=zh_CN&account=%s&token=" % quote(self._username),
                "sec-fetch-mode": "cors",
                "sec-fetch-site": "same-origin",
                "x-requested-with": "XMLHttpRequest",
            },
            params={
                "action": "login",
            },
            data={
                "userlang": "zh_CN",
                "redirect_url": "",
                "token": "",
                "lang": "zh_CN",
                "f": "json",
                "ajax": "1",
            }
        )

        self._token = re.search(r'token=(\d+)', r.json()['redirect_url']).group(1)
        return r

    def newmasssendpage(self, count, begin):
        r = self._get(
            url='https://mp.weixin.qq.com/cgi-bin/newmasssendpage',
            headers={
                "referer": "https://mp.weixin.qq.com/cgi-bin/home?t=home/index&lang=zh_CN&token=%s" % self._token,
                "sec-fetch-mode": "cors",
                "sec-fetch-site": "same-origin",
                "x-requested-with": "XMLHttpRequest",
            },
            params={
                "count": count,
                "begin": begin,
                "token": self._token,
                "lang": "zh_CN",
                "f": "json",
                "ajax": "1",
            }
        )
        return r

    def article_content(self, url):
        r = self._get(
            url=url,
            headers={
                "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
                "cache-control": "max-age=0",
                "sec-fetch-mode": "navigate",
                "sec-fetch-site": "same-origin",
                "sec-fetch-user": "?1",
                "upgrade-insecure-requests": "1",
            }
        )
        return r

    def article_cover(self, url):
        r = self._get(
            url=url,
            headers={
                "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
                "Connection": "keep-alive",
            }
        )
        return r


class QiniuClient(object):

    def __init__(self, access_key, secret_key, bucket):
        self._auth = qiniu.Auth(access_key, secret_key)
        self._bucket = bucket

    @staticmethod
    def _check_response_info(info):
        if not info.ok():
            raise Exception("QiniuClient ERROR: %s" % info.text_body)

    def put_data(self, raw, key):
        token = self._auth.upload_token(self._bucket, key)
        ret, info = qiniu.put_data(token, key, raw)
        self._check_response_info(info)
        return ret, info
