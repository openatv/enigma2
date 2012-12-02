installdir = $(pkglibdir)/python/Plugins/SystemPlugins

SUBDIRS = PositionerSetup Satfinder SoftwareManager \
	Videomode VideoTune Hotplug FastScan CableScan \
	DefaultServicesScanner CommonInterfaceAssignment \
	VideoEnhancement WirelessLan NetworkWizard VideoClippingSetup \
	SatelliteEquipmentControl DiseqcTester HdmiCEC

if DREAMBOX
SUBDIRS += FrontprocessorUpgrade NFIFlash
endif

install_PYTHON =	\
	__init__.py
