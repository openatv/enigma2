installdir = $(pkglibdir)/python/Plugins/SystemPlugins

SUBDIRS = PositionerSetup Satfinder SoftwareManager SkinSelector \
	Videomode VideoTune Hotplug HdmiCEC \
	DefaultServicesScanner CommonInterfaceAssignment \
	VideoEnhancement WirelessLan NetworkWizard

if XTREND
<<<<<<< HEAD
SUBDIRS += SatelliteEquipmentControl DiseqcTester choiceRC FastScan FanSetupXtrend Blindscan
=======
SUBDIRS += XtrendFancontrol SatelliteEquipmentControl DiseqcTester FastScan Blindscan
>>>>>>> 168da7001e1f7050dd3c4efef7c00c00932751b7
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
