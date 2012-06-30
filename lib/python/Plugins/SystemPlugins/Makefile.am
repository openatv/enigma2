installdir = $(pkglibdir)/python/Plugins/SystemPlugins

SUBDIRS = PositionerSetup Satfinder SoftwareManager \
	Videomode VideoTune Hotplug FastScan CableScan \
	DefaultServicesScanner CommonInterfaceAssignment \
	VideoEnhancement WirelessLan NetworkWizard

if XTREND
SUBDIRS += SatelliteEquipmentControl DiseqcTester HdmiCEC
endif

if ODIN
SUBDIRS += SatelliteEquipmentControl DiseqcTester HdmiCEC
endif

if VUUNO
SUBDIRS += SatelliteEquipmentControl DiseqcTester FirmwareUpgrade HdmiCEC
endif

if VUULTIMO
SUBDIRS += SatelliteEquipmentControl DiseqcTester FirmwareUpgrade HdmiCEC
endif

if VUDUO
SUBDIRS += HdmiCEC
endif

if VUSOLO
SUBDIRS += HdmiCEC
endif

if GBQUAD
SUBDIRS += HdmiCEC
endif

if TMTWIN
SUBDIRS += HdmiCEC
endif

if HAVE_TEMPFANCONTROL
SUBDIRS += TempFanControl
endif

if DREAMBOX
SUBDIRS += FrontprocessorUpgrade NFIFlash SatelliteEquipmentControl DiseqcTester
endif

if GIGABLUE
SUBDIRS += SatelliteEquipmentControl DiseqcTester HdmiCEC
endif

if VENTON
SUBDIRS += SatelliteEquipmentControl DiseqcTester HdmiCEC
endif

install_PYTHON =	\
	__init__.py
