installdir = $(pkglibdir)/python/Plugins/SystemPlugins

SUBDIRS = PositionerSetup Satfinder \
	Videomode VideoTune Hotplug HdmiCEC \
	DefaultServicesScanner CommonInterfaceAssignment \
	VideoEnhancement WirelessLan NetworkWizard

if XTREND
SUBDIRS += SatelliteEquipmentControl DiseqcTester FastScan OSD3DSetup FanSetupXtrend Blindscan
endif

if VUUNO
SUBDIRS += SatelliteEquipmentControl DiseqcTester CableScan FastScan FPGAUpgrade Blindscan
endif

if VUULTIMO
SUBDIRS += SatelliteEquipmentControl DiseqcTester CableScan FastScan FPGAUpgrade Blindscan
endif

if VUDUO
SUBDIRS += FanSetupVuPlus
endif

if HAVE_TEMPFANCONTROL
SUBDIRS += TempFanControl
endif

if DREAMBOX
SUBDIRS += FrontprocessorUpgrade NFIFlash SatelliteEquipmentControl DiseqcTester CableScan FastScan OSD3DSetup
endif

install_PYTHON =	\
	__init__.py
