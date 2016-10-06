# -*- coding: utf-8 -*-
from os import path as os_path, walk as os_walk, unlink as os_unlink
import operator
from Plugins.Plugin import PluginDescriptor
from Screens.ServiceInfo import ServiceInfoList, ServiceInfoListEntry
from ServiceReference import ServiceReference
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.config import config, ConfigSelection, ConfigYesNo, getConfigListEntry, ConfigSubsection, ConfigText
from Components.ConfigList import ConfigListScreen
from Components.NimManager import nimmanager
from Components.Label import Label
from Components.Pixmap import Pixmap
from Components.ProgressBar import ProgressBar
from Components.ServiceList import refreshServiceList
from Components.ActionMap import ActionMap
from Screens import InfoBarGenerics
from Screens.InfoBar import InfoBar
from glob import glob

config.misc.fastscan = ConfigSubsection()
config.misc.fastscan.last_configuration = ConfigText(default = "()")

from enigma import eFastScan, eDVBFrontendParametersSatellite, eDVBDB, eComponentScan, \
	eDVBSatelliteEquipmentControl, eDVBFrontendParametersTerrestrial, \
	eDVBFrontendParametersCable, eConsoleAppContainer, eDVBResourceManager, eServiceReference, eServiceCenter
from Plugins.SystemPlugins.FastScan.Scan import ServiceScan
from Components.NimManager import nimmanager

import os

class FastScan:
	def __init__(self, text, progressbar, scanTuner = 0, transponderParameters = None, scanPid = 900, keepNumbers = False, keepSettings = False, providerName = 'Favorites', alternative_number_mode = config.usage.alternative_number_mode.value):
		self.text = text
		self.progressbar = progressbar
		self.transponderParameters = transponderParameters
		self.scanPid = scanPid
		self.scanTuner = scanTuner
		self.keepNumbers = keepNumbers
		self.keepSettings = keepSettings
		self.providerName = providerName
		self.scan_alternative_number_mode = alternative_number_mode
		self.done = False

	def execBegin(self):
		self.text.setText(_('Scanning %s...') % self.providerName)
		self.progressbar.setValue(0)
		self.scan = eFastScan(self.scanPid, self.providerName, self.transponderParameters, self.keepNumbers, self.keepSettings)
		self.scan.scanCompleted.get().append(self.scanCompleted)
		self.scan.scanProgress.get().append(self.scanProgress)
		fstfile = None
		fntfile = None
		for root, dirs, files in os_walk('/tmp/'):
			for f in files:
				if f.endswith('.bin'):
					if '_FST' in f:
						fstfile = os_path.join(root, f)
					elif '_FNT' in f:
						fntfile = os_path.join(root, f)
		if fstfile and fntfile:
			self.scan.startFile(fntfile, fstfile)
			os_unlink(fstfile)
			os_unlink(fntfile)
		else:
			self.scan.start(self.scanTuner)

	def execEnd(self):
		self.scan.scanCompleted.get().remove(self.scanCompleted)
		self.scan.scanProgress.get().remove(self.scanProgress)
		del self.scan

	def scanProgress(self, progress):
		self.progressbar.setValue(progress)

	def scanCompleted(self, result):
		self.done = True
		if result < 0:
			self.text.setText(_('Scanning failed!'))
		else:
			self.text.setText(ngettext('List version %d, found %d channel', 'List version %d, found %d channels', result) % (self.scan.getVersion(), result))

	def destroy(self):
		pass

	def isDone(self):
		return self.done

