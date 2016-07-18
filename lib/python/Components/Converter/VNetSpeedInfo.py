# -*- coding: utf-8 -*-


#This plugin is free software, you are allowed to
#modify it (if you keep the license),
#but you are not allowed to distribute/publish
#it without source code (this version and your modifications).
#This means you also have to distribute
#source code of your modifications.
#
#
#######################################################################
#
# NetSpeedInfo for VU+
# Coded by markusw (c) 2013
# www.vuplus-support.org
#
####################################################################### 

import os
from Components.Label import Label
from Components.Converter.Converter import Converter
from Components.Element import cached
from Poll import Poll

class VNetSpeedInfo(Poll, Converter, object):
	RCL = 0 			# Receive Lan in Megabit/s = Geschwindigkeit/Bandbreite
	TML = 1				# Transmit Lan in Megabit/s = Geschwindigkeit/Bandbreite
	RCW = 2				# Receive Wlan in Megabit/s = Geschwindigkeit/Bandbreite
	TMW = 3				# Transmit Wlan in Megabit/s = Geschwindigkeit/Bandbreite
	RCLT = 4			# Receive Lan-total seit dem letzten Neustart in Megabyte
	TMLT = 5			# Transmit Lan-total seit dem letzten Neustart in Megabyte
	RCWT = 6			# Receive Wlan-total seit dem letzten Neustart in Megabyte
	TMWT = 7			# Transmit Wlan-total seit dem letzten Neustart in Megabyte
	RCL_MB = 8		# Receive Lan in Megabyte/s = Geschwindigkeit/Bandbreite
	TML_MB = 9		# Transmit Lan in Megabyte/s = Geschwindigkeit/Bandbreite
	RCW_MB = 10		# Receive Wlan in Megabyte/s = Geschwindigkeit/Bandbreite
	TMW_MB = 11		# Transmit Wlan in Megabyte/s = Geschwindigkeit/Bandbreite
	RC = 12				# Receive Lan oder Wlan in Megabit/s = Geschwindigkeit/Bandbreite - wenn beides vorhanden wird Lan ausgegeben
	TM = 13				# Transmit Lan oder Wlan in Megabit/s = Geschwindigkeit/Bandbreite - wenn beides vorhanden wird Lan ausgegeben
	RCT = 14			# Receive Lan oder Wlan total seit dem letzten Neustart in Megabyte - wenn beides vorhanden wird Lan ausgegeben
	TMT = 15			# Transmit Lan oder Wlan total seit dem letzten Neustart in Megabyte - wenn beides vorhanden wird Lan ausgegeben
	RC_MB = 16		# Receive Lan oder Wlan in Megabyte/s = Geschwindigkeit/Bandbreite - wenn beides vorhanden wird Lan ausgegeben
	TM_MB = 17		# Transmit Lan oder Wlan in Megabyte/s = Geschwindigkeit/Bandbreite - wenn beides vorhanden wird Lan ausgegeben
	NET_TYP = 18	# Lan - Wlan - Lan+Wlan
	ERR_RCL = 19  # Fehler Lan-Receive
	ERR_TML = 20  # Fehler Lan-Transmit
	DRO_RCL = 21  # Drop Lan-Receive
	DRO_TML = 22  # Drop Lan-Transmit
	ERR_RCW = 23  # Fehler WLan-Receive
	ERR_TMW = 24  # Fehler WLan-Transmit
	DRO_RCW = 25  # Drop WLan-Receive
	DRO_TMW = 26  # Drop WLan-Transmit

	def __init__(self, type,update_interval = 1000):
		Poll.__init__(self)
		self.poll_interval = 1000
		self.poll_enabled = True
		self.lanreceivetotal=0
		self.lanreceivetotalout=0
		self.lanreceive=0
		self.lanreceivemb=0
		self.wlanreceivetotal=0
		self.wlanreceivetotalout=0
		self.wlanreceive=0
		self.wlanreceivemb=0
		self.lantransmittotal=0
		self.lantransmittotalout=0
		self.lantransmit=0
		self.lantransmitmb=0
		self.wlantransmittotal=0
		self.wlantransmittotalout=0
		self.wlantransmit=0
		self.wlantransmitmb=0
		self.receivetotal=0
		self.receive=0
		self.transmittotal=0
		self.transmit=0
		self.receivemb=0
		self.nettyp="NONE"
		self.error_lanreceive=0
		self.drop_lanreceive=0
		self.error_lantransmite=0
		self.drop_lantransmite=0
		self.error_wlanreceive=0
		self.drop_wlanreceive=0
		self.error_wlantransmite=0
		self.drop_wlantransmite=0
		
		Converter.__init__(self, type)
		self.type = type
		self.type = type
		if type == "RCL":
			self.type = self.RCL
		elif type == "TML":
			self.type = self.TML
		elif type == "RCW":
			self.type = self.RCW
		elif type == "TMW":
			self.type = self.TMW
		elif type == "RCLT":
			self.type = self.RCLT
		elif type == "TMLT":
			self.type = self.TMLT
		elif type == "RCWT":
			self.type = self.RCWT
		elif type == "TMWT":
			self.type = self.TMWT
		elif type == "RCL_MB":
			self.type = self.RCL_MB
		elif type == "TML_MB":
			self.type = self.TML_MB
		elif type == "RCW_MB":
			self.type = self.RCW_MB
		elif type == "TMW_MB":
			self.type = self.TMW_MB
		elif type == "RC":
			self.type = self.RC
		elif type == "TM":
			self.type = self.TM
		elif type == "RCT":
			self.type = self.RCT
		elif type == "TMT":
			self.type = self.TMT
		elif type == "RC_MB":
			self.type = self.RC_MB
		elif type == "TM_MB":
			self.type = self.TM_MB
		elif type == "NET_TYP":
			self.type = self.NET_TYP
		elif type == "ERR_RCL":
			self.type = self.ERR_RCL
		elif type == "ERR_TML":
			self.type = self.ERR_TML
		elif type == "DRO_RCL":
			self.type = self.DRO_RCL
		elif type == "DRO_TML":
			self.type = self.DRO_TML
		elif type == "ERR_RCW":
			self.type = self.ERR_RCW
		elif type == "ERR_TMW":
			self.type = self.ERR_TMW
		elif type == "DRO_RCW":
			self.type = self.DRO_RCW
		elif type == "DRO_TMW":
			self.type = self.DRO_TMW

	@cached
	def getText(self):
		textvalue = ""
		textvalue = self.updateNetSpeedInfoStatus() 
		return textvalue 
	
	text = property(getText)

	def updateNetSpeedInfoStatus(self):
		flaglan=0
		flagwlan=0
		bwm=open("/proc/net/dev")
		bw = bwm.readline()
		bw = bwm.readline()
		sp=[]
		while (bw):
			bw = bwm.readline()
			while bw.find("  ") is not -1:
				bw=bw.replace("  "," ")
			if bw.find("eth") is not -1:
				flaglan=1
				sp=bw.split(":")
				bw=sp[1].lstrip()
				sp=bw.split(" ")
				if len(sp[0]) is 0:
					sp[0]="0"
				if len(sp[2]) is 0:
					sp[2]="0"
				if len(sp[3]) is 0:
					sp[3]="0"
				if len(sp[8]) is 0:
					sp[8]="0"
				if len(sp[10]) is 0:
					sp[10]="0"
				if len(sp[11]) is 0:
					sp[11]="0"
				newlanreceive=int(sp[0])/1024
				self.error_lanrecive=int(sp[2])
				self.drop_lanreceive=int(sp[3])
				if self.lanreceivetotal > 0:
					self.lanreceive=float(newlanreceive-self.lanreceivetotal)*8/1024
					self.lanreceivemb=float(newlanreceive-self.lanreceivetotal)/1024
				else:
					self.lanreceive=0
				self.lanreceivetotal=newlanreceive
				self.lanreceivetotalout=newlanreceive/1024
				newlantransmit=int(sp[8])/1024
				self.error_lantransmite=int(sp[10])
				self.drop_lantransmite=int(sp[11])
				if self.lantransmittotal > 0:
					self.lantransmit=float(newlantransmit-self.lantransmittotal)*8/1024
					self.lantransmitmb=float(newlantransmit-self.lantransmittotal)/1024
				else:
					self.lantransmit=0
				self.lantransmittotal=newlantransmit
				self.lantransmittotalout=newlantransmit/1024
				if (self.lantransmittotal + self.lanreceivetotal) == 0:
					flaglan = 0
			if (bw.find("ra") is not -1) or (bw.find("wlan") is not -1) or (bw.find("wifi") is not -1):
				flagwlan=1
				sp=bw.split(":")
				bw=sp[1].lstrip()
				sp=bw.split(" ")
				if len(sp[0]) is 0:
					sp[0]="0"
				if len(sp[2]) is 0:
					sp[2]="0"
				if len(sp[3]) is 0:
					sp[3]="0"
				if len(sp[8]) is 0:
					sp[8]="0"
				if len(sp[10]) is 0:
					sp[10]="0"
				if len(sp[11]) is 0:
					sp[11]="0"
				newwlanreceive=int(sp[0])/1024
				self.error_wlanrecive=int(sp[2])
				self.drop_wlanreceive=int(sp[3])
				if self.wlanreceivetotal > 0:
					self.wlanreceive=float(newwlanreceive-self.wlanreceivetotal)*8/1024
					self.wlanreceivemb=float(newwlanreceive-self.wlanreceivetotal)/1024
				else:
					self.wlanreceive=0
				self.wlanreceivetotal=newwlanreceive
				self.wlanreceivetotalout=newwlanreceive/1024
				newwlantransmit=int(sp[8])/1024
				self.error_wlantransmite=int(sp[10])
				self.drop_wlantransmite=int(sp[11])
				if self.wlantransmittotal > 0:
					self.wlantransmit=float(newwlantransmit-self.wlantransmittotal)*8/1024
					self.wlantransmitmb=float(newwlantransmit-self.wlantransmittotal)/1024
				else:
					self.wlantransmit=0
				self.wlantransmittotal=newwlantransmit
				self.wlantransmittotalout=newwlantransmit/1024
		bwm.close()

