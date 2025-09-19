# kate: replace-tabs on; indent-width 4; remove-trailing-spaces all; show-tabs on; newline-at-eof on;
# -*- coding:utf-8 -*-

'''
Copyright (C) 2014 Peter Urbanec
All Right Reserved
License: Proprietary / Commercial - contact enigma.licensing (at) urbanec.net
'''

import requests
import json

from fcntl import ioctl
from struct import pack
from socket import socket, create_connection, AF_INET, SOCK_DGRAM, SHUT_RDWR, error as sockerror
from . import config, saveConfigFile, getIceTVDeviceType
from Components.SystemInfo import BoxInfo

_version_string = "20191127"
_protocol = "http://"
_device_type_id = getIceTVDeviceType()
_debug_level = 0  # 1 = request/reply, 2 = 1+headers, 3 = 2+partial body, 4 = 2+full body

print("[IceTV] server set to", config.plugins.icetv.server.name.value)

iceTVServers = {
    _("Australia"): "api.icetv.com.au",
    # The German IceTV service has closed down
    # _("Germany"): "api.icetv.de",
}


def isServerReachable():
    try:
        sock = create_connection((config.plugins.icetv.server.name.value, 80), 3)
        sock.shutdown(SHUT_RDWR)
        sock.close()
        return True
    except sockerror as ex:
        print("[IceTV] Can not connect to IceTV server:", str(ex))
    return False


def ensure_binary(s, encoding='utf-8', errors='strict'):
    if isinstance(s, bytes):
        return s
    if isinstance(s, str):
        return s.encode(encoding, errors)
    raise TypeError("not expecting type '%s'" % type(s))


def getMacAddress(ifname):
    result = "00:00:00:00:00:00"
    sock = socket(AF_INET, SOCK_DGRAM)
    # noinspection PyBroadException
    try:
        iface = pack('256s', ensure_binary(ifname[:15], "utf-8"))
        info = ioctl(sock.fileno(), 0x8927, iface)
        result = ''.join(['%02x:' % char for char in info[18:24]])[:-1].upper()
        # result = ''.join(['%02x:' % six.byte2int([char]) for char in info[18:24]])[:-1].upper()
    except Exception:
        pass
    sock.close()
    return result


def haveCredentials():
    return bool(config.plugins.icetv.member.token.value)


def getCredentials():
    return {
            "email_address": config.plugins.icetv.member.email_address.value,
            "token": config.plugins.icetv.member.token.value,
    }


def clearCredentials():
    config.plugins.icetv.member.token.value = ""
    config.plugins.icetv.member.token.save()
    saveConfigFile()


def showIdToEventId(show_id):
    # Fit within 16 bits, but avoid 0 and 0xFFF8 - 0xFFFF
    return (int(show_id) % 0xFFF7) + 1


class Request:
    def __init__(self, resource):
        super(Request, self).__init__()
        self.params = {
            "api_key": "9019fa88-bd0c-4b1b-94ac-6761aa6a664f",
            "application_version": _version_string,
        }
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "SystemPlugins.IceTV/%s (%s; %s; %s)" % (_version_string, BoxInfo.getItem("displaybrand"), BoxInfo.getItem("displaymodel"), BoxInfo.getItem("imagebuild")),
        }
        self.url = _protocol + config.plugins.icetv.server.name.value + resource
        self.data = {}
        self.response = None

    def _shorten(self, text):
        if len(text) < 4000:
            return text
        return text[:2000] + "\n...\n" + text[-2000:]

    def send(self, method):
        data = json.dumps(self.data)
        # FIXME verify=False -> verify=True
        r = requests.request(method, self.url, params=self.params, headers=self.headers, data=data, verify=False, timeout=10.0)  #NOSONAR
        err = not r.ok
        if err or _debug_level > 0:
            print("[IceTV]", r.request.method, r.request.url)
        if err or _debug_level > 1:
            print("[IceTV] headers", r.request.headers)
        if err or _debug_level == 3:
            print("[IceTV]", self._shorten(r.request.body))
        elif err or _debug_level > 3:
            print("[IceTV]", r.request.body)
        if err or _debug_level > 0:
            print("[IceTV]", r.status_code, r.reason)
        if err or _debug_level > 1:
            print("[IceTV] headers", r.headers)
        if err or _debug_level == 3:
            print("[IceTV]", self._shorten(r.text))
        elif err or _debug_level > 3:
            print("[IceTV]", r.text)
        self.response = r
        if r.status_code == 401:
            clearCredentials()
        r.raise_for_status()
        return r


class AuthRequest(Request):
    def __init__(self, resource):
        super(AuthRequest, self).__init__(resource)
        self.params.update(getCredentials())


