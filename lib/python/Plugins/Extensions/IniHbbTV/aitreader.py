# -*- coding: utf-8 -*-
from subprocess import Popen, PIPE
import os, xml.dom.minidom, re

DUMPBIN = "/usr/lib/enigma2/python/Plugins/Extensions/IniHbbTV/dumpait"
class eAITSectionReader:
	def __init__(self, demux, pmtid, sid):
		self.mAppList  = []
		self.mDocument = None
		self.mCommand  = "%s --demux=%s --pmtid=%x --serviceid=%x"%(DUMPBIN, demux, pmtid, sid)

	def __text(self, nodelist):
		rc = []
		for node in nodelist:
			if node.nodeType == node.TEXT_NODE:
				rc.append(node.data)
		return ''.join(rc)

	def __item(self, application, name):
		for item in application.getElementsByTagName(name):
			return self.__text(item.childNodes)
		return None

	def __application(self, application):
		item = {}
		item["name"]    = str(self.__item(application, "name"))
		item["url"]     = str(self.__item(application, "url"))
		item["control"] = int(self.__item(application, "control"))
		item["orgid"]   = int(self.__item(application, "orgid"))
		item["appid"]   = int(self.__item(application, "appid"))
		item["profile"] = int(self.__item(application, "profile"))
		#print item
		return item

	def doParseApplications(self):
		l = []
		for application in self.mDocument.getElementsByTagName("application"):
			item = self.__application(application)
			l.append(item)
		self.mAppList = l

	def getApplicationList(self):
		return self.mAppList

	def doOpen(self):
		p1 = Popen(self.mCommand, shell=True, stdout=PIPE)
		document = p1.communicate()[0]

		# strip all none printable charators from data grabed from stream.
		control_chars = ''.join(map(unichr, range(0,32) + range(127,160)))
		control_char_re = re.compile('[%s]' % re.escape(control_chars))
		document = control_char_re.sub('', document)

		if len(document) == 0:
			return False
		self.mDocument = xml.dom.minidom.parseString(document.encode("utf-8"))
		return True

	def doDump(self):
		for x in self.getApplicationList():
			print "Name  :", x["name"]
			print "URL   :", x["url"]
			print "OrgID :", x["orgid"]
			print "AppID :", x["appid"]
			print "Control Code :", x["control"]
			print "Profile Code :", x["profile"]
			print ""

def unit_test(demux, pmtid, sid):
	reader = eAITSectionReader(demux, pmtid, sid)
	if reader.doOpen():
		reader.doParseApplications()
		reader.doDump()
	else:	print "no data!!"

#unit_test('0', 0x17d4, 0x2b66)

