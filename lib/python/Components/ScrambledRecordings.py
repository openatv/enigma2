from os.path import exists
from time import sleep
from enigma import eServiceCenter, eServiceReference, iServiceInformation

from Tools.Directories import fileReadLines, fileWriteLines


class ScrambledRecordings:
	SCRAMBLE_LIST_FILE = "/etc/enigma2/.scrambled_video_list"

	def __init__(self):
		self.isLocked = 0

	def getServiceRef(self, movie):
		return eServiceReference(f"{"1" if movie.endswith("ts") else "4097"}:0:0:0:0:0:0:0:0:0:{movie}")

	def readList(self, returnLength=False):
		files = []
		lines = fileReadLines(self.SCRAMBLE_LIST_FILE, default=[])
		for line in lines:
			if exists(line) and not exists(f"{line}.del"):
				sref = self.getServiceRef(line)
				if returnLength:
					info = eServiceCenter.getInstance().info(sref)
					files.append((sref, info and info.getLength(sref) or 0))
				else:
					files.append(sref)
		return files

	def writeList(self, append="", overwrite=False):
		result = []
		serviceHandler = eServiceCenter.getInstance()
		if not overwrite:
			lines = fileReadLines(self.SCRAMBLE_LIST_FILE, default=[])
			for line in lines:
				if line and exists(line):
					sref = self.getServiceRef(line)
					info = serviceHandler.info(sref)
					if info.getInfo(sref, iServiceInformation.sIsCrypted) == 1:
						result.append(line)
		if isinstance(append, list):
			result.extend(append)
		elif append != "":
			result.append(append)
		if not fileWriteLines(self.SCRAMBLE_LIST_FILE, result):
			if self.isLocked < 11:
				sleep(.300)
				self.isLocked += 1
				self.writeList(append=append)
			else:
				self.isLocked = 0
