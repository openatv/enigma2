AC_INIT(tuxbox-enigma,0.0.1)
AM_INIT_AUTOMAKE(tuxbox-enigma,0.0.1)

TUXBOX_APPS
TUXBOX_APPS_DIRECTORY

AC_PROG_CC
AC_PROG_CXX
AC_PROG_RANLIB

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

# fixme: decent python stuff
CPPFLAGS="$CPPFLAGS $FREETYPE_CFLAGS $FRIBIDI_CFLAGS $ID3TAG_CFLAGS $MAD_CFLAGS $PLUGINS_CFLAGS $PNG_CFLAGS $SIGC_CFLAGS $XMLTREE_CFLAGS -I/usr/include/python2.3"
CXXFLAGS="$CXXFLAGS -fno-rtti -fno-exceptions -Wall"

TUXBOX_APPS_GETTEXT

AC_OUTPUT([
Makefile
lib/Makefile
lib/actions/Makefile
lib/base/Makefile
lib/driver/Makefile
lib/dvb/Makefile
lib/dvb_si/Makefile
lib/gdi/Makefile
lib/gui/Makefile
lib/nav/Makefile
lib/network/Makefile
lib/python/Makefile
lib/service/Makefile
lib/components/Makefile
main/Makefile
])
