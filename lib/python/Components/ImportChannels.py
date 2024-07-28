from json import loads
from os.path import basename, dirname, join
from requests import get, exceptions
from shutil import move, rmtree
from tarfile import TarError, TarFile
from tempfile import mkdtemp
# from traceback import print_exc
from twisted.internet.reactor import callInThread

from Components.config import config
from Screens.MessageBox import MessageBox
from Tools.Notifications import AddNotificationWithID

THREAD_STOPPED = True


class ImportChannels:
	IMPORT_FILE = "importchannels"

	def __init__(self):
		if config.usage.remote_fallback_enabled.value and config.usage.remote_fallback_import.value and config.usage.remote_fallback.value and THREAD_STOPPED:
			if config.usage.remote_fallback_enabled.value and config.usage.remote_fallback_import.value and config.usage.remote_fallback_import_url.value != "same" and config.usage.remote_fallback_import_url.value:
				self.url = config.usage.remote_fallback_import_url.value.rsplit(":", 1)[0]
			else:
				self.url = config.usage.remote_fallback.value.rsplit(":", 1)[0]
			if config.usage.remote_fallback_openwebif_customize.value:
				self.url = f"{self.url}:{config.usage.remote_fallback_openwebif_port.value}"
			callInThread(self.getRemoteData)

	def getRemoteData(self):
		def getAPI(url, timeout=5):
			result = None
			userId = config.usage.remote_fallback_openwebif_userid.value
			password = config.usage.remote_fallback_openwebif_password.value
			auth = (userId, password) if userId and password else None
			try:
				response = get(url, headers={}, auth=auth, timeout=(3.05, timeout), verify=False)
				response.raise_for_status()
				result = response.content
			except exceptions.RequestException as err:
				print(f"[ImportChannels] getAPI Error: URL='{url}' {err}!")
			except Exception as err:
				print(f"[ImportChannels] getAPI Error: {err}!")
				# print_exc()
			return result

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
			rmtree(tmpDir, True)
			if SuccessFlag:
				AddNotificationWithID("ChannelsImportOK", MessageBox, _("%s imported from fallback tuner"), type=MessageBox.TYPE_INFO, timeout=5)
			else:
				AddNotificationWithID("ChannelsImportNOK", MessageBox, _("Import from fallback tuner failed, %s") % message, type=MessageBox.TYPE_ERROR, timeout=5)

		global THREAD_STOPPED
		THREAD_STOPPED = False
		remoteFallbackImport = config.usage.remote_fallback_import.value
		#
		settings = {}
		url = config.usage.remote_fallback_dvb_t.value
		url = url[:url.rfind(":")] if url else self.url
		response = getAPI(f"{url}/api/settings")
		if response:
			response = loads(response.decode("UTF-8"))
			if response.get("result"):
				settings = {response["settings"][x][0]: response["settings"][x][1] for x in range(len(response["settings"]))}
		#
		fallbackSetting = getFallbackSettingsValue(settings, ".terrestrial")
		if "Australia" in fallbackSetting:
			config.usage.remote_fallback_dvbt_region.value = "fallback DVB-T/T2 Australia"
		elif "Europe" in fallbackSetting:
			config.usage.remote_fallback_dvbt_region.value = "fallback DVB-T/T2 Europe"
		#
		tmpDir = mkdtemp(prefix="FallbackReceiver_")
		if "epg" in remoteFallbackImport:
			print("[ImportChannels] Writing 'epg.dat' file on server.")
			try:
				response = getAPI(f"{self.url}/api/saveepg", timeout=30)
				if response:
					success = loads(response)
					if success and not success.get("result", False):
						importChannelsDone(False, _("Error when writing 'epg.dat' on the fallback receiver"))
			except Exception as err:
				print(f"[ImportChannels] Error: Unable to save server 'epg.dat'!  ({err})")
				importChannelsDone(False, _("Exception Error when writing /etc/enigma2/epg.dat on the fallback receiver"))
				return
			print("[ImportChannels] Fetching EPG location.")
			epgLocation = None
			try:
				epgDataFile = getFallbackSettingsValue(settings, "config.misc.epgcache_filename") or "/etc/enigma2/epg.dat"
				files = []
				try:
					response = getAPI(f"{self.url}/file?dir={dirname(epgDataFile)}")
					if response:
						files = [file for file in loads(response)["files"] if basename(file).startswith(basename(epgDataFile))]
				except Exception:
					response = getAPI(f"{self.url}/file?dir=/")
					if response:
						files = [file for file in loads(response)["files"] if basename(file).startswith("epg.dat")]
				epgLocation = files[0] if files else None
			except Exception as err:
				print(f"[ImportChannels] Error: Unable to fetch remote directory list!  ({err})")
				importChannelsDone(False, _("Error while retrieving location of 'epg.dat' on the fallback receiver"))
				return
			if epgLocation:
				print("[ImportChannels] Copy EPG file.")
				try:
					response = getAPI(f"{self.url}/file?file={epgLocation}")
					if response:
						open(join(tmpDir, "epg.dat"), "wb").write(response)
				except Exception as err:
					print(f"[ImportChannels] Error: Unable to fetch remote 'epg.dat' file!  ({err})")
					importChannelsDone(False, _("Error while retrieving epg.dat from the fallback receiver"))
					return
				try:
					move(join(tmpDir, "epg.dat"), config.misc.epgcache_filename.value)
				except Exception:
					try:
						move(join(tmpDir, "epg.dat"), "/epg.dat")
					except OSError as err:
						print(f"[ImportChannels] Error: Unable to move 'epg.dat' file!  ({err})")
						importChannelsDone(False, _("Error while moving 'epg.dat' to its destination"))
						return
				print("[ImportChannels] EPG files successfully overwritten on local receiver.")
			else:
				importChannelsDone(False, _("No 'epg.dat' file found on the fallback receiver"))
		if "channels" in remoteFallbackImport:
			print("[ImportChannels] Creating channel-files (tar) on server.")
			cmd = f"{self.url}/bouqueteditor/api/backup?Filename={self.IMPORT_FILE}"  # Create tar-file on server.
			success = getAPI(cmd)
			if success and loads(success).get("Result", False):  # Successfully?
				cmd = f"{self.url}/file?dir=/tmp"
				response = getAPI(cmd)
				if response:
					fileList = loads(response).get("files", [])
					fileName = f"/tmp/{self.IMPORT_FILE}.tar"
					if fileName in fileList:
						print("[ImportChannels] Fetching channel-files (tar) from server.")
						cmd = f"{self.url}/file?file={fileName}"  # Load tar-file from server.
						response = getAPI(cmd)
						if response:
							print("[ImportChannels] Copy and extract channel-files (tar) on local receiver.")
							saveFile = join(tmpDir, f"{self.IMPORT_FILE}.tar")
							open(saveFile, "wb").write(response)  # Save tar-file to local receiver.
							extractList = []
							try:
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
							except TarError as err:
								print(f"[ImportChannels] Error: Unable to access/process tar file '{saveFile}'!  ({err})")
								return
							print("[ImportChannels] Overwrite channel-files on local receiver.")
							try:
								for fullName in extractList:
									move(join(tmpDir, fullName), join("/", fullName))  # Move (overwrite) existing files in original path.
							except Exception as err:
								print(f"[ImportChannels] Error: Unable to overwrite channel-files on local receiver!  ({err})")
								return
							print("[ImportChannels] Channel-files successfully overwritten on local receiver.")
		importChannelsDone(True, {
			"channels": _("Channels"),
			"epg": _("EPG"),
			"channels_epg": _("Channels and EPG")
		}[remoteFallbackImport])
		THREAD_STOPPED = True
