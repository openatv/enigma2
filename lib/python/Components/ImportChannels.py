import os
import re
import shutil
import tempfile
import threading
from base64 import encodebytes
from json import loads
from time import sleep
from urllib.error import URLError
from urllib.parse import quote
from urllib.request import Request, urlopen
from json import loads
from Components.config import config
from Screens.MessageBox import MessageBox
from Tools.Notifications import AddNotificationWithID

supportfiles = ('lamedb', 'blacklist', 'whitelist', 'alternatives.')

e2path = "/etc/enigma2"


class ImportChannels:

	def __init__(self):
		if config.usage.remote_fallback_enabled.value and config.usage.remote_fallback_import.value and config.usage.remote_fallback.value and not "ChannelsImport" in [x.name for x in threading.enumerate()]:
			self.header = None
			if config.usage.remote_fallback_enabled.value and config.usage.remote_fallback_import.value and config.usage.remote_fallback_import_url.value != "same" and config.usage.remote_fallback_import_url.value:
				self.url = config.usage.remote_fallback_import_url.value.rsplit(":", 1)[0]
			else:
				self.url = config.usage.remote_fallback.value.rsplit(":", 1)[0]
			if config.usage.remote_fallback_openwebif_customize.value:
				self.url = "%s:%s" % (self.url, config.usage.remote_fallback_openwebif_port.value)
				if config.usage.remote_fallback_openwebif_userid.value and config.usage.remote_fallback_openwebif_password.value:
					self.header = "Basic %s" % encodebytes(("%s:%s" % (config.usage.remote_fallback_openwebif_userid.value, config.usage.remote_fallback_openwebif_password.value)).encode("UTF-8")).strip().decode()
			self.remote_fallback_import = config.usage.remote_fallback_import.value
			self.thread = threading.Thread(target=self.threaded_function, name="ChannelsImport")
			self.thread.start()

	def getUrl(self, url, timeout=5):
		request = Request(url)
		if self.header:
			request.add_header("Authorization", self.header)
		try:
			result = urlopen(request, timeout=timeout)
		except URLError as e:
			if "[Errno -3]" in str(e.reason):
				print("[Import Channels] Network is not up yet, delay 5 seconds")
				# network not up yet
				sleep(5)
				return self.getUrl(url, timeout)
			print("[Import Channels] URLError ", e)
			raise (e)
		return result

	def getTerrestrialUrl(self):
		url = config.usage.remote_fallback_dvb_t.value
		return url[:url.rfind(":")] if url else self.url

	def getFallbackSettings(self):
		result = self.getUrl("%s/api/settings" % self.getTerrestrialUrl()).read()
		if result:
			result = loads(result.decode('utf-8'))
			if 'result' in result and result['result'] == True:
				return {result['settings'][i][0]: result['settings'][i][1] for i in range(0, len(result['settings']))}
		return {}

	def getFallbackSettingsValue(self, settings, e2settingname):
		# complete key lookup
		if e2settingname in settings:
			return settings[e2settingname]
		# partial key lookup
		for e2setting in settings:
			if e2settingname in e2setting:
				return settings[e2setting]
		return ""

	def getTerrestrialRegion(self, settings):
		description = ""
		descr = self.getFallbackSettingsValue(settings, ".terrestrial")
		if "Europe" in descr:
			description = "fallback DVB-T/T2 Europe"
		if "Australia" in descr:
			description = "fallback DVB-T/T2 Australia"
		config.usage.remote_fallback_dvbt_region.value = description

	"""
	Enumerate all the files that make up the bouquet system, either local or on a remote machine
	"""

	def ImportGetFilelist(self, remote=False, *files):
		result = []
		for file in files:
			# read the contents of the file
			try:
				if remote:
					try:
						content = self.getUrl("%s/file?file=%s/%s" % (self.url, e2path, quote(file))).readlines()
						content = map(lambda l: l.decode('utf-8', 'replace'), content)
					except Exception as e:
						print("[Import Channels] Exception: %s" % str(e))
						continue
				else:
					with open('%s/%s' % (e2path, file), 'r') as f:
						content = f.readlines()
			except Exception as e:
				# for the moment just log and ignore
				print("[Import Channels] %s" % str(e))
				continue

			# check the contents for more bouquet files
			for line in content:
