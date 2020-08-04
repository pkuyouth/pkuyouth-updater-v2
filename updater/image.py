#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ---------------------------------------
# Project: PKUYouth Webserver v2
# File: image.py
# Created Date: 2020-08-03
# Author: Xinghong Zhong
# ---------------------------------------
# Copyright (c) 2020 PKUYouth

from io import BytesIO
from PIL import Image

BG_COVER_WIDTH = 540
SM_COVER_MIN_SIZE = 130


def compress_sm_cover(im, min_size=SM_COVER_MIN_SIZE, **kwargs):

    kwargs.setdefault('resample', Image.BICUBIC)
    ow, oh = im.size

    if oh >= ow:
        nw = int(min_size)
        nh = int(nw / ow * oh)
    else:
        nh = int(min_size)
        nw = int(nh / oh * ow)

    return im.resize(size=(nw, nh), **kwargs)


def compress_bg_cover(im, width=BG_COVER_WIDTH, **kwargs):

    kwargs.setdefault('resample', Image.BICUBIC)
    ow, oh = im.size

    nw = int(width)
    nh = int(nw / ow * oh)

    if nw >= ow:
        return im

    return im.resize(size=(nw, nh), **kwargs)


def im2bytes(im, **kwargs):
    with BytesIO() as buf:
        im.save(buf, **kwargs)
        return buf.getvalue()
