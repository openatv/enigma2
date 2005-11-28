AC_DEFUN(TUXBOX_APPS,[
AM_CONFIG_HEADER(config.h)
AM_MAINTAINER_MODE

INSTALL="$INSTALL -p"

AC_GNU_SOURCE
AC_SYS_LARGEFILE

AC_ARG_WITH(target,
	[  --with-target=TARGET    target for compilation [[native,cdk]]],
	[TARGET="$withval"],[TARGET="native"])

AC_ARG_WITH(targetprefix,
	[  --with-targetprefix=PATH  prefix relative to target root (only applicable in cdk mode)],
	[targetprefix="$withval"],[targetprefix="NONE"])

AC_ARG_WITH(debug,
	[  --without-debug         disable debugging code],
	[DEBUG="$withval"],[DEBUG="yes"])

if test "$DEBUG" = "yes"; then
	DEBUG_CFLAGS="-g3 -ggdb"
	AC_DEFINE(DEBUG,1,[Enable debug messages])
fi

AC_MSG_CHECKING(target)

if test "$TARGET" = "native"; then
	AC_MSG_RESULT(native)

	if test "$CFLAGS" = "" -a "$CXXFLAGS" = ""; then
		CFLAGS="-Wall -O2 -pipe $DEBUG_CFLAGS"
		CXXFLAGS="-Wall -O2 -pipe $DEBUG_CFLAGS"
	fi
	if test "$prefix" = "NONE"; then
		prefix=/usr/local
	fi
	targetprefix=$prefix
elif test "$TARGET" = "cdk"; then
	AC_MSG_RESULT(cdk)

	if test "$CC" = "" -a "$CXX" = ""; then
		CC=powerpc-tuxbox-linux-gnu-gcc CXX=powerpc-tuxbox-linux-gnu-g++
	fi
	if test "$CFLAGS" = "" -a "$CXXFLAGS" = ""; then
		CFLAGS="-Wall -Os -mcpu=823 -pipe $DEBUG_CFLAGS"
		CXXFLAGS="-Wall -Os -mcpu=823 -pipe $DEBUG_CFLAGS"
	fi
	if test "$prefix" = "NONE"; then
		AC_MSG_ERROR(invalid prefix, you need to specify one in cdk mode)
	fi
	if test "$targetprefix" = "NONE"; then
		targetprefix=""
	fi
	if test "$host_alias" = ""; then
		cross_compiling=yes
		host_alias=powerpc-tuxbox-linux-gnu
	fi
else
	AC_MSG_RESULT(none)
	AC_MSG_ERROR([invalid target $TARGET, choose on from native,cdk]);
fi

AC_CANONICAL_BUILD
AC_CANONICAL_HOST

check_path () {
	return $(perl -e "if(\"$1\"=~m#^/usr/(local/)?bin#){print \"0\"}else{print \"1\";}")
}

])

AC_DEFUN(TUXBOX_APPS_DIRECTORY_ONE,[
AC_ARG_WITH($1,[  $6$7 [[PREFIX$4$5]]],[
	_$2=$withval
	if test "$TARGET" = "cdk"; then
		$2=`eval echo "${targetprefix}$withval"`
	else
		$2=$withval
	fi
],[
	$2="\${$3}$5"
	if test "$TARGET" = "cdk"; then
		_$2=`eval echo "${target$3}$5"`
	else
		_$2=`eval echo "${$3}$5"`
	fi
])

dnl automake <= 1.6 don't support this
dnl AC_SUBST($2)
AC_DEFINE_UNQUOTED($2,"$_$2",$7)
])

