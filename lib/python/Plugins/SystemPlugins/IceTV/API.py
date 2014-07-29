'''
Copyright (C) 2014 Peter Urbanec
All Right Reserved
License: Proprietary / Commercial - contact enigma.licensing (at) urbanec.net
'''

import requests
import json

from fcntl import ioctl
from struct import pack
from socket import socket, AF_INET, SOCK_DGRAM
from . import config

_version_string = "20140728"
_server = "http://api.dev.icetv.com.au"
_device_type_id = 22


def get_mac_address(ifname):
    result = "00:00:00:00:00:00"
    sock = socket(AF_INET, SOCK_DGRAM)
    # noinspection PyBroadException
    try:
        iface = pack('256s', ifname[:15])
        info = ioctl(sock.fileno(), 0x8927, iface)
        result = ''.join(['%02x:' % ord(char) for char in info[18:24]])[:-1].upper()
    except:
        pass
    sock.close()
    return result

def have_credentials():
    return bool(config.plugins.icetv.member.token.value)

def get_credentials():
    return {
            "email_address": config.plugins.icetv.member.email_address.value,
            "token": config.plugins.icetv.member.token.value,
    }

def clear_credentials():
    config.plugins.icetv.member.token.value = ""
    config.plugins.icetv.member.token.save()

class Request(object):
    def __init__(self, resource):
        super(Request, self).__init__()
        self.params = {
            "api_key": "9019fa88-bd0c-4b1b-94ac-6761aa6a664f",
            "application_version": _version_string,
        }
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "IceT3",
        }
        self.url = _server + resource
        self.data = {
            "device": {
                "uid": get_mac_address('eth0'),
                "label": config.plugins.icetv.device.label.value,
                "type_id": config.plugins.icetv.device.type_id.value,
            }
        }
        self.response = None

    def send(self, method):
        data = json.dumps(self.data)
        r = requests.request(method, self.url, params=self.params, headers=self.headers, data=data, verify=False)
        self.response = r
        if r.status_code == 401:
            clear_credentials()
        r.raise_for_status()
        return r


class AuthRequest(Request):
    def __init__(self, resource):
        super(AuthRequest, self).__init__(resource)
        self.params.update(get_credentials())


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


class Login(Request):
    def __init__(self, email, password, region=None):
        super(Login, self).__init__("/login")
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
        for key in ("email_address", "token", "id", "region_id"):
            config.plugins.icetv.member[key].value = result["member"][key]
        for key in ("id", "label", "type_id"):
            config.plugins.icetv.device[key].value = result["device"][key]
        config.plugins.icetv.save()
        return r


class Logout(AuthRequest):
    def __init__(self):
        super(Logout, self).__init__("/logout")

    def delete(self):
        return self.send("delete")

    def send(self, method):
        r = super(Logout, self).send(method)
        clear_credentials()
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
