installdir = $(pkglibdir)/python/Plugins/SystemPlugins

SUBDIRS = PositionerSetup Satfinder \
	Videomode VideoTune Hotplug HdmiCEC \
	DefaultServicesScanner CommonInterfaceAssignment \
	VideoEnhancement WirelessLan NetworkWizard SoftwareManager SkinSelector

if XTREND
SUBDIRS += SatelliteEquipmentControl DiseqcTester FastScan OSD3DSetup OSDPositionSetup FanSetupXtrend choiceRC
endif

if VUUNO
SUBDIRS += SatelliteEquipmentControl DiseqcTester CableScan FastScan FPGAUpgrade
endif

if VUULTIMO
SUBDIRS += SatelliteEquipmentControl DiseqcTester CableScan FastScan FPGAUpgrade
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
