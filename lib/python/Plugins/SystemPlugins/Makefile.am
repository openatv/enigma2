installdir = $(pkglibdir)/python/Plugins/SystemPlugins

SUBDIRS = PositionerSetup Satfinder SoftwareManager \
	Videomode VideoTune Hotplug \
	DefaultServicesScanner CommonInterfaceAssignment \
	VideoEnhancement WirelessLan NetworkWizard Blindscan

if XTREND
SUBDIRS += SatelliteEquipmentControl DiseqcTester choiceRC FastScan XtrendFancontrol HdmiCEC
endif

if MARA
SUBDIRS += SatelliteEquipmentControl DiseqcTester FastScan Blindscan
endif

if VUUNO
SUBDIRS += VuUnoFancontrol SatelliteEquipmentControl DiseqcTester CableScan FastScan FirmwareUpgrade RemoteControlCode HdmiCEC
endif

if VUULTIMO
SUBDIRS += VuUnoFancontrol SatelliteEquipmentControl DiseqcTester CableScan FastScan FirmwareUpgrade RemoteControlCode HdmiCEC
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
SUBDIRS += FrontprocessorUpgrade NFIFlash SatelliteEquipmentControl DiseqcTester CableScan FastScan 
endif

if GIGABLUE
SUBDIRS += GBVFD SatelliteEquipmentControl DiseqcTester FastScan HdmiCEC
endif

install_PYTHON =	\
	__init__.py