AC_DEFUN(TUXBOX_APPS_DIRECTORY,[
AC_REQUIRE([TUXBOX_APPS])

if test "$TARGET" = "cdk"; then
	datadir="\${prefix}/share"
	tuxboxdatadir="\${prefix}/share/tuxbox"
	zoneinfodir="\${datadir}/zoneinfo"
	sysconfdir="\${prefix}/etc"
	localstatedir="\${prefix}/var"
	localedir="\${prefix}/var"
	libdir="\${prefix}/lib"
	targetdatadir="\${targetprefix}/share"
	targetsysconfdir="\${targetprefix}/etc"
	targetlocalstatedir="\${targetprefix}/var"
	targetlibdir="\${targetprefix}/lib"
fi

TUXBOX_APPS_DIRECTORY_ONE(configdir,CONFIGDIR,sysconfdir,/etc,,
	[--with-configdir=PATH   ],[where to find the config files])

TUXBOX_APPS_DIRECTORY_ONE(datadir,DATADIR,datadir,/share,,
	[--with-datadir=PATH     ],[where to find data])

TUXBOX_APPS_DIRECTORY_ONE(localedir,LOCALEDIR,datadir,/share,/locale,
	[--with-localedir=PATH ],[where to find locales])

TUXBOX_APPS_DIRECTORY_ONE(fontdir,FONTDIR,datadir,/share,/fonts,
	[--with-fontdir=PATH     ],[where to find the fonts])

TUXBOX_APPS_DIRECTORY_ONE(gamesdir,GAMESDIR,localstatedir,/var,/tuxbox/games,
	[--with-gamesdir=PATH    ],[where games data is stored])

TUXBOX_APPS_DIRECTORY_ONE(libdir,LIBDIR,libdir,/lib,,
	[--with-libdir=PATH      ],[where to find the internal libs])

TUXBOX_APPS_DIRECTORY_ONE(plugindir,PLUGINDIR,libdir,/lib,/tuxbox/plugins,
	[--with-plugindir=PATH   ],[where to find the plugins])

TUXBOX_APPS_DIRECTORY_ONE(tuxboxdatadir,TUXBOXDATADIR,datadir,/share,,
	[--with-tuxboxdatadir=PATH],[where to find tuxbox data])

TUXBOX_APPS_DIRECTORY_ONE(zoneinfodir,ZONEINFODIR,datadir,/share,/zoneinfo,
	[--with-zoneinfodir=PATH ],[where to find zoneinfo db])
])

dnl automake <= 1.6 needs this specifications
AC_SUBST(CONFIGDIR)
AC_SUBST(DATADIR)
AC_SUBST(ZONEINFODIR)
AC_SUBST(FONTDIR)
AC_SUBST(GAMESDIR)
AC_SUBST(LIBDIR)
AC_SUBST(LOCALEDIR)
AC_SUBST(PLUGINDIR)
AC_SUBST(TUXBOXDATADIR)
dnl end workaround

AC_DEFUN(TUXBOX_APPS_ENDIAN,[
AC_CHECK_HEADERS(endian.h)
AC_C_BIGENDIAN
])

AC_DEFUN(TUXBOX_APPS_DRIVER,[
#AC_ARG_WITH(driver,
#	[  --with-driver=PATH      path for driver sources [[NONE]]],
#	[DRIVER="$withval"],[DRIVER=""])
#
#if test -d "$DRIVER/include"; then
#	AC_DEFINE(HAVE_DBOX2_DRIVER,1,[Define to 1 if you have the dbox2 driver sources])
#else
#	AC_MSG_ERROR([can't find driver sources])
#fi

#AC_SUBST(DRIVER)

#CPPFLAGS="$CPPFLAGS -I$DRIVER/include"
])

