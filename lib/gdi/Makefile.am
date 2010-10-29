AM_CPPFLAGS = \
	-I$(top_srcdir) \
	-I$(top_srcdir)/include \
	-include Python.h \
	-include $(top_builddir)/enigma2_config.h

AM_CXXFLAGS = \
	$(LIBSDL_CFLAGS)

noinst_LIBRARIES = libenigma_gdi.a

libenigma_gdi_a_SOURCES = \
	accel.cpp \
	bcm.cpp \
	compositing.cpp \
	epng.cpp \
	erect.cpp \
	fb.cpp \
	font.cpp \
	font_arabic.cpp \
	gfbdc.cpp \
	gfont.cpp \
	glcddc.cpp \
	gpixmap.cpp \
	grc.cpp \
	lcd.cpp \
	picexif.cpp \
	picload.cpp \
	region.cpp

gdiincludedir = $(pkgincludedir)/lib/gdi
gdiinclude_HEADERS = \
	accel.h \
	compositing.h \
	epng.h \
	epoint.h \
	erect.h \
	esize.h \
	fb.h \
	font.h \
	gfbdc.h \
	gfont.h \
	glcddc.h \
	gpixmap.h \
	grc.h \
	lcd.h \
	picexif.h \
	picload.h \
	region.h

if HAVE_LIBSDL
libenigma_gdi_a_SOURCES += \
	sdl.cpp
gdiinclude_HEADERS += \
	sdl.h
endif
