from os import stat
from time import time
from Components.config import config

ECM_INFO = "/tmp/ecm.info"
EMPTY_ECM_INFO = "", "0", "0", "0"

old_ecm_time = time()
info = {}
ecm = ""
data = EMPTY_ECM_INFO


def getCaidData():
	return (
		("0x100", "0x1ff", "Seca", "S", True),
		("0x500", "0x5ff", "Via", "V", True),
		("0x600", "0x6ff", "Irdeto", "I", True),
		("0x900", "0x9ff", "NDS", "Nd", True),
		("0xb00", "0xbff", "Conax", "Co", True),
		("0xd00", "0xdff", "CryptoW", "Cw", True),
		("0xe00", "0xeff", "PowerVU", "P", False),
		("0x1000", "0x10FF", "Tandberg", "TB", False),
		("0x1700", "0x17ff", "Beta", "B", True),
		("0x1800", "0x18ff", "Nagra", "N", True),
		("0x2600", "0x2600", "Biss", "Bi", False),
		("0x4ae0", "0x4ae1", "Dre", "D", False),
		("0x4aea", "0x4aea", "Cryptoguard", "CG", False),
		("0x4aee", "0x4aee", "BulCrypt", "B1", False),
		("0x5581", "0x5581", "BulCrypt", "B2", False)
	)


class GetEcmInfo:

	def __init__(self):
		self.textValue = ""

	def pollEcmData(self):
		global data, ecm, info, old_ecm_time
		try:
			ecm_time = stat(ECM_INFO).st_mtime
		except OSError:
			ecm_time = old_ecm_time
			data = EMPTY_ECM_INFO
			info = {}
			ecm = ""
		if ecm_time != old_ecm_time:
			oecmi1 = info.get("ecminterval1", "")
			oecmi0 = info.get("ecminterval0", "")
			info = {}
			info["ecminterval2"] = oecmi1
			info["ecminterval1"] = oecmi0
			old_ecm_time = ecm_time
			try:
				ecm = open(ECM_INFO).readlines()
			except OSError:
				ecm = ""
			for line in ecm:
				d = line.split(":", 1)
				if len(d) > 1:
					info[d[0].strip()] = d[1].strip()
			if info and info.get("from") and config.softcam.hideServerName.value:
				info["from"] = "".join(["\u2022"] * len(info.get("from")))
			data = self.getText()
			return True
		else:
			info["ecminterval0"] = int(time() - ecm_time + 0.5)

	def getEcm(self):
		return (self.pollEcmData(), ecm)

	def getEcmData(self):
		self.pollEcmData()
		return data

	def getInfo(self, member, ifempty=""):
		self.pollEcmData()
		return str(info.get(member, ifempty))

	def getText(self):
		global ecm
		try:
			using = info.get("using", "")  # Info is a dictionary.
			if using:
				# CCcam.
				if using == "fta":
					self.textValue = _("FTA")
				elif using == "emu":
					self.textValue = f"EMU ({info.get('ecm time', '?')}s)"
				else:
					hops = info.get("hops", None)
					hops = f" @{hops}" if hops and hops != "0" else ""
					self.textValue = f"{info.get('address', '?')}{hops} ({info.get('ecm time', '?')}s)"
			else:
				decode = info.get("decode", None)
				if decode:
					# Gbox (untested).
					if info["decode"] == "Network":
						cardid = f"id:{info.get('prov', '')}"
						try:
							share = open("/tmp/share.info").readlines()
							for line in share:
								if cardid in line:
									self.textValue = line.strip()
									break
							else:
								self.textValue = cardid
						except Exception:
							self.textValue = decode
					else:
						self.textValue = decode
					if ecm[1].startswith("SysID"):
						info["prov"] = ecm[1].strip()[6:]
					if info["response"] and "CaID 0x" in ecm[0] and "pid 0x" in ecm[0]:
						self.textValue += f" (0.{info['response']}s)"
						info["caid"] = ecm[0][ecm[0].find("CaID 0x") + 7:ecm[0].find(",")]
						info["pid"] = ecm[0][ecm[0].find("pid 0x") + 6:ecm[0].find(" =")]
						info["provid"] = info.get("prov", "0")[:4]
				else:
					source = info.get("source", None)
					if source:
						# Wicardd - type 2 / mgcamd.
						caid = info.get("caid", None)
						if caid:
							info["caid"] = info["caid"][2:]
							info["pid"] = info["pid"][2:]
						info["provid"] = info["prov"][2:]
						timeString = ""
						for line in ecm:
							if "msec" in line:
								line = line.split(" ")
								if line[0]:
									timeString = f" ({float(line[0]) / 1000.0}s)"
									continue
						self.textValue = f"{source}{timeString}"
					else:
						reader = info.get("reader", "")
						if reader:
							hops = info.get("hops", None)
							hops = f" @{hops}" if hops and hops != "0" else ""
							self.textValue = f"{reader}{hops} ({info.get('ecm time', '?')}s)"
						else:
							response = info.get("response time", None)
							if response:
								# Wicardd - type 1.
								response = response.split(" ")
								self.textValue = f"{response[4]} ({float(response[0]) / 1000.0}s)"
							else:
								self.textValue = ""
			decCI = info.get("caid", info.get("CAID", "0"))
			provid = info.get("provid", info.get("prov", info.get("Provider", "0")))
			ecmpid = info.get("pid", info.get("ECM PID", "0"))
		except Exception:
			ecm = ""
			self.textValue = ""
			decCI = "0"
			provid = "0"
			ecmpid = "0"
		return self.textValue, decCI, provid, ecmpid
