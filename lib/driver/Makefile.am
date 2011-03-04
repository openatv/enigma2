AM_CPPFLAGS = \
	-I$(top_srcdir) \
	-I$(top_srcdir)/include \
	-include Python.h \
	-include $(top_builddir)/enigma2_config.h

AM_CXXFLAGS = \
	$(LIBSDL_CFLAGS)

noinst_LIBRARIES = libenigma_driver.a

libenigma_driver_a_SOURCES = \
	avswitch.cpp \
	etimezone.cpp \
	misc_options.cpp \
	rc.cpp \
	rcconsole.cpp \
	rcinput.cpp \
	rfmod.cpp \
	hdmi_cec.cpp

driverincludedir = $(pkgincludedir)/lib/driver
driverinclude_HEADERS = \
	avswitch.h \
	etimezone.h \
	input_fake.h \
	misc_options.h \
	rc.h \
	rcconsole.h \
	rcdbox.h \
	rcdreambox2.h \
	rcinput.h \
	rfmod.h \
	hdmi_cec.h

if HAVE_LIBSDL
libenigma_driver_a_SOURCES += \
	rcsdl.cpp \
	rcsdl.h
endif
