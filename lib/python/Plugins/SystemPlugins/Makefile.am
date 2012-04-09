installdir = $(pkglibdir)/python/Plugins/SystemPlugins

SUBDIRS = PositionerSetup Satfinder SoftwareManager \
	Videomode VideoTune Hotplug FastScan \
	DefaultServicesScanner CommonInterfaceAssignment \
	VideoEnhancement WirelessLan NetworkWizard Blindscan

if XTREND
SUBDIRS += SatelliteEquipmentControl DiseqcTester choiceRC XtrendFancontrol HdmiCEC
endif

if MARA
SUBDIRS += SatelliteEquipmentControl DiseqcTester choiceRC XtrendFancontrol HdmiCEC
endif

if VUUNO
SUBDIRS += VuUnoFancontrol SatelliteEquipmentControl DiseqcTester CableScan FirmwareUpgrade RemoteControlCode HdmiCEC
endif

if VUULTIMO
SUBDIRS += VuUnoFancontrol SatelliteEquipmentControl DiseqcTester CableScan FirmwareUpgrade RemoteControlCode HdmiCEC
endif

if VUDUO
SUBDIRS += VuDuoFancontrol HdmiCEC
endif

if VUSOLO
SUBDIRS += HdmiCEC
endif

if TMTWIN
SUBDIRS += VuDuoFancontrol HdmiCEC
endif

if HAVE_TEMPFANCONTROL
SUBDIRS += TempFanControl
endif

if DREAMBOX
SUBDIRS += FrontprocessorUpgrade NFIFlash SatelliteEquipmentControl DiseqcTester CableScan 
endif

if GIGABLUE
SUBDIRS += VFDGiga SatelliteEquipmentControl DiseqcTester HdmiCEC
endif

if VENTON
SUBDIRS += SatelliteEquipmentControl DiseqcTester HdmiCEC 
endif

install_PYTHON =	\
	__init__.py