class FastScanStatus(Screen):
	skin = """
	<screen position="150,115" size="420,180" title="Fast Scan">
		<widget name="frontend" pixmap="icons/scan-s.png" position="5,5" size="64,64" transparent="1" alphatest="on" />
		<widget name="scan_state" position="10,120" zPosition="2" size="400,30" font="Regular;18" />
		<widget name="scan_progress" position="10,155" size="400,15" pixmap="progress_big.png" borderWidth="2" borderColor="#cccccc" />
	</screen>"""

	def __init__(self, session, scanTuner = 0, transponderParameters = None, scanPid = 900, keepNumbers = False, keepSettings = False, providerName = 'Favorites', alternative_number_mode = config.usage.alternative_number_mode.value):
		Screen.__init__(self, session)
		self.setTitle(_("Fast Scan"))
		self.scanPid = scanPid
		self.scanTuner = scanTuner
		self.transponderParameters = transponderParameters
		self.keepNumbers = keepNumbers
		self.keepSettings = keepSettings
		self.providerName = providerName
		self.scan_alternative_number_mode = alternative_number_mode

		self["frontend"] = Pixmap()
		self["scan_progress"] = ProgressBar()
		self["scan_state"] = Label(_("scan state"))

		self.prevservice = self.session.nav.getCurrentlyPlayingServiceReference()
		self.session.nav.stopService()

		self["actions"] = ActionMap(["OkCancelActions"],
			{
				"ok": self.ok,
				"cancel": self.cancel
			})

		self.onFirstExecBegin.append(self.doServiceScan)

	def doServiceScan(self):
		self["scan"] = FastScan(self["scan_state"], self["scan_progress"], self.scanTuner, self.transponderParameters, self.scanPid, self.keepNumbers, self.keepSettings, self.providerName)

	def restoreService(self):
		if self.prevservice:
			self.session.nav.playService(self.prevservice)

	def ok(self):
		if self["scan"].isDone():
			refreshServiceList()
			self.restoreService()
			self.close()

	def cancel(self):
		self.restoreService()
		self.close()

