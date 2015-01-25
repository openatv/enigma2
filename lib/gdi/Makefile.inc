noinst_LIBRARIES += gdi/libenigma_gdi.a

gdi_libenigma_gdi_CXXFLAGS = $(LIBSDL_CFLAGS)

gdi_libenigma_gdi_a_SOURCES = \
	gdi/accel.cpp \
	gdi/bcm.cpp \
	gdi/compositing.cpp \
	gdi/epng.cpp \
	gdi/erect.cpp \
	gdi/fb.cpp \
	gdi/fblcd.cpp \
	gdi/font.cpp \
	gdi/font_arabic.cpp \
	gdi/gfont.cpp \
	gdi/glcddc.cpp \
	gdi/gmaindc.cpp \
	gdi/gpixmap.cpp \
	gdi/grc.cpp \
	gdi/lcd.cpp \
	gdi/picexif.cpp \
	gdi/picload.cpp \
	gdi/region.cpp

gdiincludedir = $(pkgincludedir)/lib/gdi
gdiinclude_HEADERS = \
	gdi/accel.h \
	gdi/compositing.h \
	gdi/epng.h \
	gdi/epoint.h \
	gdi/erect.h \
	gdi/esize.h \
	gdi/fb.h \
	gdi/fblcd.h \
	gdi/font.h \
	gdi/gfont.h \
	gdi/glcddc.h \
	gdi/gpixmap.h \
	gdi/grc.h \
	gdi/lcd.h \
	gdi/picexif.h \
	gdi/picload.h \
	gdi/region.h

if HAVE_LIBSDL
gdi_libenigma_gdi_a_SOURCES += \
	gdi/sdl.cpp \
	gdi/sdl.h
else
gdi_libenigma_gdi_a_SOURCES += \
	gdi/gfbdc.cpp \
	gdi/gfbdc.h
endif
