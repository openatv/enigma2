from __future__ import print_function
from future import standard_library
standard_library.install_aliases()
import re, os, urllib.request, urllib.error, urllib.parse, sys


def DownloadSetting(url):
    list = []
    try:
        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'VAS')
        response = urllib.request.urlopen(req)
        link = response.read()
        response.close()
        xx = re.compile('<td><a href="(.+?)">(.+?)</a></td>.*?<td>(.+?)</td>', re.DOTALL).findall(link)
        for link, name, date in xx:
            print(link, name, date)
            prelink = ''
            if not link.startswith("http://"):
                prelink = url.replace('asd.php','')
            list.append((date, name, prelink + link))

    except:
        print("ERROR DownloadSetting %s" %(url))

    return list

def ConverDate(data):
    year = data[:2]
    month = data[-4:][:2]
    day = data[-2:]
    return day + '-' + month + '-20' + year

def ConverDateBack(data):
    year = data[-2:]
    month = data[-7:][:2]
    day = data[:2]
    return year + month + day