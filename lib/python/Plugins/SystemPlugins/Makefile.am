installdir = $(pkglibdir)/python/Plugins/SystemPlugins

SUBDIRS = SoftwareManager PositionerSetup Satfinder \
	Videomode VideoTune Hotplug \
	CommonInterfaceAssignment \
	FastScan HdmiCEC VideoClippingSetup \
	VideoEnhancement WirelessLan NetworkWizard \
	SABnzbdSetup IniFanSetup

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
SUBDIRS += SatelliteEquipmentControl DiseqcTester CableScan
endif

install_PYTHON =	\
	__init__.py
