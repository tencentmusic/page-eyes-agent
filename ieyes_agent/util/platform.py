#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author : aidenmo
# @Email : aidenmo@tencent.com
# @Time : 2025/6/9 15:47
import json
from enum import StrEnum
from urllib.parse import urlparse, urlencode, quote

import requests
from loguru import logger


class Platform(StrEnum):
    WEB = "WEB"
    WEB_H5 = "WEB_H5"
    QY = "QY"
    KG = "KG"
    KW = "KW"
    BD = "BD"
    MP = "MP"


def get_wx_schema(url):
    """
    :param url: {tenant}://{envVersion}/{path}, eg. musician://release/pages/home/index
    :return:
    """
    scheme, no_schema_url = url.split(':', 1)
    parse_res = urlparse(no_schema_url, scheme=scheme)

    payload = {
        "tenant": parse_res.scheme,
        "path": parse_res.path,
        "query": parse_res.query,
        "envVersion": parse_res.netloc or "release"
    }
    res = requests.post('https://y.tencentmusic.com/passport/v1/wx/generateUrlScheme', json=payload)
    if res.status_code == 200:
        logger.info(res.text)
        schema = res.json().get('data')
        return schema
    else:
        logger.error(res.text)
        return ''


def get_client_url_schema(url, platform):
    """获取客户端打开指定 url schema 地址"""
    if platform == Platform.QY:
        params = {'p': json.dumps({'url': url})}
        return f'qqmusic://qq.com/ui/openUrl?{urlencode(params, quote_via=quote)}'
    elif platform == Platform.KG:
        params = {"cmd": "303", "jsonStr": {"title": "", "url": f"{url}"}, "type": 9, "action": 0}
        return f'kugou://start.weixin?{quote(json.dumps(params))}'
    elif platform == Platform.KW:
        params = {'t': 27, 'u': url}
        return f'kwapp://open?{quote(urlencode(params, quote_via=quote))}'
    elif platform == Platform.BD:
        params = {'t': 27, 'u': url}
        return f'kwapp://open?{quote(urlencode(params, quote_via=quote))}'
    elif platform == Platform.MP:
        return get_wx_schema(url)
    else:
        return url
