AM_CPPFLAGS = \
	-I$(top_srcdir) \
	-I$(top_srcdir)/include \
	-include Python.h

noinst_LTLIBRARIES = libenigma_gdi.la

libenigma_gdi_la_SOURCES = \
	region.cpp grc.cpp epng.cpp erect.cpp fb.cpp font.cpp font_arabic.cpp gfbdc.cpp  \
	glcddc.cpp gpixmap.cpp lcd.cpp gfont.cpp accel.cpp picload.cpp picexif.cpp \
	compositing.cpp bcm.cpp

if WITH_SDL
libenigma_gdi_la_SOURCES += sdl.cpp
endif
