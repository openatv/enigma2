AM_CPPFLAGS = \
	-I$(top_srcdir) \
	-I$(top_srcdir)/include \
	-include Python.h \
	-include $(top_builddir)/enigma2_config.h

AM_CXXFLAGS = \
	$(LIBSDL_CFLAGS)

noinst_LTLIBRARIES = libenigma_gdi.la

libenigma_gdi_la_SOURCES = \
	accel.cpp \
	accel.h \
	bcm.cpp \
	compositing.cpp \
	compositing.h \
	epng.cpp \
	epng.h \
	epoint.h \
	erect.cpp \
	erect.h \
	esize.h \
	fb.cpp \
	fb.h \
	font.cpp \
	font.h \
	font_arabic.cpp \
	gfbdc.cpp \
	gfbdc.h \
	gfont.cpp \
	gfont.h \
	glcddc.cpp \
	glcddc.h \
	gpixmap.cpp \
	gpixmap.h \
	grc.cpp \
	grc.h \
	lcd.cpp \
	lcd.h \
	picexif.cpp \
	picexif.h \
	picload.cpp \
	picload.h \
	region.cpp \
	region.h

if HAVE_LIBSDL
libenigma_gdi_la_SOURCES += \
	sdl.cpp \
	sdl.h
endif
