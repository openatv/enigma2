#	-*-	coding:	utf-8	-*-

from enigma import gFont, addFont, eTimer, eConsoleAppContainer, ePicLoad, loadPNG, getDesktop, eServiceReference, iPlayableService, eListboxPythonMultiContent, RT_HALIGN_LEFT, RT_HALIGN_RIGHT, RT_HALIGN_CENTER, RT_VALIGN_CENTER, eListbox, gPixmapPtr, getPrevAsciiCode

from Plugins.Plugin import PluginDescriptor

from twisted.internet import reactor, defer
from twisted.web.client import downloadPage, getPage, error

from Components.ActionMap import NumberActionMap, ActionMap
from Components.AVSwitch import AVSwitch
from Components.Button import Button
from Components.config import config, ConfigInteger, ConfigSelection, getConfigListEntry, ConfigText, ConfigDirectory, ConfigYesNo, configfile, ConfigSelection, ConfigSubsection, ConfigPIN, NoSave, ConfigNothing
from Components.ConfigList import ConfigListScreen
from Components.FileList import FileList, FileEntryComponent
from Components.GUIComponent import GUIComponent
from Components.Label import Label
from Components.Language import language
from Components.MenuList import MenuList
from Components.MultiContent import MultiContentEntryText, MultiContentEntryPixmap, MultiContentEntryPixmapAlphaTest
from Components.Pixmap import Pixmap, MovingPixmap
from Components.PluginList import PluginEntryComponent, PluginList
from Components.ScrollLabel import ScrollLabel
from Components.ServiceEventTracker import ServiceEventTracker, InfoBarBase
from Components.Sources.Boolean import Boolean
from Components.Sources.StaticText import StaticText

from Screens.ChoiceBox import ChoiceBox
from Screens.InfoBar import MoviePlayer, InfoBar
from Screens.InfoBarGenerics import InfoBarSeek, InfoBarNotifications
from Screens.InputBox import PinInput
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from Screens.Standby import TryQuitMainloop
from Screens.VirtualKeyBoard import VirtualKeyBoard

from Tools.Directories import fileExists, resolveFilename, SCOPE_PLUGINS, SCOPE_CURRENT_SKIN, createDir
from Tools.LoadPixmap import LoadPixmap

import re, urllib, urllib2, os, cookielib, time, socket, sha, shutil, base64, datetime, math, hashlib, random, json, md5, string, xml.etree.cElementTree, bz2
from urllib2 import Request, URLError, urlopen as urlopen2
from socket import gaierror, error
from urllib import quote, unquote_plus, unquote, urlencode
from httplib import HTTPConnection, CannotSendRequest, BadStatusLine, HTTPException
from base64 import b64decode
from binascii import unhexlify
from urlparse import parse_qs
from time import *
from bz2 import BZ2File

# MediaPortal Imports
from debuglog import printlog as printl
import mp_globals
from simpleplayer import SimplePlayer
from coverhelper import CoverHelper
from mp_globals import std_headers

def registerFont(file, name, scale, replacement):
		try:
				addFont(file, name, scale, replacement)
		except Exception, ex: #probably just openpli
				addFont(file, name, scale, replacement, 0)

def decodeHtml(text):
	text = text.replace('&auml;','ä')
	text = text.replace('\u00e4','ä')
	text = text.replace('&#228;','ä')

	text = text.replace('&Auml;','Ä')
	text = text.replace('\u00c4','Ä')
	text = text.replace('&#196;','Ä')

	text = text.replace('&ouml;','ö')
	text = text.replace('\u00f6','ö')
	text = text.replace('&#246;','ö')

	text = text.replace('&ouml;','Ö')
	text = text.replace('&Ouml;','Ö')
	text = text.replace('\u00d6','Ö')
	text = text.replace('&#214;','Ö')

	text = text.replace('&uuml;','ü')
	text = text.replace('\u00fc','ü')
	text = text.replace('&#252;','ü')

	text = text.replace('&Uuml;','Ü')
	text = text.replace('\u00dc','Ü')
	text = text.replace('&#220;','Ü')

	text = text.replace('&szlig;','ß')
	text = text.replace('\u00df','ß')
	text = text.replace('&#223;','ß')

	text = text.replace('&amp;','&')
	text = text.replace('&quot;','\"')
	text = text.replace('&gt;','>')
	text = text.replace('&apos;',"'")
	text = text.replace('&acute;','\'')
	text = text.replace('&ndash;','-')
	text = text.replace('&bdquo;','"')
	text = text.replace('&rdquo;','"')
	text = text.replace('&ldquo;','"')
	text = text.replace('&lsquo;','\'')
	text = text.replace('&rsquo;','\'')
	text = text.replace('&#034;','\'')
	text = text.replace('&#038;','&')
	text = text.replace('&#039;','\'')
	text = text.replace('&#39;','\'')
	text = text.replace('&#160;',' ')
	text = text.replace('\u00a0',' ')
	text = text.replace('\u00b4','\'')
	text = text.replace('&#174;','')
	text = text.replace('&#225;','a')
	text = text.replace('&#233;','e')
	text = text.replace('&#243;','o')
	text = text.replace('&#8211;',"-")
	text = text.replace('\u2013',"-")
	text = text.replace('&#8216;',"'")
	text = text.replace('&#8217;',"'")
	text = text.replace('&#8220;',"'")
	text = text.replace('&#8221;','"')
	text = text.replace('&#8222;',',')
	text = text.replace('\u201e','\"')
	text = text.replace('\u201c','\"')
	text = text.replace('\u201d','\'')
	text = text.replace('\u2019s','\'')
	text = text.replace('\u00e0','à')
	text = text.replace('\u00e7','ç')
	text = text.replace('\u00e9','é')

	text = text.replace('&#xC4;','Ä')
	text = text.replace('&#xD6;','Ö')
	text = text.replace('&#xDC;','Ü')
	text = text.replace('&#xE4;','ä')
	text = text.replace('&#xF6;','ö')
	text = text.replace('&#xFC;','ü')
	text = text.replace('&#xDF;','ß')
	text = text.replace('&#xE9;','é')
	text = text.replace('&#xB7;','·')
	text = text.replace("&#x27;","'")
	text = text.replace("&#x26;","&")
	text = text.replace("&#xFB;","û")
	text = text.replace("&#xF8;","ø")
	text = text.replace("&#x21;","!")
	text = text.replace("&#x3f;","?")

	text = text.replace('&#8230;','...')
	text = text.replace('\u2026','...')
	text = text.replace('&hellip;','...')

	text = text.replace('&#8234;','')
	return text

def iso8859_Decode(txt):
	txt = txt.replace('\xe4','ä').replace('\xf6','ö').replace('\xfc','ü').replace('\xdf','ß')
	txt = txt.replace('\xc4','Ä').replace('\xd6','Ö').replace('\xdc','Ü')
	#txt.decode('iso-8859-1').encode('utf-8')
	return txt

def decodeHtml2(txt):
	txt = iso8859_Decode(txt)
	txt = decodeHtml(txt).strip()
	return txt

def stripAllTags(html):
	cleanr =re.compile('<.*?>')
	cleantext = re.sub(cleanr,'', html)
	return cleantext

def make_closing(base, **attrs):
    """
    Needed for BZ2File with Python (2.6), which otherwise raise "AttributeError: BZ2File instance has no attribute '__exit__'".
    """
    if not hasattr(base, '__enter__'):
        attrs['__enter__'] = lambda self: self
    if not hasattr(base, '__exit__'):
        attrs['__exit__'] = lambda self, type, value, traceback: self.close()
    return type('Closing' + base.__name__, (base, object), attrs)