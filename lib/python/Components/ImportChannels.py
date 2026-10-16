from base64 import b64encode
from os.path import join
from shutil import move, rmtree
from tarfile import TarError, TarFile
from tempfile import mkdtemp
from urllib.parse import quote
from twisted.internet.defer import inlineCallbacks
from twisted.internet.threads import deferToThread

from Components.config import config
from Screens.MessageBox import MessageBox
from Tools.Downloader import downloadPage, formatError, getJson
from Tools.Notifications import AddNotificationWithID


class ImportChannels:
	IMPORT_FILE = "importchannels"
	running = False

	def __init__(self):
		if config.usage.remote_fallback_enabled.value and config.usage.remote_fallback_import.value and config.usage.remote_fallback.value and not ImportChannels.running:
			if config.usage.remote_fallback_enabled.value and config.usage.remote_fallback_import.value and config.usage.remote_fallback_import_url.value != "same" and config.usage.remote_fallback_import_url.value:
				self.url = config.usage.remote_fallback_import_url.value.rsplit(":", 1)[0]
			else:
				self.url = config.usage.remote_fallback.value.rsplit(":", 1)[0]
			if config.usage.remote_fallback_openwebif_customize.value:
				self.url = f"{self.url}:{config.usage.remote_fallback_openwebif_port.value}"
			userId = config.usage.remote_fallback_openwebif_userid.value
			password = config.usage.remote_fallback_openwebif_password.value
			self.headers = {"Authorization": f"Basic {b64encode(f'{userId}:{password}'.encode()).decode()}"} if userId and password else {}
			ImportChannels.running = True
			self.getRemoteData().addErrback(self.importError)

	def getAPI(self, url, fileName=None, timeout=10):
		def apiError(failure):
			print(f"[ImportChannels] getAPI Error: URL='{url}' {formatError(failure)}!")
			return None if fileName is None else False

		url = quote(url, safe="!#$%&'()*+,/:;=?@[]~")  # Requote like requests did.
		if fileName:
			return downloadPage(url, fileName, headers=self.headers, connectTimeout=3, idleTimeout=timeout, verify=False).addCallbacks(lambda result: True, apiError)
		return getJson(url, headers=self.headers, connectTimeout=3, timeout=timeout, verify=False).addErrback(apiError)

	def importError(self, failure):
		print(f"[ImportChannels] Error: Unexpected error!  ({formatError(failure)})")
		AddNotificationWithID("ChannelsImportNOK", MessageBox, _("Unexpected error while importing from the remote receiver!"), type=MessageBox.TYPE_ERROR, timeout=5)

	@inlineCallbacks
	def getRemoteData(self):
		def getFallbackSettingsValue(settings, settingName):
			result = ""
			if settingName in settings:  # Complete key lookup.
				result = settings[settingName]
			else:
				for setting in settings:  # Partial key lookup.
					if settingName in setting:
						result = settings[setting]
						break
			return result

		def importChannelsDone(SuccessFlag, message):
			if SuccessFlag:
				AddNotificationWithID("ChannelsImportOK", MessageBox, _("%s imported from remote receiver.") % message, type=MessageBox.TYPE_INFO, timeout=5)
			else:
				AddNotificationWithID("ChannelsImportNOK", MessageBox, message, type=MessageBox.TYPE_ERROR, timeout=5)

		def moveEpg():
			try:
				move(join(tmpDir, "epg.dat"), config.misc.epgcache_filename.value)
			except Exception:
				move(join(tmpDir, "epg.dat"), "/epg.dat")

		def extractChannels(saveFile):
			extractList = []
			with TarFile.open(saveFile) as tar:
				for member in tar.getmembers():
					fullName = member.name
					for item in ["lamedb", "blacklist", "whitelist", "alternatives"]:
						if item in fullName.split("/")[-1]:  # Search in plain filename only.
							extractList.append(fullName)
							break
					if fullName.endswith((".tv", ".radio")):
						extractList.append(fullName)
				tar.extractall(path=tmpDir, members=extractList)  # Extract desired files from tar-file.
			return extractList

		def moveChannels(extractList):
			for fullName in extractList:
				move(join(tmpDir, fullName), join("/", fullName))  # Move (overwrite) existing files in original path.

		remoteFallbackImport = config.usage.remote_fallback_import.value
		tmpDir = None
		try:
			tmpDir = mkdtemp(prefix="FallbackReceiver_")
			url = config.usage.remote_fallback_dvb_t.value
			url = url[:url.rfind(":")] if url else self.url
			respDict = yield self.getAPI(f"{url}/api/settings")
			settings = {key: value for key, value in (respDict or {}).get("settings", [])}
			fallbackSetting = getFallbackSettingsValue(settings, ".terrestrial")
			if "Australia" in fallbackSetting:
				config.usage.remote_fallback_dvbt_region.value = "Fallback DVB-T/T2 Australia"
			elif "Europe" in fallbackSetting:
				config.usage.remote_fallback_dvbt_region.value = "Fallback DVB-T/T2 Europe"
			if "epg" in remoteFallbackImport:
				print("[ImportChannels] Writing 'epg.dat' file on server.")
				respDict = yield self.getAPI(f"{self.url}/api/saveepg")
				if not (respDict or {}).get("result", False):
					importChannelsDone(False, _("Error writing 'epg.dat' on the remote receiver!"))
					return
				epgLocation = respDict.get("path", "/etc/enigma2/epg.dat")
				print("[ImportChannels] Fetching EPG location.")
				if not epgLocation:
					importChannelsDone(False, _("No 'epg.dat' file found on the remote receiver!"))
					return
				print("[ImportChannels] Copy EPG file.")
				if not (yield self.getAPI(f"{self.url}/file?file={epgLocation}", fileName=join(tmpDir, "epg.dat"))):
					importChannelsDone(False, _("Error retrieving 'epg.dat' from the remote receiver!"))
					return
				try:
					yield deferToThread(moveEpg)
				except OSError as err:
					print(f"[ImportChannels] Error: Unable to move 'epg.dat' file!  ({err})")
					importChannelsDone(False, _("Error moving 'epg.dat' to its destination!"))
					return
				print("[ImportChannels] EPG files successfully overwritten on local receiver.")
			if "channels" in remoteFallbackImport:
				print("[ImportChannels] Creating channel-files (tar) on server.")
				success = yield self.getAPI(f"{self.url}/bouqueteditor/api/backup?Filename={self.IMPORT_FILE}")  # Create tar-file on server.
				if not (success or {}).get("Result", False):
					importChannelsDone(False, _("Error creating the channel backup on the remote receiver!"))
					return
				response = yield self.getAPI(f"{self.url}/file?dir=/tmp")
				fileName = f"/tmp/{self.IMPORT_FILE}.tar"
				if fileName not in (response or {}).get("files", []):
					importChannelsDone(False, _("No channel backup found on the remote receiver!"))
					return
				print("[ImportChannels] Fetching channel-files (tar) from server.")
				saveFile = join(tmpDir, f"{self.IMPORT_FILE}.tar")
				if not (yield self.getAPI(f"{self.url}/file?file={fileName}", fileName=saveFile)):  # Load tar-file from server.
					importChannelsDone(False, _("Error retrieving the channel backup from the remote receiver!"))
					return
				print("[ImportChannels] Copy and extract channel-files (tar) on local receiver.")
				try:
					extractList = yield deferToThread(extractChannels, saveFile)
				except (TarError, OSError) as err:
					print(f"[ImportChannels] Error: Unable to access/process tar file '{saveFile}'!  ({err})")
					importChannelsDone(False, _("Error extracting the channel backup!"))
					return
				print("[ImportChannels] Overwrite channel-files on local receiver.")
				try:
					yield deferToThread(moveChannels, extractList)
				except Exception as err:
					print(f"[ImportChannels] Error: Unable to overwrite channel-files on local receiver!  ({err})")
					importChannelsDone(False, _("Error overwriting the channel files on the local receiver!"))
					return
				print("[ImportChannels] Channel-files successfully overwritten on local receiver.")
			importChannelsDone(True, {
				"channels": _("Channels"),
				"epg": _("EPG"),
				"channels_epg": _("Channels and EPG")
			}[remoteFallbackImport])
		finally:
			if tmpDir:
				rmtree(tmpDir, True)
			ImportChannels.running = False
