installdir = $(pkglibdir)/python/Plugins/SystemPlugins

SUBDIRS = PositionerSetup Satfinder \
	Videomode VideoTune Hotplug HdmiCEC \
	DefaultServicesScanner CommonInterfaceAssignment \
	VideoEnhancement WirelessLan NetworkWizard

if XTREND
SUBDIRS += XtrendFancontrol SatelliteEquipmentControl DiseqcTester FastScan Blindscan
endif

if VUPLUS
SUBDIRS += RemoteControlCode
endif

if VUUNO
SUBDIRS += VuUnoFancontrol SatelliteEquipmentControl DiseqcTester CableScan FastScan FirmwareUpgrade Blindscan 
endif

if VUULTIMO
SUBDIRS += VuUnoFancontrol SatelliteEquipmentControl DiseqcTester CableScan FastScan FirmwareUpgrade Blindscan
endif

if VUDUO
SUBDIRS += VuDuoFancontrol
endif

if HAVE_TEMPFANCONTROL
SUBDIRS += TempFanControl
endif

if DREAMBOX
SUBDIRS += FrontprocessorUpgrade NFIFlash SatelliteEquipmentControl DiseqcTester CableScan FastScan
endif

install_PYTHON =	\
	__init__.py
