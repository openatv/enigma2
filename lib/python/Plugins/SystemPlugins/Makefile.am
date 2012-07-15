installdir = $(pkglibdir)/python/Plugins/SystemPlugins

SUBDIRS = PositionerSetup Satfinder FastScan \
	Videomode VideoTune Hotplug HdmiCEC \
	DefaultServicesScanner CommonInterfaceAssignment SoftwareManager \
	VideoEnhancement WirelessLan NetworkWizard SABnzbdSetup VideoClippingSetup

if XTREND
SUBDIRS += SatelliteEquipmentControl DiseqcTester
endif

if ODIN
SUBDIRS += SatelliteEquipmentControl DiseqcTester
endif

if VUUNO
SUBDIRS += SatelliteEquipmentControl DiseqcTester CableScan
endif

if VUULTIMO
SUBDIRS += SatelliteEquipmentControl DiseqcTester CableScan
endif

if HAVE_TEMPFANCONTROL
SUBDIRS += TempFanControl
endif

if DREAMBOX
SUBDIRS += FrontprocessorUpgrade NFIFlash SatelliteEquipmentControl DiseqcTester CableScan
endif

install_PYTHON =	\
	__init__.py
