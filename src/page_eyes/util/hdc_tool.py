#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author : aidenmo
# @Email : aidenmo@tencent.com
# @Time : 2026/2/11 11:32
import re
import tempfile
from dataclasses import dataclass
from typing import Iterator, List, NamedTuple, Optional

from PIL import Image
from hdcutils import HDCClient, HDCDevice


class HdcError(Exception):
    """ hdc error """


@dataclass
class HdcDeviceInfo:
    connect_key: str
    connect_type: str
    state: str


class WindowSize(NamedTuple):
    width: int
    height: int


class HdcDevice(HDCDevice):
    def window_size(self) -> WindowSize:
        output, _ = self.hidumper.cmd(['-s', 'RenderService', '-a', 'screen'])
        o = re.search(r"render resolution=(\d+)x(\d+)", output)
        if o:
            w, h = o.group(1), o.group(2)
            return WindowSize(int(w), int(h))
        m = re.search(r"physical resolution=(\d+)x(\d+)", output)
        if m:
            w, h = m.group(1), m.group(2)
            return WindowSize(int(w), int(h))
        raise HdcError("resolution size output unexpected", output)

    def screenshot(self, display_id: Optional[int] = 0) -> Image.Image:
        remote_path = '/data/local/tmp/screenshot.jpeg'
        out, _ = self.shell(['snapshot_display', '-i', str(display_id), '-f', remote_path])
        if 'successfully' in out:
            with tempfile.TemporaryDirectory() as tmpdir:
                self.file_recv(remote=remote_path, local=tmpdir)
                return Image.open(f'{tmpdir}/screenshot.jpeg')
        raise HdcError("snapshot_display failed", out)

    def click(self, x: float | int, y: float | int, display_id: Optional[int] = None) -> None:
        out, _ = self.uitest.click(x, y)
        if 'No Error' in out:
            return
        raise HdcError("uitest click failed", out)

    def swipe(self, sx, sy, ex, ey, duration: float = 1.0) -> None:
        """
        <from_x> <from_y> <to_x> <to_y> [velocity] [stepLength]   velocity ranges from 200 to 40000, default 600
        velocity small, swipe slower
        """
        out, _ = self.uitest.swipe(sx, sy, ex, ey, int(duration * -7000 + 15000))
        if 'No Error' in out:
            return
        raise HdcError("uitest swipe failed", out)

    def get_main_ability(self, bundle_name: str) -> str:
        out, _ = self.bm.cmd(['dump', '-n', bundle_name, '|', 'grep', 'mainAbility'])
        res = re.search(r'"mainAbility": "(\S+)"', out)
        if not res:
            return 'EntryAbility'
        return res.group(1)


class HdcClient(HDCClient):

    def device(self, connect_key: str = None) -> HdcDevice:
        return HdcDevice(connect_key=connect_key, hdc=self)

    def list(self) -> list[HdcDeviceInfo]:
        devices = []
        for target in self.list_targets(detail=True):
            connect_key, connect_type, state, _ = target.split(maxsplit=3)
            devices.append(HdcDeviceInfo(connect_key=connect_key, connect_type=connect_type, state=state))
        return devices

    def iter_device(self) -> Iterator[HdcDevice]:
        """
        Returns:
            iter only HdcDevice with state:Connected
        """
        for info in self.list():
            if info.state == "Connected":
                yield self.device(connect_key=info.connect_key)

    def device_list(self) -> List[HdcDevice]:
        return list(self.iter_device())

    def connect(self, addr: str, timeout: float = 10) -> str:
        out, err = self.cmd(['tconn', addr], timeout=timeout)
        return out

    def disconnect(self, addr: str, timeout: float = 10) -> str:
        out, err = self.cmd(['tconn', addr, '-remove'], timeout=timeout)
        return out
