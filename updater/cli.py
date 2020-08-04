#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ---------------------------------------
# Project: PKUYouth Webserver v2
# File: cli.py
# Created Date: 2020-08-03
# Author: Xinghong Zhong
# ---------------------------------------
# Copyright (c) 2020 PKUYouth

import os
import time
from functools import wraps
from io import BytesIO
from PIL import Image
import pymysql
from lxml import etree
from urllib.parse import urlparse, parse_qsl
from .config import UpdaterConfig
from .client import MPWXClient, QiniuClient
from .image import compress_sm_cover, compress_bg_cover, im2bytes
from .utils import jgz_dump, jgz_load
from .const import CACHE_DIR

ADLIST_JSON = os.path.join(CACHE_DIR, "adlist.json.gz")
ADCLIST_JSON = os.path.join(CACHE_DIR, "adclist.json.gz")

def log(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        print("=== %s BEGIN ===" % func.__name__)
        ret = func(*args, **kwargs)
        print("=== %s END ===" % func.__name__)
        return ret
    return wrapper


@log
def task_mpwx_login(client):

    if client.logined:
        print("[MPWX] Use old session")
        return

    r = client.homepage()
    r = client.bizlogin_prelogin()
    r = client.bizlogin_startlogin()
    r = client.bizlogin_validate()
    r = client.loginqrcode_ask()
    r = client.loginqrcode_getqrcode()

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
                print("[MPWX] Wait for sanning QR code (status: %s)" % status)
                current_status = status
        elif status == 4:
            if current_status != 4:
                print("[MPWX] Wait for administrator confirmation (status: %s)" % status)
                current_status = status
        elif status == 1:
            if current_status != 1:
                print("[MPWX] Comfirmed (status: %s)" % status)
                current_status = status
        elif status == 2:
            raise RuntimeError("[MPWX] Your login operation was denied by administrator (status: %s)" % status)
        elif status == 3:
            raise RuntimeError("[MPWX] Your login operation has expired (status: %s)" % status)
        else:
            print(rjson)
            raise RuntimeError("[MPWX] Unknonwn status %s" % status)

        time.sleep(1.5)

    r = client.bizlogin_login()
    client.dump_session()


@log
def task_download_articles_list(client):

    count = 7
    begin = 0
    total = -1

    adlist = []

    while total == -1 or begin <= total:

        print("[MPWX] GET newmasssendpage %d/%d)" % (begin, total))

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


@log
def task_download_article_content(client, conn):

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

        print("[MPWX] GET article_content (%s, %s)" % (appmsgid, idx))

        url = ad['content_url']

        r = client.article_content(url)
        tree = etree.HTML(r.content)

        digest = tree.xpath('//head/meta[@name="description"]/@content')

        if len(digest) == 0:
            print("[MPWX] Abnormal article %s" % url)
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


@log
def task_update_database(conn):

    cur = conn.cursor()

    adlist = jgz_load(ADLIST_JSON)
    adclist = jgz_load(ADCLIST_JSON)

    admap = { (ad['appmsgid'], ad['idx']): ad for ad in adlist }

    print("[MYSQL] Insert new articles")

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

    print("[MYSQL] update old articles")

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


@log
def task_update_static(client, qclient):

    adclist = jgz_load(ADCLIST_JSON)

    for ad in adclist:

        if ad['digest'] is None and ad['content'] is None:
            continue

        appmsgid = ad['appmsgid']
        idx = ad['idx']
        key = "%s%s" % (appmsgid, idx)

        print("[MPWX] update_static (%s, %s)" % (appmsgid, idx))

        url = ad['cover_url']
        r = client.article_cover(url)

        buf = BytesIO(r.content)
        im = Image.open(buf).convert('RGB')

        sim = compress_sm_cover(im)
        bim = compress_bg_cover(im)

        smdata = im2bytes(sim, format='jpeg', quality=50)
        bgdata = im2bytes(bim, format='jpeg', quality=60)

        smkey = "pkuyouth/sm_cover/%s.jpeg" % key
        bgkey = "pkuyouth/bg_cover/%s.jpeg" % key

        print("[QINIU] PUT %s" % smkey)
        qclient.put_data(smdata, smkey)

        print("[QINIU] PUT %s" % bgkey)
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
        task_mpwx_login(client)
        task_download_articles_list(client)
        task_download_article_content(client, conn)
        task_update_database(conn)
        task_update_static(client, qclient)

    except:
        conn.rollback()
        raise

    finally:
        conn.close()
        client.close()


if __name__ == "__main__":
    main()

