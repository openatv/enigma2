AC_INIT(tuxbox-enigma,0.0.1)
AM_INIT_AUTOMAKE(tuxbox-enigma,0.0.1)

TUXBOX_APPS
TUXBOX_APPS_DIRECTORY

AC_PROG_CC
AC_PROG_CXX
AC_PROG_RANLIB

AC_ARG_WITH(pythonincdir,
	[  --with-pythonincdir=NAME dir [[...]]],
	[PYTHON_INCDIR="$withval"],[PYTHON_INCDIR="/usr/include/python2.4"])
AC_SUBST(PYTHON_INCDIR)

AC_ARG_WITH(libsdl,
	AC_HELP_STRING([--with-libsdl], [use sdl, yes or no]),
	[[withsdl=$withval]],
	[[withsdl=yes]]
)
		
TUXBOX_APPS_DVB
#TUXBOX_APPS_DRIVER

TUXBOX_APPS_LIB_CONFIG(FREETYPE,freetype-config)
#TUXBOX_APPS_LIB_PKGCONFIG(FRIBIDI,fribidi)
TUXBOX_APPS_LIB_PKGCONFIG(ID3TAG,id3tag)
TUXBOX_APPS_LIB_PKGCONFIG(MAD,mad)
#TUXBOX_APPS_LIB_PKGCONFIG(PLUGINS,tuxbox-plugins)
TUXBOX_APPS_LIB_PKGCONFIG(PNG,libpng)
TUXBOX_APPS_LIB_PKGCONFIG(SIGC,sigc++-1.2)
#TUXBOX_APPS_LIB_PKGCONFIG(XMLTREE,tuxbox-xmltree)
if test "$withsdl" = "yes" ; then
	TUXBOX_APPS_LIB_CONFIG(SDL,sdl-config)
	AC_DEFINE_UNQUOTED([WITH_SDL],[$withsdl],[With SDL])
fi

# fixme: decent python stuff
CPPFLAGS="$CPPFLAGS $MD5SUM_CFLAGS $FREETYPE_CFLAGS $FRIBIDI_CFLAGS $ID3TAG_CFLAGS $MAD_CFLAGS $PLUGINS_CFLAGS $PNG_CFLAGS $SIGC_CFLAGS $XMLTREE_CFLAGS -I$PYTHON_INCDIR -DHAVE_CPP_FILT -DMEMLEAK_CHECK"
CXXFLAGS="$CXXFLAGS -fno-rtti -fno-exceptions -Wall"
LDFLAGS="$LDFLAGS -rdynamic"

TUXBOX_APPS_GETTEXT

AC_OUTPUT([
Makefile
data/Makefile
lib/Makefile
lib/actions/Makefile
lib/base/Makefile
lib/driver/Makefile
lib/dvb/Makefile
lib/dvb_ci/Makefile
lib/dvb_si/Makefile
lib/gdi/Makefile
lib/gui/Makefile
lib/nav/Makefile
lib/network/Makefile
lib/python/Makefile
lib/python/Components/Makefile
lib/python/Screens/Makefile
lib/python/Tools/Makefile
lib/service/Makefile
lib/components/Makefile
main/Makefile
])