AC_DEFUN([TUXBOX_APPS_DVB],[
AC_ARG_WITH(dvbincludes,
	[  --with-dvbincludes=PATH  path for dvb includes [[NONE]]],
	[DVBINCLUDES="$withval"],[DVBINCLUDES=""])

if test "$DVBINCLUDES"; then
	CPPFLAGS="$CPPFLAGS -I$DVBINCLUDES"
fi

AC_CHECK_HEADERS(ost/dmx.h,[
	DVB_API_VERSION=1
	AC_MSG_NOTICE([found dvb version 1])
])

if test -z "$DVB_API_VERSION"; then
AC_CHECK_HEADERS(linux/dvb/version.h,[
	AC_LANG_PREPROC_REQUIRE()
	AC_REQUIRE([AC_PROG_EGREP])
	AC_LANG_CONFTEST([AC_LANG_SOURCE([[
#include <linux/dvb/version.h>
version DVB_API_VERSION
	]])])
	DVB_API_VERSION=`(eval "$ac_cpp conftest.$ac_ext") 2>&AS_MESSAGE_LOG_FD | $EGREP "^version" | sed "s,version\ ,,"`
	rm -f conftest*

	AC_MSG_NOTICE([found dvb version $DVB_API_VERSION])
])
fi

if test "$DVB_API_VERSION"; then
	AC_DEFINE(HAVE_DVB,1,[Define to 1 if you have the dvb includes])
	AC_DEFINE_UNQUOTED(HAVE_DVB_API_VERSION,$DVB_API_VERSION,[Define to the version of the dvb api])
else
	AC_MSG_ERROR([can't find dvb headers])
fi
])

AC_DEFUN(_TUXBOX_APPS_LIB_CONFIG,[
AC_PATH_PROG($1_CONFIG,$2,no)
if test "$$1_CONFIG" != "no"; then
	if test "$TARGET" = "cdk" && check_path "$$1_CONFIG"; then
		AC_MSG_$3([could not find a suitable version of $2]);
	else
		$1_CFLAGS=$($$1_CONFIG --cflags)
		$1_LIBS=$($$1_CONFIG --libs)
	fi
fi

AC_SUBST($1_CFLAGS)
AC_SUBST($1_LIBS)
])

AC_DEFUN(TUXBOX_APPS_LIB_CONFIG,[
_TUXBOX_APPS_LIB_CONFIG($1,$2,ERROR)
if test "$$1_CONFIG" = "no"; then
	AC_MSG_ERROR([could not find $2]);
fi
])

AC_DEFUN(TUXBOX_APPS_LIB_CONFIG_CHECK,[
_TUXBOX_APPS_LIB_CONFIG($1,$2,WARN)
])

AC_DEFUN(TUXBOX_APPS_PKGCONFIG,[
AC_PATH_PROG(PKG_CONFIG, pkg-config,no)
if test "$PKG_CONFIG" = "no" ; then
	AC_MSG_ERROR([could not find pkg-config]);
fi
])

AC_DEFUN(_TUXBOX_APPS_LIB_PKGCONFIG,[
PKG_CHECK_MODULES($1,$2)
AC_SUBST($1_CFLAGS)
AC_SUBST($1_LIBS)
])

AC_DEFUN(TUXBOX_APPS_LIB_PKGCONFIG,[
_TUXBOX_APPS_LIB_PKGCONFIG($1,$2)
if test -z "$$1_CFLAGS" ; then
	AC_MSG_ERROR([could not find package $2]);
fi
])

AC_DEFUN(TUXBOX_APPS_LIB_PKGCONFIG_CHECK,[
_TUXBOX_APPS_LIB_PKGCONFIG($1,$2)
])

AC_DEFUN(_TUXBOX_APPS_LIB_SYMBOL,[
AC_CHECK_LIB($2,$3,HAVE_$1="yes",HAVE_$1="no")
if test "$HAVE_$1" = "yes"; then
	$1_LIBS=-l$2
fi

AC_SUBST($1_LIBS)
])

AC_DEFUN(TUXBOX_APPS_LIB_SYMBOL,[
_TUXBOX_APPS_LIB_SYMBOL($1,$2,$3,ERROR)
if test "$HAVE_$1" = "no"; then
	AC_MSG_ERROR([could not find $2]);
fi
])

AC_DEFUN(TUXBOX_APPS_LIB_CONFIG_SYMBOL,[
_TUXBOX_APPS_LIB_SYMBOL($1,$2,$3,WARN)
])

AC_DEFUN(TUXBOX_APPS_GETTEXT,[
AM_PATH_PROG_WITH_TEST(MSGFMT, msgfmt,
	[$ac_dir/$ac_word --statistics /dev/null >/dev/null 2>&1 &&
	(if $ac_dir/$ac_word --statistics /dev/null 2>&1 >/dev/null | grep usage >/dev/null; then exit 1; else exit 0; fi)],
	:)
AC_PATH_PROG(GMSGFMT, gmsgfmt, $MSGFMT)

AM_PATH_PROG_WITH_TEST(XGETTEXT, xgettext,
	[$ac_dir/$ac_word --omit-header --copyright-holder= /dev/null >/dev/null 2>&1 &&
	(if $ac_dir/$ac_word --omit-header --copyright-holder= /dev/null 2>&1 >/dev/null | grep usage >/dev/null; then exit 1; else exit 0; fi)],
	:)

AM_PATH_PROG_WITH_TEST(MSGMERGE, msgmerge,[$ac_dir/$ac_word --update -q /dev/null /dev/null >/dev/null 2>&1],:)

AC_MSG_CHECKING([whether NLS is requested])
AC_ARG_ENABLE(nls,
	[  --disable-nls           do not use Native Language Support],
	USE_NLS=$enableval, USE_NLS=yes)
AC_MSG_RESULT($USE_NLS)
AC_SUBST(USE_NLS)

if test "$USE_NLS" = "yes"; then
	AC_CACHE_CHECK([for GNU gettext in libc], gt_cv_func_gnugettext_libc,[
		AC_TRY_LINK([
			#include <libintl.h>
			#ifndef __GNU_GETTEXT_SUPPORTED_REVISION
			#define __GNU_GETTEXT_SUPPORTED_REVISION(major) ((major) == 0 ? 0 : -1)
			#endif
			extern int _nl_msg_cat_cntr;
			extern int *_nl_domain_bindings;
			],[
			bindtextdomain ("", "");
			return (int) gettext ("") + _nl_msg_cat_cntr + *_nl_domain_bindings;
			], gt_cv_func_gnugettext_libc=yes, gt_cv_func_gnugettext_libc=no
		)]
	)

	if test "$gt_cv_func_gnugettext_libc" = "yes"; then
		AC_DEFINE(ENABLE_NLS, 1, [Define to 1 if translation of program messages to the user's native language is requested.])
		gt_use_preinstalled_gnugettext=yes
	else
		USE_NLS=no
	fi
fi

if test -f "$srcdir/po/LINGUAS"; then
	ALL_LINGUAS=$(sed -e "/^#/d" "$srcdir/po/LINGUAS")
fi

POFILES=
GMOFILES=
UPDATEPOFILES=
DUMMYPOFILES=
for lang in $ALL_LINGUAS; do
	POFILES="$POFILES $srcdirpre$lang.po"
	GMOFILES="$GMOFILES $srcdirpre$lang.gmo"
	UPDATEPOFILES="$UPDATEPOFILES $lang.po-update"
	DUMMYPOFILES="$DUMMYPOFILES $lang.nop"
done
INST_LINGUAS=
if test -n "$ALL_LINGUAS"; then
	for presentlang in $ALL_LINGUAS; do
		useit=no
		if test -n "$LINGUAS"; then
			desiredlanguages="$LINGUAS"
		else
			desiredlanguages="$ALL_LINGUAS"
		fi
		for desiredlang in $desiredlanguages; do
			case "$desiredlang" in
				"$presentlang"*) useit=yes;;
			esac
		done
		if test $useit = yes; then
			INST_LINGUAS="$INST_LINGUAS $presentlang"
		fi
	done
fi
CATALOGS=
if test -n "$INST_LINGUAS"; then
	for lang in $INST_LINGUAS; do
		CATALOGS="$CATALOGS $lang.gmo"
	done
fi
AC_SUBST(POFILES)
AC_SUBST(GMOFILES)
AC_SUBST(UPDATEPOFILES)
AC_SUBST(DUMMYPOFILES)
AC_SUBST(CATALOGS)
])

dnl backward compatiblity
AC_DEFUN([AC_GNU_SOURCE],
[AH_VERBATIM([_GNU_SOURCE],
[/* Enable GNU extensions on systems that have them.  */
#ifndef _GNU_SOURCE
# undef _GNU_SOURCE
#endif])dnl
AC_BEFORE([$0], [AC_COMPILE_IFELSE])dnl
AC_BEFORE([$0], [AC_RUN_IFELSE])dnl
AC_DEFINE([_GNU_SOURCE])
])

AC_DEFUN([AC_PROG_EGREP],
[AC_CACHE_CHECK([for egrep], [ac_cv_prog_egrep],
   [if echo a | (grep -E '(a|b)') >/dev/null 2>&1
    then ac_cv_prog_egrep='grep -E'
    else ac_cv_prog_egrep='egrep'
    fi])
 EGREP=$ac_cv_prog_egrep
 AC_SUBST([EGREP])
])

AC_DEFUN([AC_PYTHON_DEVEL],[
        #
        # should allow for checking of python version here...
        #
        AC_REQUIRE([AM_PATH_PYTHON])

        # Check for Python include path
        AC_MSG_CHECKING([for Python include path])
        python_path=`echo $PYTHON | sed "s,/bin.*$,,"`
        for i in "$python_path/include/python$PYTHON_VERSION/" "$python_path/include/python/" "$python_path/" ; do
                python_path=`find $i -type f -name Python.h -print | sed "1q"`
                if test -n "$python_path" ; then
                        break
                fi
        done
        python_path=`echo $python_path | sed "s,/Python.h$,,"`
        AC_MSG_RESULT([$python_path])
        if test -z "$python_path" ; then
                AC_MSG_ERROR([cannot find Python include path])
        fi
        AC_SUBST([PYTHON_CPPFLAGS],[-I$python_path])

        # Check for Python library path
        AC_MSG_CHECKING([for Python library path])
        python_path=`echo $PYTHON | sed "s,/bin.*$,,"`
        for i in "$python_path/lib/python$PYTHON_VERSION/config/" "$python_path/lib/python$PYTHON_VERSION/" "$python_path/lib/python/config/" "$python_path/lib/python/" "$python_path/" ; do
                python_path=`find $i -type f -name libpython$PYTHON_VERSION.* -print | sed "1q"`
                if test -n "$python_path" ; then
                        break
                fi
        done
        python_path=`echo $python_path | sed "s,/libpython.*$,,"`
        AC_MSG_RESULT([$python_path])
        if test -z "$python_path" ; then
                AC_MSG_ERROR([cannot find Python library path])
        fi
        AC_SUBST([PYTHON_LDFLAGS],["-L$python_path -lpython$PYTHON_VERSION"])
        #
        python_site=`echo $python_path | sed "s/config/site-packages/"`
        AC_SUBST([PYTHON_SITE_PKG],[$python_site])
])
