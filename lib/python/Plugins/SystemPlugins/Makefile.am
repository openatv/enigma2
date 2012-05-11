installdir = $(pkglibdir)/python/Plugins/SystemPlugins

SUBDIRS = PositionerSetup Satfinder FastScan \
	Videomode VideoTune Hotplug HdmiCEC \
	DefaultServicesScanner CommonInterfaceAssignment \
	VideoEnhancement WirelessLan NetworkWizard SABnzbdSetup

if XTREND
SUBDIRS += XtrendFancontrol SatelliteEquipmentControl DiseqcTester Blindscan
endif

if MARA
SUBDIRS += SatelliteEquipmentControl DiseqcTester Blindscan
endif

if VUUNO
SUBDIRS += VuUnoFanControl SatelliteEquipmentControl DiseqcTester CableScan FirmwareUpgrade Blindscan RemoteControlCode
endif

if VUULTIMO
SUBDIRS += VuUnoFanControl SatelliteEquipmentControl DiseqcTester CableScan FirmwareUpgrade Blindscan RemoteControlCode
endif

if VUDUO
SUBDIRS += VuDuoFanControl
endif

if TMTWIN
SUBDIRS += TmTwinFanControl
endif

if HAVE_TEMPFANCONTROL
SUBDIRS += TempFanControl
endif

if DREAMBOX
SUBDIRS += FrontprocessorUpgrade NFIFlash SatelliteEquipmentControl DiseqcTester CableScan
endif

install_PYTHON =	\
	__init__.py