class FastScanScreen(ConfigListScreen, Screen):
	skin = """
	<screen position="100,115" size="520,290" title="Fast Scan">
		<widget name="config" position="10,10" size="500,250" scrollbarMode="showOnDemand" />
		<widget name="introduction" position="10,265" size="500,25" font="Regular;20" halign="center" />
	</screen>"""

	def __init__(self, session, nimList):
		Screen.__init__(self, session)
		self.prevservice = self.session.nav.getCurrentlyPlayingServiceReference()
		self.setTitle(_("Fast Scan"))
		
		self.providers = {}
		
		#hacky way
		self.providers['Astra_19_AustriaSat'] = (0, 900, True)
		self.providers['DigiTV'] = (0, 900, True)
		self.providers['FocusSat'] = (0, 900, True)
		self.providers['Freesat_Czech_Republic'] = (0, 900, True)
		self.providers['Freesat_Hungary'] = (0, 900, True)
		self.providers['Freesat_Moldavia'] = (0, 900, True)
		self.providers['Freesat_Romania'] = (0, 900, True)
		self.providers['Freesat_Slovenske'] = (0, 900, True)
		self.providers['HDPlus'] = (0, 900, True)
		self.providers['Own_Scan'] = (0, 900, True)
		self.providers['Sky_de_Full'] = (0, 900, True)
		self.providers['Sky_de_Bundesliga'] = (0, 900, True)
		self.providers['Sky_de_Cinema'] = (0, 900, True)
		self.providers['Sky_de_Entertainment'] = (0, 900, True)
		self.providers['Sky_de_Sport'] = (0, 900, True)
		self.providers['Sky_de_Starter'] = (0, 900, True)
		self.providers['UPC'] = (0, 900, True)
		
		#orgin
		self.providers['CanalDigitaal'] = (1, 900, True)
		self.providers['Canal Digitaal Astra 1'] = (0, 900, True)
		self.providers['TV Vlaanderen'] = (1, 910, True)
		self.providers['TV Vlaanderen  Astra 1'] = (0, 910, True)
		self.providers['TeleSAT'] = (0, 920, True)
		self.providers['TeleSAT Astra3'] = (1, 920, True)
		self.providers['HD Austria'] = (0, 950, False)
		self.providers['Fast Scan Deutschland'] = (0, 960, False)
		self.providers['Fast Scan Deutschland Astra3'] = (1, 960, False) 
		self.providers['Skylink Czech Republic'] = (1, 30, False)
		self.providers['Skylink Slovak Republic'] = (1, 31, False)
		self.providers['AustriaSat Magyarorszag Eutelsat 9E'] = (2, 951, False)
		self.providers['AustriaSat Magyarorszag Astra 3'] = (1, 951, False)

		self.transponders = ((12515000, 22000000, eDVBFrontendParametersSatellite.FEC_5_6, 192,
			eDVBFrontendParametersSatellite.Polarisation_Horizontal, eDVBFrontendParametersSatellite.Inversion_Unknown,
			eDVBFrontendParametersSatellite.System_DVB_S, eDVBFrontendParametersSatellite.Modulation_QPSK,
			eDVBFrontendParametersSatellite.RollOff_alpha_0_35, eDVBFrontendParametersSatellite.Pilot_Off),
			(12070000, 27500000, eDVBFrontendParametersSatellite.FEC_3_4, 235,
			eDVBFrontendParametersSatellite.Polarisation_Horizontal, eDVBFrontendParametersSatellite.Inversion_Unknown,
			eDVBFrontendParametersSatellite.System_DVB_S, eDVBFrontendParametersSatellite.Modulation_QPSK,
			eDVBFrontendParametersSatellite.RollOff_alpha_0_35, eDVBFrontendParametersSatellite.Pilot_Off))
		self.session.postScanService = session.nav.getCurrentlyPlayingServiceOrGroup()
                
		self["actions"] = ActionMap(["SetupActions", "MenuActions"],
		{
			"ok": self.keyGo,
			"save": self.keyGo,
			"cancel": self.keyCancel,
			"menu": self.closeRecursive,
		}, -2)

		providerList = list(x[0] for x in sorted(self.providers.iteritems(), key = operator.itemgetter(0)))

		lastConfiguration = eval(config.misc.fastscan.last_configuration.value)
		if not lastConfiguration:
			lastConfiguration = (nimList[0][0], providerList[0], True, True, False, config.usage.alternative_number_mode.value)
		self.scan_nims = ConfigSelection(default = lastConfiguration[0], choices = nimList)
		self.scan_provider = ConfigSelection(default = lastConfiguration[1], choices = providerList)
		self.scan_hd = ConfigYesNo(default = lastConfiguration[2])
		self.scan_keepnumbering = ConfigYesNo(default = lastConfiguration[3])
		self.scan_keepsettings = ConfigYesNo(default = lastConfiguration[4])
		# WORKAROUND FOR OLD CONFIGURATION WHICH MISSES lastConfiguration[5]
		try:
			self.scan_alternative_number_mode = ConfigYesNo(default = lastConfiguration[5])
		except:
			self.scan_alternative_number_mode =  ConfigYesNo(default = config.usage.alternative_number_mode.value)
		#	self.scan_alternative_number_mode = ConfigYesNo(default = lastConfiguration[5])
		# WORKAROUND FOR OLD CONFIGURATION WHICH MISSES lastConfiguration[5]
		
		self.list = []
		self.tunerEntry = getConfigListEntry(_("Tuner"), self.scan_nims)
		self.list.append(self.tunerEntry)

		self.scanProvider = getConfigListEntry(_("Provider"), self.scan_provider)
		self.list.append(self.scanProvider)

		self.scanHD = getConfigListEntry(_("HD list"), self.scan_hd)
		self.list.append(self.scanHD)

		self.list.append(getConfigListEntry(_("Use fastscan channel numbering"), self.scan_keepnumbering))
		self.list.append(getConfigListEntry(_("Use fastscan channel names"), self.scan_keepsettings))
		self.list.append(getConfigListEntry(_("Use alternate bouquets numbering"), self.scan_alternative_number_mode))

		ConfigListScreen.__init__(self, self.list)
		self["config"].list = self.list
		self["config"].l.setList(self.list)

		self.finished_cb = None

		self["introduction"] = Label(_("Select your provider, and press OK to start the scan"))


	def addSatTransponder(self, tlist, frequency, symbol_rate, polarisation, fec, inversion, orbital_position, system, modulation, rolloff, pilot):
		parm = eDVBFrontendParametersSatellite()
		parm.modulation = modulation
		parm.system = system
		parm.frequency = frequency * 1000
		parm.symbol_rate = symbol_rate * 1000
		parm.polarisation = polarisation
		parm.fec = fec
		parm.inversion = inversion
		parm.orbital_position = orbital_position
		parm.rolloff = rolloff
		parm.pilot = pilot
		tlist.append(parm)
		
	def restoreService(self):
		if self.prevservice:
			self.session.nav.playService(self.prevservice)


	def readXML(self, xml):
                global ret
                self.session.nav.stopService()
		tlist = []
		self.path = "/etc/enigma2"
	       	lastsc1 = self.path + "/userbouquet.LastScanned.tv"
	       	favlist1 = self.path + "/bouquets.tv"
	       	newbouq11 = '#SERVICE 1:7:1:0:0:0:0:0:0:0:FROM BOUQUET "userbouquet.LastScanned.tv" ORDER BY bouquet'
                if os.path.isfile(favlist1):              
                         f = open(favlist1, "a+")
                         ret = f.read().split("\n")
		         if newbouq11 in ret:
				yy = ret.index(newbouq11)
				ret.pop(yy)
                         f.close()
                         os.remove(favlist1)
                yx = [newbouq11]
                yx.extend(ret)
                yz = open(favlist1, "w")
                yz.write("\n".join(map(lambda x: str(x), yx)))
                yz.close()     
                h = open('/etc/enigma2/userbouquet.LastScanned.tv', "w")
                h.write("#NAME Last Scanned\n")
                h.close()
                eDVBDB.getInstance().reloadBouquets()
		import xml.dom.minidom as minidom
		try:
                	xmldoc = "/usr/lib/enigma2/python/Plugins/SystemPlugins/FastScan/xml/" + xml + ".xml"
			xmldoc = minidom.parse(xmldoc)
			tr_list = xmldoc.getElementsByTagName('transporder')
			for lista in tr_list:      
				frequency = lista.getAttribute("frequency")
				symbolrate = lista.getAttribute("symbolrate")
				fec = lista.getAttribute("fec")
				orbpos = lista.getAttribute("orbpos")
				pol = lista.getAttribute("pol")
				system = lista.getAttribute("system")
				modulation = lista.getAttribute("modulation")
					
				self.frequency = frequency
				self.symbolrate = symbolrate
				if pol == "H":
			    		pol = 0
				elif pol == "V":
			    		pol = 1
				elif pol == "L":
			    		pol = 2
				elif pol == "R":
			    		pol = 3
				self.polarization =  pol # 0 - H, 1 - V, 2- CL, 3 - CR

				if fec == "Auto":
			    		fec = 0
				elif fec == "1/2":
			    		fec = 1
				elif fec == "2/3":
			    		fec = 2
				elif fec == "3/4":
			    		fec = 3
				elif fec == "3/5":
			    		fec = 4
				elif fec == "4/5":
			    		fec = 5
				elif fec == "5/6":
			    		fec = 6
				elif fec == "7/8":
			    		fec = 7
				elif fec == "8/9":
			    		fec = 8
				elif fec == "9/10":
			    		fec = 9
		
				self.fec = fec # 0 - Auto, 1 - 1/2, 2 - 2/3, 3 - 3/4, 4 - 3/5, 5 - 4/5, 6 - 5/6, 7 - 7/8, 8 - 8/9 , 9 - 9/10,
			
				self.inversion = 2 # 0 - off, 1 -on, 2 - AUTO
			
				self.orbpos = orbpos
			
				if system == "DVBS":
			    		system = 0
				elif system == "DVBS2":
			    		system = 1
			    
				self.system = system # DVB-S = 0, DVB-S2 = 1
			
				if modulation == "QPSK":
			    		modulation = 1
				elif modulation == "8PSK":
			    		modulation = 2
			    
				self.modulation = modulation # 0- QPSK, 1 -8PSK
			
				self.rolloff = 0 #
			
				self.pilot = 2 # 0 - off, 1 - on 2 - AUTO
		
				self.addSatTransponder(tlist, int(self.frequency),
							int(self.symbolrate),
							int(self.polarization),
							int(fec),
							int(self.inversion),
							int(orbpos),
							int(self.system),
							int(self.modulation),
							int(self.rolloff),
							int(self.pilot))
		 
                        self.session.openWithCallback(self.bouqmake, ServiceScan, [{"transponders": tlist, "feid": int(self.scan_nims.value), "flags": 0, "networkid": 0}])
                except:
                        #self.session.open(MessageBox, _("xml File missing, please check it."), MessageBox.TYPE_ERROR)
                        print "xml File missing, please check it."
									
	def bouqmake(self, session):
		prov = self.scan_provider.value.lower()
		global sname
		global ret
		ret1 = ret
