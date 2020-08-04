#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ---------------------------------------
# Project: PKUYouth Webserver v2
# File: test_client.py
# Created Date: 2020-08-03
# Author: Xinghong Zhong
# ---------------------------------------
# Copyright (c) 2020 PKUYouth

import sys
sys.path.append('../')

import os
import re
import time
import pickle
import gzip
from pprint import pprint
from io import BytesIO
from PIL import Image
import pymysql
from lxml import etree
from urllib.parse import urlparse, parse_qsl
from updater.config import UpdaterConfig
from updater.client import MPWXClient, QiniuClient
from updater.image import compress_sm_cover, compress_bg_cover
from updater.utils import jgz_dump, jgz_load, mkdir
from updater.const import CACHE_DIR
from updater.debug import print_request, print_response, dump_response_content,\
    print_set_cookies, print_client_cookies, download_static, get_image_size


ADLIST_JSON = os.path.join(CACHE_DIR, "adlist.json.gz")
ADCLIST_JSON = os.path.join(CACHE_DIR, "adclist.json.gz")
IMAGE_CACHE_DIR = os.path.join(CACHE_DIR, "image/")

mkdir(IMAGE_CACHE_DIR)


def test_download_static():
    download_static("https://res.wx.qq.com/mpres/zh_CN/htmledition/pages/login/loginscan/loginscan4f932d.js")
    download_static("https://res.wx.qq.com/mpres/zh_CN/htmledition/3rd/tajs/tajs492dbc.js")
    download_static("https://mp.weixin.qq.com/s?__biz=MzA3NzAzMDEyNg==&mid=200397842&idx=1&sn=959d94ba5a4ff29b6e06a060fc774cf5#rd", "200397842_1.html")
    download_static("https://mp.weixin.qq.com/s?__biz=MzA3NzAzMDEyNg==&mid=2650833181&idx=1&sn=f13ff0050b9d77784ae1f96d6ff040f0#rd", "2650833181_1.html")


def test_login(client):

    if client.logined:
        return

    r = client.homepage()
    r = client.bizlogin_prelogin()
    r = client.bizlogin_startlogin()
    r = client.bizlogin_validate()
    r = client.loginqrcode_ask()
    r = client.loginqrcode_getqrcode()

    dump_response_content(r, "loginqrcode.jpg")

    buf = BytesIO(r.content)
    im = Image.open(buf)

    im.show()

    current_status = -1

    while current_status != 1:

        r = client.loginqrcode_ask()
        rjson = r.json()

        status = rjson['status']

        if status == 0:
            if current_status != 0:
                print("等待扫码")
                current_status = status
        elif status == 4:
            if current_status != 4:
                print("等待确认")
                current_status = status
        elif status == 1:
            if current_status != 1:
                print("确认登录")
                current_status = status
        elif status == 2:
            raise Exception("管理员已拒绝你的操作申请")
        elif status == 3:
            raise Exception("操作申请已过期")
        else:
            pprint(rjson)
            print("Unknown Status !")

        time.sleep(1.5)

    r = client.bizlogin_login()
    client.dump_session()


def test_download_articles_list(client):

    count = 7
    begin = 0
    total = -1

    adlist = []

    while total == -1 or begin <= total:

        print("GET newmasssendpage %d/%d" % (begin, total))

        r = client.newmasssendpage(count, begin)
        rjson = r.json()

        total = rjson['total_count']
        slist = rjson['sent_list']

        for msg in slist:
            if msg['type'] != 9:
                continue

            masssend_time = msg['sent_info']['time']

            for m in msg['appmsg_info']:

                if m['is_deleted']:
                    continue
                if 'comment_id' not in m and 'copyright_type' not in m:
                    continue

                ad = {
                    "appmsgid": "{:0>10d}".format(m['appmsgid']),
                    "title": m['title'],
                    "cover_url": m['cover'],
                    "content_url": m['content_url'],
                    "like_num": m['like_num'],
                    "read_num": m['read_num'],
                    "masssend_time": masssend_time,
                }

                for k, v in parse_qsl(urlparse(m['content_url']).query):
                    if k in ("idx", "itemidx"):
                        ad['idx'] = v
                    if k in ("sn", "sign"):
                        ad['sn'] = v

                assert 'idx' in ad and 'sn' in ad

                adlist.append(ad)

        begin += count

    jgz_dump(adlist, ADLIST_JSON)
    client.dump_session()


