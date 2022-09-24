from Components.SystemInfo import BoxInfo


class BoxBranding:
	def __init__(self):
		print("[boxbranding] Loading boxbranding emulation.")

	def getBoxInfoData(self, item):
		value = BoxInfo.getItem(item)
		if value is None:
			value = ""
		else:
			# Apparently all the values are returned as text.
			# (Boolean values would be better for processing.)
			if value.lower() in ("false", "no", "off", "disabled"):
				# value = False
				value = "False"
			if value.lower() in ("true", "yes", "on", "enabled"):
				# value = True
				value = "True"
		return value

## VALID

	def getBrandOEM(self):
		return self.getBoxInfoData("brand")

	def getMachineBrand(self):
		return self.getBoxInfoData("displaybrand")

	def getMachineName(self):
		return self.getBoxInfoData("displaymodel")

	def getMachineBuild(self):
		return self.getBoxInfoData("model")

	def getBoxType(self):
		return self.getBoxInfoData("machinebuild")

	def getDisplayType(self):
		return self.getBoxInfoData("displaytype")

	def getImageVersion(self):
		return self.getBoxInfoData("imageversion")

	def getImageBuild(self):
		return self.getBoxInfoData("imagebuild")

	def getImageFolder(self):
		return self.getBoxInfoData("imagedir")

	def getMachineUBINIZE(self):
		return self.getBoxInfoData("ubinize")

	def getMachineMKUBIFS(self):
		return self.getBoxInfoData("mkubifs")

	def getMachineMtdKernel(self):
		return self.getBoxInfoData("mtdkernel")

	def getMachineMtdRoot(self):
		return self.getBoxInfoData("mtdrootfs")

	def getMachineKernelFile(self):
		return self.getBoxInfoData("kernelfile")

	def getMachineRootFile(self):
		return self.getBoxInfoData("rootfile")

	def getImageFileSystem(self):
		return self.getBoxInfoData("imagefs")

	def getImageDistro(self):
		return self.getBoxInfoData("distro")

	def getFeedsUrl(self):
		return self.getBoxInfoData("feedsurl")

	def getHaveAVJACK(self):
		return self.getBoxInfoData("avjack")

	def getHaveCI(self):
		return self.getBoxInfoData("ci")

	def getHaveDVI(self):
		return self.getBoxInfoData("dvi")

	def getHaveHDMI(self):
		return self.getBoxInfoData("hdmi")

	def getHaveHDMIinFHD(self):
		return self.getBoxInfoData("hdmifhdin")

	def getHaveHDMIinHD(self):
		return self.getBoxInfoData("hdmihdin")

	def getHaveRCA(self):
		return self.getBoxInfoData("rca")

	def getHaveSCART(self):
		return self.getBoxInfoData("scart")

	def getHaveSCARTYUV(self):
		return self.getBoxInfoData("scartyuv")

	def getHaveWOL(self):
		return self.getBoxInfoData("wol")

	def getHaveWWOL(self):
		return self.getBoxInfoData("wwol")

	def getHaveYUV(self):
		return self.getBoxInfoData("yuv")

	def getMachineMake(self):
		return self.getBoxInfoData("machinebuild")

	def getOEVersion(self):
		return self.getBoxInfoData("oe")

	def getImageType(self):
		return self.getBoxInfoData("imagetype")

	def getImageDevBuild(self):
		return self.getBoxInfoData("imagedevbuild")

	def getImageArch(self):
		return self.getBoxInfoData("architecture")

	def getDriverDate(self):
		return self.getBoxInfoData("driversdate")


# NOT implemented and not used

	def getMachineProcModel(self):
		return self.getBoxInfoData("")


# NOT in enigma.info and not used

	def getHaveTranscoding2(self):
		return self.getBoxInfoData("")

	def getHaveTranscoding1(self):
		return self.getBoxInfoData("")

	def getHaveMiniTV(self):
		return self.getBoxInfoData("")


boxbranding = BoxBranding()