#####new		
		if prov == "sky_de_full":
		        provlist = ['Sky_de_Bundesliga', 'Sky_de_Cinema', 'Sky_de_Entertainment', 'Sky_de_Sport', 'Sky_de_Starter']
                        for xprov in provlist:
                                newprov = xprov
				self.path = "/etc/enigma2"
				lastsc = self.path + "/userbouquet.LastScanned.tv"
				newbouq = self.path + "/userbouquet." + newprov + ".tv"
				newbouq_unsort = self.path + "/userbouquet." + newprov + ".tv_unsort"
       				favlist = self.path + "/bouquets.tv"
       				newbouq_unsortlist = self.path + newbouq_unsort
       				newbouq1 = '#SERVICE 1:7:1:0:0:0:0:0:0:0:FROM BOUQUET "userbouquet.' + newprov + '.tv" ORDER BY bouquet\r'
       				newbouq2 = '#NAME ' + newprov + ' '
       				newbouq3 = '"userbouquet.' + newprov + '.tv"'
               			newbouq11 = '#SERVICE 1:7:1:0:0:0:0:0:0:0:FROM BOUQUET "userbouquet.LastScanned.tv" ORDER BY bouquet'
               			path = self.path
       				#prefix = self.scan_provider.value 
       				try:
               				txtdoc = "/usr/lib/enigma2/python/Plugins/SystemPlugins/FastScan/xml/" + newprov.lower() + ".txt"
       					hh = []
               				gg = open(txtdoc, "r")
       					reta = gg.read().split("\n")
					gg.close()
               				ff = open(lastsc, "r")
       					retb = ff.read().split("\n")
					ff.close()
       					i = 1
       					wx = [newbouq2]
       					wx1 = [newbouq2]
                			if retb[1].startswith("#SERVICE"):
                        			while i+1 < len(retb):
              						self.updateServiceName(int(i))
                               				if sname in reta:
                                       				wx.append(sname + " " + retb[i])
                        	
                       					i +=1
                				wz = open(newbouq_unsort, "w")
                				wz.write("\n".join(map(lambda x: str(x), wx)))    
                				wz.close()
                        			for wwww in reta:
                        				for s in wx:
                        	                		www1 = s.rsplit("#", 1)
                        	                		wwww1 = www1[0].rstrip()
                                        			if wwww1 == wwww:
                                        	        		s1 = "#" + www1[1]
                                       					wx1.append(s1)
                               	                			break
                                                wz1 = open(newbouq, "w")
                				wz1.write("\n".join(map(lambda x: str(x), wx1)))    
                				wz1.close()
                				rety = []
                        			if os.path.isfile(favlist):
                        				os.remove(favlist)
                        			if os.path.isfile(newbouq_unsortlist):
                        				os.remove(newbouq_unsortlist)
                        			for zz in ret1:
                        				if newbouq3 in zz:
                        					print "no Service add"
                               				else:
                                       				rety.append(zz)
                        			rety[1:1] = [newbouq1]
                                                ret1 = rety
                				wv = open(favlist, "w")
                				wv.write("\n".join(map(lambda x: str(x), rety)))
                				wv.close()
                				#eDVBDB.getInstance().reloadBouquets()
                        		else:
                				wv = open(favlist, "w")
                				wv.write("\n".join(map(lambda x: str(x), ret1)))
                				wv.close()                   
                				#eDVBDB.getInstance().reloadBouquets()                         	
                        			self.keyCancel()
                		except:
                        		print 'My error, value:no xml found'
                        eDVBDB.getInstance().reloadBouquets()         
                       			#self.session.open(MessageBox, _("Chanel-txt File missing, please check it."), MessageBox.TYPE_ERROR)		