def test_download_article_content(client, conn):

    adlist = jgz_load(ADLIST_JSON)

    lastid = '9999999999'

    for ad in adlist:
        appmsgid = ad['appmsgid']
        assert appmsgid <= lastid, (appmsgid, lastid)
        lastid = appmsgid

    sql = 'SELECT MAX(`appmsgid`) FROM `article` WHERE LENGTH(`appmsgid`) = 10'

    with conn.cursor() as cur:
        cur.execute(sql)
        max_appmsgid = cur.fetchone()[0].zfill(10)

    adclist = []

    for ad in adlist:

        appmsgid = ad['appmsgid']
        idx = ad['idx']

        if appmsgid <= max_appmsgid:
            break

        print("GET article_content (%s, %s)" % (appmsgid, idx))

        url = ad['content_url']

        r = client.article_content(url)
        tree = etree.HTML(r.content)

        digest = tree.xpath('//head/meta[@name="description"]/@content')

        if len(digest) == 0:
            digest = None
            content = None
        else:
            digest = digest[0]
            content = tree.xpath('//div[@id="js_content"]//text()')
            content = ' '.join(s.strip() for s in content if len(s) > 0 and not s.isspace())

        adclist.append({
            'digest': digest,
            'content': content,
            **ad,
        })

    jgz_dump(adclist, ADCLIST_JSON)


def test_update_database(conn):

    cur = conn.cursor()

    adlist = jgz_load(ADLIST_JSON)
    adclist = jgz_load(ADCLIST_JSON)

    admap = { (ad['appmsgid'], ad['idx']): ad for ad in adlist }

    for ad in adclist:

        appmsgid = ad['appmsgid']
        idx = ad['idx']

        key = (appmsgid, idx)
        admap.pop(key)

        if ad['digest'] is None and ad['content'] is None:
            continue

        appmsgid = appmsgid.lstrip('0')
        idx = int(idx)
        sn = ad['sn']
        title = ad['title']
        digest = ad['digest']
        content = ad['content']
        cover_url = ad['cover_url']
        content_url = ad['content_url']
        like_num = ad['like_num']
        read_num = ad['read_num']
        masssend_time = ad['masssend_time']

        sql = (
            'INSERT INTO `article` '
            '(`appmsgid`,`idx`,`sn`,`title`,`digest`,`content`,`cover_url`,'
            ' `content_url`,`like_num`,`read_num`,`masssend_time`) '
            'VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)'
        )

        data = (appmsgid, idx, sn, title, digest, content, cover_url,
                content_url, like_num, read_num, masssend_time)
        cur.execute(sql, data)

    for ad in admap.values():

        appmsgid = ad['appmsgid'].lstrip('0')
        idx = int(ad['idx'])
        like_num = ad['like_num']
        read_num = ad['read_num']

        sql = (
            'UPDATE `article` '
            'SET `like_num` = %s,'
            '    `read_num` = %s '
            'WHERE `appmsgid` = %s AND `idx` = %s '
        )

        data = (like_num, read_num, appmsgid, idx)
        cur.execute(sql, data)

    cur.close()
    conn.commit()


def test_update_static(client, qclient):

    adclist = jgz_load(ADCLIST_JSON)

    for ad in adclist:

        if ad['digest'] is None and ad['content'] is None:
            continue

        url = ad['cover_url']
        r = client.article_cover(url)

        buf = BytesIO(r.content)
        im = Image.open(buf).convert('RGB')

        sim = compress_sm_cover(im)
        bim = compress_bg_cover(im)

        kwargs = {
            'quality': 60
        }

        osz = get_image_size(im, 'jpeg', **kwargs)
        ssz = get_image_size(sim, 'jpeg', **kwargs)
        bsz = get_image_size(bim, 'jpeg', **kwargs)

        print(osz, ssz, bsz)

        key = "%s%s" % (ad['appmsgid'], ad['idx'])
        assert len(key) == 11

        im.save(os.path.join(IMAGE_CACHE_DIR, "%s.im.jpeg" % key), **kwargs)
        sim.save(os.path.join(IMAGE_CACHE_DIR, "%s.sim.jpeg" % key), **kwargs)
        bim.save(os.path.join(IMAGE_CACHE_DIR, "%s.bim.jpeg" % key), **kwargs)

        smbuf = BytesIO()
        sim.save(smbuf, format='jpeg', quality=50)
        smdata = smbuf.getvalue()
        smkey = "pkuyouth/sm_cover/%s.jpeg" % key

        bgbuf = BytesIO()
        bim.save(bgbuf, format='jpeg', quality=60)
        bgdata = bgbuf.getvalue()
        bgkey = "pkuyouth/bg_cover/%s.jpeg" % key

        qclient.put_data(smdata, smkey)
        qclient.put_data(bgdata, bgkey)


def main():

    config = UpdaterConfig()

    client = MPWXClient(
        username=config.mpwx_username,
        password=config.mpwx_password,
    )

    qclient = QiniuClient(
        access_key=config.qiniu_access_key,
        secret_key=config.qiniu_secret_key,
        bucket=config.qiniu_bucket,
    )

    conn = pymysql.connect(
        host=config.mysql_host,
        port=config.mysql_port,
        user=config.mysql_user,
        password=config.mysql_password,
        db=config.mysql_database,
        charset=config.mysql_charset,
    )

    try:
        # test_login(client)
        # test_download_articles_list(client)
        # test_download_article_content(client, conn)
        # test_update_database(conn)
        # test_update_static(client, qclient)
        pass

    except:
        conn.rollback()
        raise

    finally:
        conn.close()
        client.close()


if __name__ == "__main__":
    # test_download_static()
    main()

