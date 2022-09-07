installdir = $(pkglibdir)/python/Plugins/SystemPlugins

SUBDIRS = PositionerSetup Satfinder SoftwareManager \
	VideoTune Hotplug CableScan \
	DefaultServicesScanner CommonInterfaceAssignment \
	VideoEnhancement WirelessLan NetworkWizard VideoClippingSetup \
	SatelliteEquipmentControl DiseqcTester FastScan LCNScanner IceTV \
	FastChannelChange vps

if HAVE_LIBVUGLES2
SUBDIRS += AnimationSetup
endif

if HAVE_OSDANIMATION
SUBDIRS += AnimationSetup
endif

if DREAMBOX
SUBDIRS += FrontprocessorUpgrade
endif

if DM900
SUBDIRS += FSBLUpdater
endif

if DM920
SUBDIRS += FSBLUpdater
endif

if HAVE_FCC
SUBDIRS += FastChannelChange
endif

install_PYTHON = __init__.py
