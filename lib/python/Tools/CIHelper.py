from xml.etree.cElementTree import parse
from Tools.XMLTools import elementsWithTag, mergeText, stringToXML
from enigma import eDVBCIInterfaces, eDVBCI_UI, eEnv, eServiceCenter, eServiceReference
from timer import TimerEntry
import NavigationInstance 

import os

class CIHelper:

	CI_ASSIGNMENT_LIST = None
	CI_ASSIGNMENT_SERVICES_LIST = None
	CI_MULTIDESCRAMBLE = None
	CI_MULTIDESCRAMBLE_MODULES = ("AlphaCrypt", )

	def parse_ci_assignment(self):
		NUM_CI=eDVBCIInterfaces.getInstance().getNumOfSlots()
		if NUM_CI > 0:
			self.CI_ASSIGNMENT_LIST=[]
			def getValue(definitions, default):
				ret = ""
				Len = len(definitions)
				return Len > 0 and definitions[Len-1].text or default

			for ci in range(NUM_CI):
				filename = eEnv.resolve("${sysconfdir}/enigma2/ci") + str(ci) + ".xml"

				if not os.path.exists(filename):
					continue

				try:
					tree = parse(filename).getroot()
					read_services=[]
					read_providers=[]
					usingcaid=[]
					for slot in tree.findall("slot"):
						read_slot = getValue(slot.findall("id"), False).encode("UTF-8")

						for caid in slot.findall("caid"):
							read_caid = caid.get("id").encode("UTF-8")
							usingcaid.append(long(read_caid,16))

						for service in slot.findall("service"):
							read_service_ref = service.get("ref").encode("UTF-8")
							read_services.append (read_service_ref)

						for provider in slot.findall("provider"):
							read_provider_name = provider.get("name").encode("UTF-8")
							read_provider_dvbname = provider.get("dvbnamespace").encode("UTF-8")
							read_providers.append((read_provider_name,long(read_provider_dvbname,16)))

						self.CI_ASSIGNMENT_LIST.append((int(read_slot), (read_services, read_providers, usingcaid)))
				except:
					print "[CI_ASSIGNMENT %d] error parsing xml..." % ci

			services = []
			providers = []
			for item in self.CI_ASSIGNMENT_LIST:
				print "[CI_Activate] activate CI%d with following settings:" % item[0]
				print item[1]
				try:
					eDVBCIInterfaces.getInstance().setDescrambleRules(item[0],item[1])
				except:
					print "[CI_Activate_Config_CI%d] error setting DescrambleRules..." %item[0]
				for x in item[1][0]:
					services.append(x)
				for x in item[1][1]:
					providers.append(x[0])
			service_refs = []
			if len(services):
				for x in services:
					service_refs.append(eServiceReference(x))
			provider_services_refs = []
			if len(providers):
				provider_services_refs = self.getProivderServices(providers)
			self.CI_ASSIGNMENT_SERVICES_LIST = [service_refs, provider_services_refs]

	def load_ci_assignment(self, force = False):
		if self.CI_ASSIGNMENT_LIST is None or force:
			self.parse_ci_assignment()

	def getProivderServices(self, providers):
		provider_services_refs = []
		if len(providers):
			serviceHandler = eServiceCenter.getInstance()
			for x in providers:
				refstr = '1:7:0:0:0:0:0:0:0:0:(provider == "%s") && (type == 1) || (type == 17) || (type == 22) || (type == 25) || (type == 31) || (type == 134) || (type == 195) ORDER BY name:%s' % (x,x)
				myref = eServiceReference(refstr)
				servicelist = serviceHandler.list(myref)
				if not servicelist is None:
					while True:
						service = servicelist.getNext()
						if not service.valid():
							break
						provider_services_refs.append(service)
		return provider_services_refs

	def ServiceIsAssigned(self, ref):
		self.load_ci_assignment()

		if self.CI_ASSIGNMENT_SERVICES_LIST:
			for x in self.CI_ASSIGNMENT_SERVICES_LIST:
				if len(x) and ref in x:
					return True
		return False

	def canMultiDescramble(self, ref):
		if self.CI_MULTIDESCRAMBLE is None:
			no_ci = eDVBCIInterfaces.getInstance().getNumOfSlots()
			if no_ci > 0:
				self.CI_MULTIDESCRAMBLE = False
				for ci in range(no_ci):
					appname = eDVBCI_UI.getInstance().getAppName(ci)
					if appname in self.CI_MULTIDESCRAMBLE_MODULES:
						self.CI_MULTIDESCRAMBLE = True
		elif self.CI_MULTIDESCRAMBLE == False:
			return False
			
		if self.CI_ASSIGNMENT_LIST is not None and len(self.CI_ASSIGNMENT_LIST):
			for x in self.CI_ASSIGNMENT_LIST:
				if ref.toString() in x[1][0]:
					appname = eDVBCI_UI.getInstance().getAppName(x[0])
					if appname in self.CI_MULTIDESCRAMBLE_MODULES:
						return True
			for x in self.CI_ASSIGNMENT_LIST:
				f_providers = x[1][1]
				if len(f_providers):
					providers = []
					for prov in f_providers:
						providers.append(prov[0])
					provider_services_refs = self.getProivderServices(providers)
					if ref in provider_services_refs:
						appname = eDVBCI_UI.getInstance().getAppName(x[0])
						if appname in self.CI_MULTIDESCRAMBLE_MODULES:
							return True
		return False

	def isPlayable(self, service):
		service = eServiceReference(service)
		if NavigationInstance.instance.getRecordings():
			if self.ServiceIsAssigned(service):
				for timer in NavigationInstance.instance.RecordTimer.timer_list:
					if timer.state == TimerEntry.StateRunning:
						if timer.justplay:
							pass
						else:
							timerservice = timer.service_ref.ref
							if timerservice != service:
								if self.ServiceIsAssigned(timerservice):
									if self.canMultiDescramble(service):
										for x in (4, 2, 3):
											if  timerservice.getUnsignedData(x) !=  service.getUnsignedData(x):
												return 0
									else:
										return 0
		return 1

cihelper = CIHelper()

def isPlayable(service):
	ret = cihelper.isPlayable(service)
	return ret
