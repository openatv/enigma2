AC_INIT(tuxbox-enigma,0.0.1)
AM_INIT_AUTOMAKE(tuxbox-enigma,0.0.1)

TUXBOX_APPS
TUXBOX_APPS_DIRECTORY

AC_PROG_CC
AC_PROG_CXX
AC_PROG_RANLIB

AC_ARG_WITH(libsdl,
	AC_HELP_STRING([--with-libsdl], [use sdl, yes or no]),
	[[withsdl=$withval]],
	[[withsdl=yes]]
)

AM_PATH_PYTHON(2.3)
AC_PYTHON_DEVEL

TUXBOX_APPS_DVB

TUXBOX_APPS_LIB_CONFIG(FREETYPE,freetype-config)
TUXBOX_APPS_LIB_PKGCONFIG(FRIBIDI,fribidi)
TUXBOX_APPS_LIB_PKGCONFIG(ID3TAG,id3tag)
TUXBOX_APPS_LIB_PKGCONFIG(MAD,mad)
#TUXBOX_APPS_LIB_PKGCONFIG(PLUGINS,tuxbox-plugins)
TUXBOX_APPS_LIB_PKGCONFIG(PNG,libpng)
TUXBOX_APPS_LIB_PKGCONFIG(SIGC,sigc++-1.2)
TUXBOX_APPS_LIB_PKGCONFIG(DVBSI,libdvbsi++)

if test "$withsdl" = "yes" ; then
	TUXBOX_APPS_LIB_CONFIG(SDL,sdl-config)
	AC_DEFINE_UNQUOTED([WITH_SDL],[$withsdl],[With SDL])
fi

CPPFLAGS="$CPPFLAGS "'-I$(top_srcdir)'
CPPFLAGS="$CPPFLAGS -D_REENTRANT $PYTHON_CPPFLAGS $MD5SUM_CFLAGS $FREETYPE_CFLAGS $FRIBIDI_CFLAGS $ID3TAG_CFLAGS $MAD_CFLAGS $PLUGINS_CFLAGS $PNG_CFLAGS $SDL_CFLAGS $SIGC_CFLAGS $XMLTREE_CFLAGS $DVBSI_CFLAGS"
CXXFLAGS="$CXXFLAGS -fno-rtti -fno-exceptions -Wall"
LDFLAGS="$LDFLAGS -pthread $PYTHON_LDFLAGS $SDL_LDFLAGS"

TUXBOX_APPS_GETTEXT

AC_OUTPUT([
Makefile
data/Makefile
data/fonts/Makefile
data/countries/Makefile
data/defaults/Makefile
data/extensions/Makefile
lib/Makefile
lib/actions/Makefile
lib/base/Makefile
lib/driver/Makefile
lib/dvb/Makefile
lib/dvb_ci/Makefile
lib/gdi/Makefile
lib/gui/Makefile
lib/nav/Makefile
lib/python/Makefile
lib/python/Components/Makefile
lib/python/Screens/Makefile
lib/python/Plugins/Makefile
lib/python/Plugins/SystemPlugins/Makefile
lib/python/Plugins/SystemPlugins/SoftwareUpdate/Makefile
lib/python/Plugins/SystemPlugins/OldSoftwareUpdate/Makefile
lib/python/Plugins/SystemPlugins/FrontprocessorUpgrade/Makefile
lib/python/Plugins/DemoPlugins/Makefile
lib/python/Plugins/DemoPlugins/TestPlugin/Makefile
lib/python/Plugins/Extensions/Makefile
lib/python/Plugins/Extensions/TuxboxPlugins/Makefile
lib/python/Plugins/Extensions/WebInterface/Makefile
lib/python/Plugins/Extensions/FileManager/Makefile
lib/python/Plugins/Extensions/CutListEditor/Makefile
lib/python/Tools/Makefile
lib/service/Makefile
lib/components/Makefile
po/Makefile
main/Makefile
])