###new end
		else:
			self.path = "/etc/enigma2"
			lastsc = self.path + "/userbouquet.LastScanned.tv"
			newbouq = self.path + "/userbouquet." + self.scan_provider.value + ".tv"
			newbouq_unsort = self.path + "/userbouquet." + self.scan_provider.value + ".tv_unsort"
       			favlist = self.path + "/bouquets.tv"
       			newbouq_unsortlist = self.path + newbouq_unsort
       			newbouq1 = '#SERVICE 1:7:1:0:0:0:0:0:0:0:FROM BOUQUET "userbouquet.' + self.scan_provider.value + '.tv" ORDER BY bouquet\r'
       			newbouq2 = '#NAME ' + self.scan_provider.value + ' '
       			newbouq3 = '"userbouquet.' + self.scan_provider.value + '.tv"'
               		newbouq11 = '#SERVICE 1:7:1:0:0:0:0:0:0:0:FROM BOUQUET "userbouquet.LastScanned.tv" ORDER BY bouquet'
               		path = self.path
       			prefix = self.scan_provider.value 
       			try:
               			txtdoc = "/usr/lib/enigma2/python/Plugins/SystemPlugins/FastScan/xml/" + self.scan_provider.value.lower() + ".txt"
       				hh = []
               			gg = open(txtdoc, "r")
       				reta = gg.read().split("\n")
				gg.close()
               			ff = open(lastsc, "r")
       				retb = ff.read().split("\n")
				ff.close()
       				i = 1
       				wx = [newbouq2]
       				wx1 = [newbouq2]
                		if retb[1].startswith("#SERVICE"):
                        		while i+1 < len(retb):	       
              					self.updateServiceName(int(i))
                               			if sname in reta:
                                       			wx.append(sname + " " + retb[i])
                        	
                       				i +=1
                			wz = open(newbouq_unsort, "w")
                			wz.write("\n".join(map(lambda x: str(x), wx)))    
                			wz.close()
                        		for wwww in reta:
                        			for s in wx:
                        	                	www1 = s.rsplit("#", 1)
                        	                	wwww1 = www1[0].rstrip()
                                        		if wwww1 == wwww:
                                        	        	s1 = "#" + www1[1]
                                       				wx1.append(s1)
                               	                		break
                			wz1 = open(newbouq, "w")
                			wz1.write("\n".join(map(lambda x: str(x), wx1)))    
                			wz1.close()
                        		
                 		
                			rety = []
                        		if os.path.isfile(favlist):              
                        			os.remove(favlist)                            	
                        		if os.path.isfile(newbouq_unsortlist):              
                        			os.remove(newbouq_unsortlist)
                        		for zz in ret:
                        			if newbouq3 in zz:
                        				print "no Service add"
                               			else:
                                       			rety.append(zz)
                        		rety[1:1] = [newbouq1]
                			wv = open(favlist, "w")
                			wv.write("\n".join(map(lambda x: str(x), rety)))
                			wv.close()
                			eDVBDB.getInstance().reloadBouquets()
                                 
                        	else:
                			wv = open(favlist, "w")
                			wv.write("\n".join(map(lambda x: str(x), ret)))
                			wv.close()                   
                			eDVBDB.getInstance().reloadBouquets()                         	
                        		self.keyCancel()
                	except:
                        	print 'My error, value:no xml found' 
                       		#self.session.open(MessageBox, _("Chanel-txt File missing, please check it."), MessageBox.TYPE_ERROR)
	
        
        def searchNumberHelper(self, serviceHandler, num, bouquet):
		servicelist = self.serviceHandler.list(bouquet)
		if not servicelist is None:
			while num:
				serviceIterator = servicelist.getNext()
				if not serviceIterator.valid(): #check end of list
					break
				playable = not (serviceIterator.flags & (eServiceReference.isMarker|eServiceReference.isDirectory))
				if playable:
					num -= 1;
			if not num: #found service with searched number ?
				return serviceIterator, 0
		return None, num  

	def updateServiceName(self, number):
		global sname
                bouquet = InfoBar.instance.servicelist.bouquet_root
		service = None
		self.serviceHandler = eServiceCenter.getInstance()
		serviceHandler = self.serviceHandler
		bouquetlist = serviceHandler.list(bouquet)
		if not bouquetlist is None:
			while number:
				bouquet = bouquetlist.getNext()
				if not bouquet.valid(): #check end of list
					break
				if bouquet.flags & eServiceReference.isDirectory:
					service, number = self.searchNumberHelper(serviceHandler, number, bouquet)
                if service is not None:
			info = serviceHandler.info(service)
			sname = info.getName(service).replace('\xc2\x86', '').replace('\xc2\x87', '')
		else:
			sname = _("Unknown Service")


        def keyGo(self):
		prov = self.scan_provider.value.lower()
                if prov == "astra_19_austriasat" or prov == "digitv" or prov == "focussat" or prov == "freesat_czech_republic" or prov == "freesat_hungary" or prov == "freesat_moldavia" or prov == "freesat_slovenske" or prov == "freesat_romania" or prov == "hdplus" or prov == "own_scan" or prov == "sky_de_starter" or prov == "sky_de_cinema" or prov == "sky_de_sport" or prov == "sky_de_bundesliga" or prov == "sky_de_entertainment" or prov == "sky_de_full" or prov == "upc":           
                  if self.scan_alternative_number_mode.value == True:
                        config.usage.alternative_number_mode.value = True
                        config.usage.alternative_number_mode.save()
                  else:
                        config.usage.alternative_number_mode.value = False
                        config.usage.alternative_number_mode.save()
		  config.misc.fastscan.last_configuration.value = `(self.scan_nims.value, self.scan_provider.value, self.scan_hd.value, self.scan_keepnumbering.value, self.scan_keepsettings.value, self.scan_alternative_number_mode.value)`
		  config.misc.fastscan.save()
		  self.readXML(self.scan_provider.value.lower())
		else:
                  if self.scan_alternative_number_mode.value == True:
                        config.usage.alternative_number_mode.value = True
                        config.usage.alternative_number_mode.save()
                  else:
                        config.usage.alternative_number_mode.value = False
                        config.usage.alternative_number_mode.save()
		  config.misc.fastscan.last_configuration.value = `(self.scan_nims.value, self.scan_provider.value, self.scan_hd.value, self.scan_keepnumbering.value, self.scan_keepsettings.value, self.scan_alternative_number_mode.value)`
		  config.misc.fastscan.save()
		  self.startScan()


	def getTransponderParameters(self, number):
		transponderParameters = eDVBFrontendParametersSatellite()
		transponderParameters.frequency = self.transponders[number][0]
		transponderParameters.symbol_rate = self.transponders[number][1]
		transponderParameters.fec = self.transponders[number][2]
		transponderParameters.orbital_position = self.transponders[number][3]
		transponderParameters.polarisation = self.transponders[number][4]
		transponderParameters.inversion = self.transponders[number][5]
		transponderParameters.system = self.transponders[number][6]
		transponderParameters.modulation = self.transponders[number][7]
		transponderParameters.rolloff = self.transponders[number][8]
		transponderParameters.pilot = self.transponders[number][9]
		return transponderParameters

	def startScan(self):
		pid = self.providers[self.scan_provider.value][1]
		if self.scan_hd.value and self.providers[self.scan_provider.value][2]:
			pid += 1
		if self.scan_nims.value:
			self.session.open(FastScanStatus, scanTuner = int(self.scan_nims.value),
				transponderParameters = self.getTransponderParameters(self.providers[self.scan_provider.value][0]),
				scanPid = pid, keepNumbers = self.scan_keepnumbering.value, keepSettings = self.scan_keepsettings.value,
				providerName = self.scan_provider.getText(), alternative_number_mode = config.usage.alternative_number_mode.value)

	def keyCancel(self):
	        self.restoreService()
		self.close()

