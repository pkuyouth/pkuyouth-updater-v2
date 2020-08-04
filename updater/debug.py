#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ---------------------------------------
# Project: PKUYouth Webserver v2
# File: debug.py
# Created Date: 2020-08-03
# Author: Xinghong Zhong
# ---------------------------------------
# Copyright (c) 2020 PKUYouth

import os
from io import BytesIO
from pprint import pprint
import requests
from PIL import Image
from .const import CACHE_DIR

def print_request(response, *, body=False):
    r = response.request
    print("=== REQUEST BGEIN ===")
    print("> URL: %s" % r.url)
    print("> Headers:")
    pprint(dict(r.headers))
    if body:
        print("> Body:")
        pprint(r.body)
    print("=== REQUEST END ===")

def print_response(response, *, json=False):
    r = response
    print("=== RESPONSE BEGIN ===")
    print("> URL: %s" % r.url)
    print("> Status: %s" % r.status_code)
    print("> Headers:")
    pprint(dict(r.headers))
    print("> Cookies:")
    pprint(dict(r.cookies))
    if json:
        print("> JSON:")
        pprint(r.json())
    print("=== RESPONSE END ===")

def print_set_cookies(response):
    print("=== SET COOKIES BEGIN ===")
    for v in response.raw.headers.getheaders('set-cookie'):
        print(v)
    print("=== SET COOKIES END ===")

def print_client_cookies(client):
    s = client._session
    print("=== CLIENT COOKIES BEGIN ===")
    for domain, v_domain in s.cookies._cookies.items():
        for path, v_path in v_domain.items():
            for key, cookie in v_path.items():
                print(cookie)
    print("=== CLIENT COOKIES END ===")

def dump_response_content(response, filename):
    filepath = os.path.join(CACHE_DIR, filename)
    with open(filepath, 'wb') as fp:
        fp.write(response.content)

def download_static(url, filename=None):
    r = requests.get(url)
    if filename is None:
        filename = url[ url.rfind('/') + 1 : ]
    filepath = os.path.join(CACHE_DIR, filename)
    with open(filepath, 'wb') as fp:
        fp.write(r.content)

def get_image_size(im, format='jpeg', **kwargs):
    with BytesIO() as buf:
        im.save(buf, format=format, **kwargs)
        return len(buf.getvalue())