#		if ((flaglan == 1) and (flagwlan == 0)) or ((flaglan == 1) and (flagwlan == 1)):
		if flaglan == 1:
			self.receive = self.lanreceive
			self.transmit = self.lantransmit
			self.receivetotal = self.lanreceivetotal
			self.transmittotal = self.lantransmittotal
			if flagwlan == 1:
				self.nettyp = "LAN+WLAN"
			else:
				self.nettyp = "LAN"
		elif (flaglan == 0) and (flagwlan == 1):
			self.receive = self.wlanreceive
			self.transmit = self.wlantransmit
			self.receivetotal = self.wlanreceivetotal
			self.transmittotal = self.wlantransmittotal
			self.nettyp = "WLAN"
		if (flaglan == 1) or (flagwlan == 1):
			self.receivemb = self.receive/8
			self.transmitmb = self.transmit/8
		if self.type == self.RCL:
			return "%3.2f" % self.lanreceive
		elif self.type == self.TML:
			return "%3.2f" % self.lantransmit
		elif self.type == self.RCW:
			return "%3.2f" % self.wlanreceive
		elif self.type == self.TMW:
			return "%3.2f" % self.wlantransmit
		elif self.type == self.RCLT:
			return "%d" % self.lanreceivetotalout
		elif self.type == self.TMLT:
			return "%d" % self.lantransmittotalout
		elif self.type == self.RCWT:
			return "%d" % self.wlanreceivetotalout
		elif self.type == self.TMWT:
			return "%d" % self.wlantransmittotalout
		elif self.type == self.RCL_MB:
			return "%3.2f" % self.lanreceivemb
		elif self.type == self.TML_MB:
			return "%3.2f" % self.lantransmitmb
		elif self.type == self.RCW_MB:
			return "%3.2f" % self.wlanreceivemb
		elif self.type == self.TMW_MB:
			return "%3.2f" % self.wlantransmitmb
		elif self.type == self.RC:
			return "%3.2f" % self.receive
		elif self.type == self.TM:
			return "%3.2f" % self.transmit
		elif self.type == self.RCT:
			return "%d" % self.receivetotalout
		elif self.type == self.TMT:
			return "%d" % self.transmittotalout
		elif self.type == self.RC_MB:
			return "%3.2f" % self.receivemb
		elif self.type == self.TM_MB:
			return "%3.2f" % self.transmitmb
		elif self.type == self.NET_TYP:
			return "%s" % self.nettyp
		elif self.type == self.ERR_RCL:
			return "%d" % self.error_lanreceive
		elif self.type == self.ERR_TML:
			return "%d" % self.error_lantransmite
		elif self.type == self.DRO_RCL:
			return "%d" % self.drop_lanreceive
		elif self.type == self.DRO_TML:
			return "%d" % self.drop_lantransmite
		elif self.type == self.ERR_RCW:
			return "%d" % self.error_wlanreceive
		elif self.type == self.ERR_TMW:
			return "%d" % self.error_wlantransmite
		elif self.type == self.DRO_RCW:
			return "%d" % self.drop_wlanreceive
		elif self.type == self.DRO_TMW:
			return "%d" % self.drop_wlantransmite

	def changed(self, what):
		if what[0] == self.CHANGED_POLL:
			Converter.changed(self, what)
