# This plugin is free software, you are allowed to
# modify it (if you keep the license),
# but you are not allowed to distribute/publish
# it without source code (this version and your modifications).
# This means you also have to distribute
# source code of your modifications.
#
#
#######################################################################
#
# NetSpeedInfo for VU+
# Coded by markusw (c) 2013
# www.vuplus-support.org
#
#######################################################################

from Components.Converter.Converter import Converter
from Components.Converter.Poll import Poll
from Components.Element import cached


class VNetSpeedInfo(Poll, Converter):
	RCL = 0  # LAN receive speed in Mbit/s.
	TML = 1  # LAN transmit speed in Mbit/s.
	RCW = 2  # WLAN receive speed in Mbit/s.
	TMW = 3  # WLAN transmit speed in Mbit/s.
	RCLT = 4  # LAN receive total since the last reboot in MB.
	TMLT = 5  # LAN transmit total since the last reboot in MB.
	RCWT = 6  # WLAN receive total since the last reboot in MB.
	TMWT = 7  # WLAN transmit total since the last reboot in MB.
	RCL_MB = 8  # LAN receive speed in MB/s.
	TML_MB = 9  # LAN transmit speed in MB/s.
	RCW_MB = 10  # WLAN receive speed in MB/s.
	TMW_MB = 11  # WLAN transmit speed in MB/s.
	RC = 12  # LAN or WLAN receive speed in Mbit/s, LAN if both are available.
	TM = 13  # LAN or WLAN transmit speed in Mbit/s, LAN if both are available.
	RCT = 14  # LAN or WLAN receive total since the last reboot in MB, LAN if both are available.
	TMT = 15  # LAN or WLAN transmit total since the last reboot in MB, LAN if both are available.
	RC_MB = 16  # LAN or WLAN receive speed in MB/s, LAN if both are available.
	TM_MB = 17  # LAN or WLAN transmit speed in MB/s, LAN if both are available.
	NET_TYP = 18  # LAN, WLAN or LAN+WLAN.
	ERR_RCL = 19  # LAN receive errors.
	ERR_TML = 20  # LAN transmit errors.
	DRO_RCL = 21  # LAN receive drops.
	DRO_TML = 22  # LAN transmit drops.
	ERR_RCW = 23  # WLAN receive errors.
	ERR_TMW = 24  # WLAN transmit errors.
	DRO_RCW = 25  # WLAN receive drops.
	DRO_TMW = 26  # WLAN transmit drops.

	def __init__(self, tokens, update_interval=1000):
		Poll.__init__(self)
		self.poll_interval = 1000
		self.poll_enabled = True
		self.lanreceivetotal = 0
		self.lanreceivetotalout = 0
		self.lanreceive = 0
		self.lanreceivemb = 0
		self.wlanreceivetotal = 0
		self.wlanreceivetotalout = 0
		self.wlanreceive = 0
		self.wlanreceivemb = 0
		self.lantransmittotal = 0
		self.lantransmittotalout = 0
		self.lantransmit = 0
		self.lantransmitmb = 0
		self.wlantransmittotal = 0
		self.wlantransmittotalout = 0
		self.wlantransmit = 0
		self.wlantransmitmb = 0
		self.receivetotal = 0
		self.receivetotalout = 0
		self.receive = 0
		self.transmittotal = 0
		self.transmittotalout = 0
		self.transmit = 0
		self.receivemb = 0
		self.transmitmb = 0
		self.nettyp = "NONE"
		self.error_lanreceive = 0
		self.drop_lanreceive = 0
		self.error_lantransmite = 0
		self.drop_lantransmite = 0
		self.error_wlanreceive = 0
		self.drop_wlanreceive = 0
		self.error_wlantransmite = 0
		self.drop_wlantransmite = 0
		Converter.__init__(self, tokens)
		self.type = {
			"DRO_RCL": self.DRO_RCL,
			"DRO_RCW": self.DRO_RCW,
			"DRO_TML": self.DRO_TML,
			"DRO_TMW": self.DRO_TMW,
			"ERR_RCL": self.ERR_RCL,
			"ERR_RCW": self.ERR_RCW,
			"ERR_TML": self.ERR_TML,
			"ERR_TMW": self.ERR_TMW,
			"NET_TYP": self.NET_TYP,
			"RC": self.RC,
			"RCL": self.RCL,
			"RCLT": self.RCLT,
			"RCL_MB": self.RCL_MB,
			"RCT": self.RCT,
			"RCW": self.RCW,
			"RCWT": self.RCWT,
			"RCW_MB": self.RCW_MB,
			"RC_MB": self.RC_MB,
			"TM": self.TM,
			"TML": self.TML,
			"TMLT": self.TMLT,
			"TML_MB": self.TML_MB,
			"TMT": self.TMT,
			"TMW": self.TMW,
			"TMWT": self.TMWT,
			"TMW_MB": self.TMW_MB,
			"TM_MB": self.TM_MB
		}.get(tokens, tokens)

	def changed(self, what):
		if what[0] == self.CHANGED_POLL:
			Converter.changed(self, what)

	@cached
	def getText(self):
		return self.updateNetSpeedInfoStatus()

	text = property(getText)

	def updateNetSpeedInfoStatus(self):
		def readCounters(line):  # Receive KB, receive errors, receive drops, transmit KB, transmit errors, transmit drops.
			values = line.split(":", 1)[1].split()
			return int(values[0]) / 1024, int(values[2]), int(values[3]), int(values[8]) / 1024, int(values[10]), int(values[11])

		flagLan = False
		flagWlan = False
		with open("/proc/net/dev") as fd:
			lines = fd.readlines()[2:]  # Skip the two header lines.
		for line in lines:
			if "eth" in line:
				flagLan = True
				receiveTotal, self.error_lanreceive, self.drop_lanreceive, transmitTotal, self.error_lantransmite, self.drop_lantransmite = readCounters(line)
				if self.lanreceivetotal > 0:
					self.lanreceive = (receiveTotal - self.lanreceivetotal) * 8 / 1024
					self.lanreceivemb = (receiveTotal - self.lanreceivetotal) / 1024
				else:
					self.lanreceive = 0
				self.lanreceivetotal = receiveTotal
				self.lanreceivetotalout = receiveTotal / 1024
				if self.lantransmittotal > 0:
					self.lantransmit = (transmitTotal - self.lantransmittotal) * 8 / 1024
					self.lantransmitmb = (transmitTotal - self.lantransmittotal) / 1024
				else:
					self.lantransmit = 0
				self.lantransmittotal = transmitTotal
				self.lantransmittotalout = transmitTotal / 1024
				if (self.lantransmittotal + self.lanreceivetotal) == 0:
					flagLan = False
			elif "ra" in line or "wlan" in line or "wifi" in line:
				flagWlan = True
				receiveTotal, self.error_wlanreceive, self.drop_wlanreceive, transmitTotal, self.error_wlantransmite, self.drop_wlantransmite = readCounters(line)
				if self.wlanreceivetotal > 0:
					self.wlanreceive = (receiveTotal - self.wlanreceivetotal) * 8 / 1024
					self.wlanreceivemb = (receiveTotal - self.wlanreceivetotal) / 1024
				else:
					self.wlanreceive = 0
				self.wlanreceivetotal = receiveTotal
				self.wlanreceivetotalout = receiveTotal / 1024
				if self.wlantransmittotal > 0:
					self.wlantransmit = (transmitTotal - self.wlantransmittotal) * 8 / 1024
					self.wlantransmitmb = (transmitTotal - self.wlantransmittotal) / 1024
				else:
					self.wlantransmit = 0
				self.wlantransmittotal = transmitTotal
				self.wlantransmittotalout = transmitTotal / 1024
		if flagLan:
			self.receive = self.lanreceive
			self.transmit = self.lantransmit
			self.receivetotal = self.lanreceivetotal
			self.transmittotal = self.lantransmittotal
			self.nettyp = "LAN+WLAN" if flagWlan else "LAN"
		elif flagWlan:
			self.receive = self.wlanreceive
			self.transmit = self.wlantransmit
			self.receivetotal = self.wlanreceivetotal
			self.transmittotal = self.wlantransmittotal
			self.nettyp = "WLAN"
		if flagLan or flagWlan:
			self.receivetotalout = self.receivetotal / 1024
			self.transmittotalout = self.transmittotal / 1024
			self.receivemb = self.receive / 8
			self.transmitmb = self.transmit / 8
		value = {
			self.DRO_RCL: self.drop_lanreceive,
			self.DRO_RCW: self.drop_wlanreceive,
			self.DRO_TML: self.drop_lantransmite,
			self.DRO_TMW: self.drop_wlantransmite,
			self.ERR_RCL: self.error_lanreceive,
			self.ERR_RCW: self.error_wlanreceive,
			self.ERR_TML: self.error_lantransmite,
			self.ERR_TMW: self.error_wlantransmite,
			self.NET_TYP: self.nettyp,
			self.RC: self.receive,
			self.RCL: self.lanreceive,
			self.RCLT: self.lanreceivetotalout,
			self.RCL_MB: self.lanreceivemb,
			self.RCT: self.receivetotalout,
			self.RCW: self.wlanreceive,
			self.RCWT: self.wlanreceivetotalout,
			self.RCW_MB: self.wlanreceivemb,
			self.RC_MB: self.receivemb,
			self.TM: self.transmit,
			self.TML: self.lantransmit,
			self.TMLT: self.lantransmittotalout,
			self.TML_MB: self.lantransmitmb,
			self.TMT: self.transmittotalout,
			self.TMW: self.wlantransmit,
			self.TMWT: self.wlantransmittotalout,
			self.TMW_MB: self.wlantransmitmb,
			self.TM_MB: self.transmitmb
		}.get(self.type)
		if self.type in (self.RC, self.RCL, self.RCL_MB, self.RCW, self.RCW_MB, self.RC_MB, self.TM, self.TML, self.TML_MB, self.TMW, self.TMW_MB, self.TM_MB):
			text = f"{value:3.2f} Mb/s"
		elif self.type == self.NET_TYP:
			text = value
		else:
			text = None if value is None else f"{int(value)}"
		return text
