installdir = $(pkglibdir)/python/Plugins/SystemPlugins

SUBDIRS = PositionerSetup Satfinder SoftwareManager \
	Videomode VideoTune Hotplug HdmiCEC \
	DefaultServicesScanner CommonInterfaceAssignment \
	VideoEnhancement WirelessLan NetworkWizard Blindscan

if XTREND
SUBDIRS += SatelliteEquipmentControl DiseqcTester choiceRC FastScan XtrendFancontrol 
endif

if VUPLUS
SUBDIRS += RemoteControlCode
endif

if VUUNO
SUBDIRS += VuUnoFancontrol SatelliteEquipmentControl DiseqcTester CableScan FastScan FirmwareUpgrade
endif

if VUULTIMO
SUBDIRS += VuUnoFancontrol SatelliteEquipmentControl DiseqcTester CableScan FastScan FirmwareUpgrade
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
