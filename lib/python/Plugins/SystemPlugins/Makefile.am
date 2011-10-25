installdir = $(pkglibdir)/python/Plugins/SystemPlugins

SUBDIRS = PositionerSetup Satfinder SoftwareManager SkinSelector \
	Videomode VideoTune Hotplug HdmiCEC \
	DefaultServicesScanner CommonInterfaceAssignment \
	VideoEnhancement WirelessLan NetworkWizard

if XTREND
SUBDIRS += SatelliteEquipmentControl DiseqcTester choiceRC FastScan XtrendFancontrol Blindscan
endif

if VUUNO
SUBDIRS += VuUnoFancontrol SatelliteEquipmentControl DiseqcTester CableScan FastScan FPGAUpgrade Blindscan RemoteControlCode
endif

if VUULTIMO
SUBDIRS += VuUnoFancontrol SatelliteEquipmentControl DiseqcTester CableScan FastScan FPGAUpgrade Blindscan RemoteControlCode
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
