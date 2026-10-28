noinst_LIBRARIES += gdi/libenigma_gdi.a

gdi_libenigma_gdi_a_CXXFLAGS = -O3 $(LIBSDL_CFLAGS) $(EGL_CFLAGS) $(GLES2_CFLAGS) $(NXPL_CFLAGS) $(VUPL_CFLAGS) $(V3DPLATFORM_CFLAGS)

gdi_libenigma_gdi_a_SOURCES = \
	gdi/accel.cpp \
	gdi/bcm.cpp \
	gdi/compositing.cpp \
	gdi/drawing.cpp \
	gdi/epng.cpp \
	gdi/erect.cpp \
	gdi/dreamge2d.cpp \
	gdi/fb.cpp \
	gdi/font.cpp \
	gdi/font_arabic.cpp \
	gdi/gfont.cpp \
	gdi/gfont_atlas.cpp \
	gdi/glcddc.cpp \
	gdi/gmaindc.cpp \
	gdi/gpixmap.cpp \
	gdi/grc.cpp \
	gdi/lcd.cpp \
	gdi/picexif.cpp \
	gdi/picload.cpp \
	gdi/pixmapcache.cpp \
	gdi/region.cpp \
	gdi/spinner.cpp

gdiincludedir = $(pkgincludedir)/lib/gdi
gdiinclude_HEADERS = \
	gdi/accel.h \
	gdi/compositing.h \
	gdi/drawing.h \
	gdi/epng.h \
	gdi/epoint.h \
	gdi/erect.h \
	gdi/esize.h \
	gdi/fb.h \
	gdi/font.h \
	gdi/gfont.h \
	gdi/gfont_atlas.h \
	gdi/glcddc.h \
	gdi/gpixmap.h \
	gdi/grc.h \
	gdi/lcd.h \
	gdi/picexif.h \
	gdi/picload.h \
	gdi/pixmapcache.h \
	gdi/region.h \
	gdi/spinner.h


if HAVE_EGL
gdi_libenigma_gdi_a_SOURCES += \
	gdi/egl/egl_config.cpp \
	gdi/egl/egl_init.cpp \
	gdi/egl/shader/gadvanced_shader.cpp \
	gdi/egl/shader/gshader.cpp \
	gdi/egl/shader/gtext_shader.cpp \
	gdi/egl/shader/gtexture_shader.cpp \
	gdi/egl/gegldc.cpp \
	gdi/egl/gles_version.cpp \
	gdi/egl/gtexture_manager.cpp
gdiinclude_HEADERS += \
	gdi/egl/egl_config.h \
	gdi/egl/inative_window_provider.h \
	gdi/egl/shader/gadvanced_shader.h \
	gdi/egl/shader/gshader.h \
	gdi/egl/shader/gtext_shader.h \
	gdi/egl/shader/gtexture_shader.h \
	gdi/egl/gegldc.h \
	gdi/egl/gles_version.h \
	gdi/egl/gtexture_manager.h

if DREAMNEXTGEN
gdi_libenigma_gdi_a_SOURCES += \
	gdi/egl/platform/amlogic/amlogic_fb_output.cpp \
	gdi/egl/platform/amlogic/amlogic_window_provider.cpp
gdiinclude_HEADERS += \
	gdi/egl/platform/amlogic/amlogic_fb_output.h \
	gdi/egl/platform/amlogic/amlogic_window_provider.h
endif

if HAVE_VUPLUS_EGL
gdi_libenigma_gdi_a_SOURCES += \
	gdi/egl/platform/vuplus/vuplus_window_provider.cpp
gdiinclude_HEADERS += \
	gdi/egl/platform/vuplus/vuplus_window_provider.h
endif

if HAVE_VUPLUS_MIPSEL_EGL
gdi_libenigma_gdi_a_SOURCES += \
	gdi/egl/platform/vuplus_mips/vuplus_mips_window_provider.cpp
gdiinclude_HEADERS += \
	gdi/egl/platform/vuplus_mips/vuplus_mips_window_provider.h
endif

if HAVE_NXPL_EGL
gdi_libenigma_gdi_a_SOURCES += \
	gdi/egl/platform/nxpl/nxpl_window_provider.cpp
gdiinclude_HEADERS += \
	gdi/egl/platform/nxpl/nxpl_window_provider.h
endif

if HAVE_V3DPLATFORM_EGL
gdi_libenigma_gdi_a_SOURCES += \
	gdi/egl/platform/v3dplatform/v3dplatform_window_provider.cpp
gdiinclude_HEADERS += \
	gdi/egl/platform/v3dplatform/v3dplatform_window_provider.h
endif

if HAVE_HISILICON_EGL
gdi_libenigma_gdi_a_SOURCES += \
	gdi/egl/platform/hisilicon/hisilicon_window_provider.cpp
gdiinclude_HEADERS += \
	gdi/egl/platform/hisilicon/hisilicon_window_provider.h
endif

if HAVE_DREAMBCM_EGL
gdi_libenigma_gdi_a_SOURCES += \
	gdi/egl/platform/dreambcm/dreambcm_window_provider.cpp
gdiinclude_HEADERS += \
	gdi/egl/platform/dreambcm/dreambcm_window_provider.h
endif
endif


if HAVE_LIBSDL
gdi_libenigma_gdi_a_SOURCES += \
	gdi/sdl.cpp \
	gdi/sdl.h
else
gdi_libenigma_gdi_a_SOURCES += \
	gdi/gfbdc.cpp \
	gdi/gfbdc.h
endif

if LCD_FRAMEBUFFER_MODE
gdi_libenigma_gdi_a_SOURCES += \
	gdi/fblcd.cpp \
	gdi/fblcd.h
endif
