installdir = $(pkglibdir)/python/Plugins/SystemPlugins

SUBDIRS = SoftwareManager PositionerSetup Satfinder \
	Videomode VideoTune Hotplug \
	DefaultServicesScanner CommonInterfaceAssignment \
	VideoEnhancement WirelessLan NetworkWizard

if XTREND
SUBDIRS += SatelliteEquipmentControl DiseqcTester FastScan OSD3DSetup OSDPositionSetup FanSetupXtrend
endif

if VUUNO
SUBDIRS += SatelliteEquipmentControl DiseqcTester CableScan FastScan OSD3DSetup OSDPositionSetup FPGAUpgrade
endif

if VUULTIMO
SUBDIRS += SatelliteEquipmentControl DiseqcTester CableScan FastScan OSD3DSetup OSDPositionSetup FPGAUpgrade
endif

if VUDUO
SUBDIRS += FanSetupVuPlus
endif

if ET9000
SUBDIRS += VFDSetupXtrend
endif

if HAVE_TEMPFANCONTROL
SUBDIRS += TempFanControl
endif

if DREAMBOX
SUBDIRS += FrontprocessorUpgrade NFIFlash SatelliteEquipmentControl DiseqcTester CableScan FastScan OSDPositionSetup OSD3DSetup
endif

install_PYTHON =	\
	__init__.py