def FastScanMain(session, **kwargs):
	if session.nav.RecordTimer.isRecording():
		session.open(MessageBox, _("A recording is currently running. Please stop the recording before trying to scan."), MessageBox.TYPE_ERROR)
	else:
		nimList = []
		for n in nimmanager.nim_slots:
			if n.canBeCompatible("DVB-S"):
				try:
					n.config.dvbs
					legacy = False
				except:
					legacy = True
				break
			if not legacy:
				config = n.config.dvbs
			else:
				config = n.config
			config_mode = config.configMode.value
			if not n.canBeCompatible("DVB-S"):
				continue
			if config_mode == "nothing":
				continue
			if config_mode in ("loopthrough", "satposdepends"):
				root_id = nimmanager.sec.getRoot(n.slot_id, int(n.config.connectedTo.value))
				if n.type == nimmanager.nim_slots[root_id].type: # check if connected from a DVB-S to DVB-S2 Nim or vice versa
					continue
		nimList.append((str(n.slot), n.friendly_full_description))
		if nimList:
			session.open(FastScanScreen, nimList)
		else:
			print "No suitable sat tuner found!"

def FastScanStart(menuid, **kwargs):
	from Components.About import about
	if menuid == "scan":
			return [(_("Fast Scan"), FastScanMain, "fastscan", None)]     
	else:
		return []

def Plugins(**kwargs):
	if nimmanager.hasNimType("DVB-S"):
		return PluginDescriptor(name=_("Fast Scan"), description="Scan Diefferent sat provider", where = PluginDescriptor.WHERE_MENU, fnc=FastScanStart)
	else:
		return []

