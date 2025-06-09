#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author : aidenmo
# @Email : aidenmo@tencent.com
# @Time : 2025/5/30 12:34
import json
from pathlib import Path
from urllib.parse import urlencode, quote, urlparse

import requests
from adbutils import AdbDevice
from loguru import logger


class AdbDeviceProxy:
    def __init__(self, device: AdbDevice):
        self._device = device
        self.adb_target_dir = "/data/local/tmp"
        self.adb_path = self._push_yadb()

    def _push_yadb(self):
        if not getattr(self._device, 'yadb', None):
            adb_bin_path = Path(__file__).parent / 'bin' / 'yadb'
            logger.info('push yadb to device...')
            self._device.sync.push(src=adb_bin_path, dst=self.adb_target_dir)
            setattr(self._device, 'yadb', f'{self.adb_target_dir}/yadb')
        return getattr(self._device, 'yadb')

    def execute_command(self, *args: str):
        self._device.shell([
            'app_process',
            f'-Djava.class.path={self.adb_path}',
            f'{self.adb_target_dir}',
            'com.ysbing.yadb.Main',
            *args
        ])

    def input_text(self, text: str):
        self.execute_command('-keyboard', text)


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


# def get_client_url_schema(url, platform):
#     """获取客户端打开指定 url schema 地址"""
#     if platform == PageTypeEnum.QY:
#         params = {'p': json.dumps({'url': url})}
#         return f'qqmusic://qq.com/ui/openUrl?{urlencode(params, quote_via=quote)}'
#     elif platform == PageTypeEnum.KG:
#         params = {"cmd": "303", "jsonStr": {"title": "", "url": f"{url}"}, "type": 9, "action": 0}
#         return f'kugou://start.weixin?{quote(json.dumps(params))}'
#     elif platform == PageTypeEnum.KW:
#         params = {'t': 27, 'u': url}
#         return f'kwapp://open?{quote(urlencode(params, quote_via=quote))}'
#     elif platform == PageTypeEnum.BD:
#         params = {'t': 27, 'u': url}
#         return f'kwapp://open?{quote(urlencode(params, quote_via=quote))}'
#     elif platform == PageTypeEnum.MP:
#         return get_wx_schema(url)
#     else:
#         return url