#				print ("[Import Channels] %s" % line)
				# check if it contains another bouquet reference, first tv type then radio type
				r = re.match('#SERVICE 1:7:1:0:0:0:0:0:0:0:FROM BOUQUET "(.*)" ORDER BY bouquet', line) or re.match('#SERVICE 1:7:2:0:0:0:0:0:0:0:FROM BOUQUET "(.*)" ORDER BY bouquet', line)
				if r:
					# recurse
					result.extend(self.ImportGetFilelist(remote, r.group(1)))
			# add add the file itself
			result.append(file)

		# return the file list
		return result

	def threaded_function(self):
		settings = self.getFallbackSettings()
		self.getTerrestrialRegion(settings)
		self.tmp_dir = tempfile.mkdtemp(prefix="ImportChannels_")

		if "epg" in self.remote_fallback_import:
			print("[Import Channels] Writing epg.dat file on server box")
			try:
				result = loads(self.getUrl("%s/api/saveepg" % self.url, timeout=30).read().decode('utf-8'))
				if 'result' not in result and result['result'] == False:
					self.ImportChannelsDone(False, _("Error when writing epg.dat on the fallback receiver"))
			except Exception as e:
				print("[Import Channels] Exception: %s" % str(e))
				self.ImportChannelsDone(False, _("Error when writing epg.dat on the fallback receiver"))
				return
			print("[Import Channels] Get EPG Location")
			try:
				epgdatfile = self.getFallbackSettingsValue(settings, "config.misc.epgcache_filename") or "/media/hdd/epg.dat"
				try:
					files = [file for file in loads(self.getUrl("%s/file?dir=%s" % (self.url, os.path.dirname(epgdatfile))).read())["files"] if os.path.basename(file).startswith(os.path.basename(epgdatfile))]
				except:
					files = [file for file in loads(self.getUrl("%s/file?dir=/" % self.url).read())["files"] if os.path.basename(file).startswith("epg.dat")]
				epg_location = files[0] if files else None
			except Exception as e:
				print("[Import Channels] Exception: %s" % str(e))
				self.ImportChannelsDone(False, _("Error while retrieving location of epg.dat on the fallback receiver"))
				return
			if epg_location:
				print("[Import Channels] Copy EPG file...")
				try:
					open(os.path.join(self.tmp_dir, "epg.dat"), "wb").write(self.getUrl("%s/file?file=%s" % (self.url, epg_location)).read())
				except Exception as e:
					print("[Import Channels] Exception: %s" % str(e))
					self.ImportChannelsDone(False, _("Error while retrieving epg.dat from the fallback receiver"))
					return
				try:
					shutil.move(os.path.join(self.tmp_dir, "epg.dat"), config.misc.epgcache_filename.value)
				except:
					# follow same logic as in epgcache.cpp
					try:
						shutil.move(os.path.join(self.tmp_dir, "epg.dat"), "/epg.dat")
					except Exception as e:
						print("[Import Channels] Exception: %s" % str(e))
						self.ImportChannelsDone(False, _("Error while moving epg.dat to its destination"))
						return
			else:
				self.ImportChannelsDone(False, _("No epg.dat file found on the fallback receiver"))

		if "channels" in self.remote_fallback_import:
			print("[Import Channels] Enumerate remote files")
			files = self.ImportGetFilelist(True, 'bouquets.tv', 'bouquets.radio')

			print("[Import Channels] Enumerate remote support files")
			for file in loads(self.getUrl("%s/file?dir=%s" % (self.url, e2path)).read())["files"]:
				if os.path.basename(file).startswith(supportfiles):
					files.append(file.replace(e2path, ''))

			print("[Import Channels] Fetch remote files")
			for file in files:
#				print("[Import Channels] Downloading %s..." % file)
				try:
					open(os.path.join(self.tmp_dir, os.path.basename(file)), "wb").write(self.getUrl("%s/file?file=%s/%s" % (self.url, e2path, quote(file))).read())
				except Exception as e:
					print("[Import Channels] Exception: %s" % str(e))

			print("[Import Channels] Enumerate local files")
			files = self.ImportGetFilelist(False, 'bouquets.tv', 'bouquets.radio')

			print("[Import Channels] Removing old local files...")
			for file in files:
#				print("- Removing %s..." % file)
				try:
					os.remove(os.path.join(e2path, file))
				except OSError:
					print("[Import Channels] File %s did not exist" % file)

			print("[Import Channels] Updating files...")
			files = [x for x in os.listdir(self.tmp_dir)]
			for file in files:
#				print("- Moving %s..." % file)
				shutil.move(os.path.join(self.tmp_dir, file), os.path.join(e2path, file))

		self.ImportChannelsDone(True, {"channels": _("Channels"), "epg": _("EPG"), "channels_epg": _("Channels and EPG")}[self.remote_fallback_import])

	def ImportChannelsDone(self, flag, message=None):
		shutil.rmtree(self.tmp_dir, True)
		if flag:
			AddNotificationWithID("ChannelsImportOK", MessageBox, _("%s imported from fallback tuner") % message, type=MessageBox.TYPE_INFO, timeout=5)
		else:
			AddNotificationWithID("ChannelsImportNOK", MessageBox, _("Import from fallback tuner failed, %s") % message, type=MessageBox.TYPE_ERROR, timeout=5)
