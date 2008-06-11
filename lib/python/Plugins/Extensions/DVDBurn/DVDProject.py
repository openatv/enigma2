class DVDProject:
	def __init__(self):
		self.titles = [ ]
		self.target = None
		self.name = _("New DVD")

	def addService(self, service):
		import DVDTitle
		t = DVDTitle.DVDTitle()
		t.source = service

		from enigma import eServiceCenter, iServiceInformation
		serviceHandler = eServiceCenter.getInstance()

		info = serviceHandler.info(service)
		descr = info and " " + info.getInfoString(service, iServiceInformation.sDescription) or ""
		t.name = info and info.getName(service) or "Title" + descr

		self.titles.append(t)
		return t
