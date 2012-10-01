noinst_LIBRARIES += gui/libenigma_gui.a

gui_libenigma_gui_a_SOURCES = \
	gui/ebutton.cpp \
	gui/ecanvas.cpp \
	gui/einput.cpp \
	gui/egauge.cpp \
	gui/einputnumber.cpp \
	gui/einputstring.cpp \
	gui/elabel.cpp \
	gui/elistbox.cpp \
	gui/elistboxcontent.cpp \
	gui/epixmap.cpp \
	gui/epositiongauge.cpp \
	gui/eslider.cpp \
	gui/esubtitle.cpp \
	gui/evideo.cpp \
	gui/ewidget.cpp \
	gui/ewidgetanimation.cpp \
	gui/ewidgetdesktop.cpp \
	gui/ewindow.cpp \
	gui/ewindowstyle.cpp \
	gui/ewindowstyleskinned.cpp

guiincludedir = $(pkgincludedir)/lib/gui
guiinclude_HEADERS = \
	gui/ebutton.h \
	gui/ecanvas.h \
	gui/einput.h \
	gui/egauge.h \
	gui/einputnumber.h \
	gui/einputstring.h \
	gui/elabel.h \
	gui/elistbox.h \
	gui/elistboxcontent.h \
	gui/epixmap.h \
	gui/epositiongauge.h \
	gui/eslider.h \
	gui/esubtitle.h \
	gui/evideo.h \
	gui/ewidget.h \
	gui/ewidgetanimation.h \
	gui/ewidgetdesktop.h \
	gui/ewindow.h \
	gui/ewindowstyle.h \
	gui/ewindowstyleskinned.h
