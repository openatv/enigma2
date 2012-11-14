installdir = $(pkglibdir)/python/Plugins/SystemPlugins

SUBDIRS = SoftwareManager PositionerSetup Satfinder \
	Videomode VideoTune Hotplug \
	DefaultServicesScanner CommonInterfaceAssignment \
	FastScan HdmiCEC VideoClippingSetup \
	VideoEnhancement WirelessLan NetworkWizard \
	SABnzbdSetup

if XTREND
SUBDIRS += SatelliteEquipmentControl DiseqcTester
endif

if MARA
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
