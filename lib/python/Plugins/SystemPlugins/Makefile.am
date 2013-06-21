installdir = $(pkglibdir)/python/Plugins/SystemPlugins

SUBDIRS = SoftwareManager PositionerSetup Satfinder \
	Videomode VideoTune Hotplug \
	DefaultServicesScanner CommonInterfaceAssignment \
	HdmiCEC VideoClippingSetup \
	VideoEnhancement WirelessLan NetworkWizard \
	SABnzbdSetup FastScan

if XTREND
SUBDIRS += SatelliteEquipmentControl DiseqcTester
endif

if ODIN
SUBDIRS += SatelliteEquipmentControl DiseqcTester
endif

if VUSOLO2
SUBDIRS += SatelliteEquipmentControl DiseqcTester
endif

if VUUNO
SUBDIRS += SatelliteEquipmentControl DiseqcTester CableScan
endif

if VUULTIMO
SUBDIRS += SatelliteEquipmentControl DiseqcTester CableScan
endif

if DREAMBOX
SUBDIRS += FrontprocessorUpgrade NFIFlash SatelliteEquipmentControl DiseqcTester CableScan
endif

install_PYTHON =	\
	__init__.py
