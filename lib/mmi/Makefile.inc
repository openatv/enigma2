noinst_LIBRARIES += mmi/libenigma_mmi.a

mmi_libenigma_mmi_a_SOURCES = \
	mmi/mmi_ui.cpp

mmiincludedir = $(pkgincludedir)/lib/mmi
mmiinclude_HEADERS = \
	mmi/mmi_ui.h
