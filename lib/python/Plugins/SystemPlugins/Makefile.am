installdir = $(pkglibdir)/python/Plugins/SystemPlugins

SUBDIRS = PositionerSetup Satfinder \
	VideoTune Hotplug CableScan \
	DefaultServicesScanner CommonInterfaceAssignment \
	VideoClippingSetup \
	SatelliteEquipmentControl DiseqcTester FastScan LCNScanner IceTV \
	FastChannelChange vps

if DREAMBOX
SUBDIRS += FrontprocessorUpgrade
endif

if DREAMNEXTGEN
SUBDIRS += AmlFRQ VideoEnhancementAML
else
SUBDIRS += VideoEnhancement
endif

if DM7252S
SUBDIRS += FSBLUpdater
endif

if HAVE_FCC
SUBDIRS += FastChannelChange
endif

install_PYTHON = __init__.py
