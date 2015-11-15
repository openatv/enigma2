installdir = $(pkglibdir)/python/Plugins/SystemPlugins

SUBDIRS = PositionerSetup Satfinder SoftwareManager \
	VideoTune Hotplug CableScan \
	DefaultServicesScanner CommonInterfaceAssignment \
	VideoEnhancement WirelessLan NetworkWizard VideoClippingSetup \
	SatelliteEquipmentControl DiseqcTester HdmiCEC FastScan LCNScanner

if HAVE_LIBVUGLES2
SUBDIRS += AnimationSetup
endif

if VUSOLO4K
SUBDIRS += FastZapSupport
endif

if DREAMBOX
SUBDIRS += FrontprocessorUpgrade NFIFlash
endif

install_PYTHON = __init__.py