class Regions(Request):
    def __init__(self):
        super(Regions, self).__init__("/regions")

    def get(self):
        return self.send("get")


class Region(Request):
    def __init__(self, region):
        super(Region, self).__init__("/regions/" + str(int(region)))

    def get(self):
        return self.send("get")


class Channels(Request):
    def __init__(self, region=None):
        if region is None:
            super(Channels, self).__init__("/regions/channels")
        else:
            super(Channels, self).__init__("/regions/" + str(int(region)) + "/channels")

    def get(self):
        return self.send("get")


class UserChannels(AuthRequest):
    def __init__(self, region=None):
        if region is None:
            super(UserChannels, self).__init__("/regions/channels")
        else:
            super(UserChannels, self).__init__("/regions/" + str(int(region)) + "/channels")

    def get(self):
        return self.send("get")


class Login(Request):
    def __init__(self, email, password, region=None):
        super(Login, self).__init__("/login")
        self.data["device"] = {
            "uid": getMacAddress('eth0'),
            "label": config.plugins.icetv.device.label.value,
            "type_id": config.plugins.icetv.device.type_id.value,
        }
        self.data["member"] = {
            "email_address": email,
            "password": password,
        }
        if region:
            self.data["member"]["region_id"] = region

    def post(self):
        return self.send("post")

    def put(self):
        return self.send("put")

    def send(self, method):
        r = super(Login, self).send(method)
        result = r.json()
        config.plugins.icetv.member.email_address.value = result["member"]["email_address"]
        config.plugins.icetv.member.token.value = result["member"]["token"]
        config.plugins.icetv.member.id.value = result["member"]["id"]
        config.plugins.icetv.member.region_id.value = result["member"]["region_id"]
        config.plugins.icetv.device.id.value = result["device"]["id"]
        config.plugins.icetv.device.label.value = result["device"]["label"]
        config.plugins.icetv.device.type_id.value = result["device"]["type_id"]
        config.plugins.icetv.save()
        saveConfigFile()
        return r


class Logout(AuthRequest):
    def __init__(self):
        super(Logout, self).__init__("/logout")

    def delete(self):
        return self.send("delete")

    def send(self, method):
        r = super(Logout, self).send(method)
        clearCredentials()
        return r


class Devices(AuthRequest):
    def __init__(self):
        super(Devices, self).__init__("/devices")

    def get(self):
        return self.send("get")

    def post(self):
        return self.send("post")


class Device(AuthRequest):
    def __init__(self, deviceid):
        super(Device, self).__init__("/devices/" + str(int(deviceid)))

    def get(self):
        return self.send("get")

    def put(self):
        return self.send("put")

    def delete(self):
        return self.send("delete")


class DeviceTypes(AuthRequest):
    def __init__(self):
        super(DeviceTypes, self).__init__("/devices/types")

    def get(self):
        return self.send("get")


class DeviceType(AuthRequest):
    def __init__(self, deviceid):
        super(DeviceType, self).__init__("/devices/types/" + str(int(deviceid)))

    def get(self):
        return self.send("get")


class DeviceManufacturers(AuthRequest):
    def __init__(self):
        super(DeviceManufacturers, self).__init__("/devices/manufacturers")

    def get(self):
        return self.send("get")


class DeviceManufacturer(AuthRequest):
    def __init__(self, deviceid):
        super(DeviceManufacturer, self).__init__("/devices/manufacturers/" + str(int(deviceid)))

    def get(self):
        return self.send("get")


class Shows(AuthRequest):
    def __init__(self):
        super(Shows, self).__init__("/shows")

    def get(self):
        return self.send("get")


class Timers(AuthRequest):
    def __init__(self):
        super(Timers, self).__init__("/shows/timers")

    def get(self):
        return self.send("get")

    def post(self):
        return self.send("post")

    def put(self):
        return self.send("put")


class Timer(AuthRequest):
    def __init__(self, timerid):
        super(Timer, self).__init__("/shows/timers/" + str(timerid))

    def get(self):
        return self.send("get")

    def put(self):
        return self.send("put")

    def delete(self):
        return self.send("delete")


class Scans(AuthRequest):
    def __init__(self):
        super(Scans, self).__init__("/scans")

    def post(self):
        return self.send("post")


class Settings(AuthRequest):
    def __init__(self):
        super(Settings, self).__init__("/user/settings")

    def get(self):
        return self.send("get")

    def post(self):
        return self.send("post")


class PvrLogs(AuthRequest):
    def __init__(self):
        super(PvrLogs, self).__init__("/user/pvr_logs")

    def get(self):
        return self.send("get")

    def post(self):
        return self.send("post")
