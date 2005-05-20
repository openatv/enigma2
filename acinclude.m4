AC_DEFUN(TUXBOX_APPS,[
AM_CONFIG_HEADER(config.h)
AM_MAINTAINER_MODE

AC_GNU_SOURCE
AC_SYS_LARGEFILE

AC_ARG_WITH(target,
	[  --with-target=TARGET    target for compilation [[native,cdk]]],
	[TARGET="$withval"],[TARGET="native"])

AC_ARG_WITH(targetprefix,
	[  --with-targetprefix=PATH  prefix relative to target root [[PREFIX[for native], /[for cdk]]]],
	[targetprefix="$withval"],[targetprefix="NONE"])

AC_ARG_WITH(debug,
	[  --without-debug         disable debugging code],
	[DEBUG="$withval"],[DEBUG="yes"])

if test "$DEBUG" = "yes"; then
	DEBUG_CFLAGS="-g3 -ggdb"
	AC_DEFINE(DEBUG,1,[Enable debug messages])
fi

if test "$TARGET" = "native"; then
	if test "$CFLAGS" = "" -a "$CXXFLAGS" = ""; then
		CFLAGS="-Wall -O2 -pipe $DEBUG_CFLAGS"
		CXXFLAGS="-Wall -O2 -pipe $DEBUG_CFLAGS"
	fi
	if test "$prefix" = "NONE"; then
		prefix=/usr/local
	fi
	if test "$targetprefix" = "NONE"; then
		targetprefix="\${prefix}"
		_targetprefix="${prefix}"
	else
		_targetprefix="$targetprefix"
	fi
elif test "$TARGET" = "cdk"; then
	if test "$CC" = "" -a "$CXX" = ""; then
		CC=powerpc-tuxbox-linux-gnu-gcc CXX=powerpc-tuxbox-linux-gnu-g++
	fi
	if test "$CFLAGS" = "" -a "$CXXFLAGS" = ""; then
		CFLAGS="-Wall -Os -mcpu=823 -pipe $DEBUG_CFLAGS"
		CXXFLAGS="-Wall -Os -mcpu=823 -pipe $DEBUG_CFLAGS"
	fi
	if test "$prefix" = "NONE"; then
		prefix=/dbox2/cdkroot
	fi
	if test "$targetprefix" = "NONE"; then
		targetprefix=""
		_targetprefix=""
	else
		_targetprefix="$targetprefix"
	fi
	if test "$host_alias" = ""; then
		cross_compiling=yes
		host_alias=powerpc-tuxbox-linux-gnu
	fi
else
	AC_MSG_ERROR([invalid target $TARGET, choose on from native,cdk]);
fi

AC_CANONICAL_BUILD
AC_CANONICAL_HOST

targetdatadir="\${targetprefix}/share"
_targetdatadir="${_targetprefix}/share"
targetsysconfdir="\${targetprefix}/etc"
_targetsysconfdir="${_targetprefix}/etc"
targetlocalstatedir="\${targetprefix}/var"
_targetlocalstatedir="${_targetprefix}/var"
targetlibdir="\${targetprefix}/lib"
_targetlibdir="${_targetprefix}/lib"
AC_SUBST(targetprefix)
AC_SUBST(targetdatadir)
AC_SUBST(targetsysconfdir)
AC_SUBST(targetlocalstatedir)

check_path () {
	return $(perl -e "if(\"$1\"=~m#^/usr/(local/)?bin#){print \"0\"}else{print \"1\";}")
}

])

AC_DEFUN(TUXBOX_APPS_DIRECTORY,[
AC_REQUIRE([TUXBOX_APPS])

CONFIGDIR="\${localstatedir}/tuxbox/config"
_CONFIGDIR="${_targetlocalstatedir}/tuxbox/config"
AC_SUBST(CONFIGDIR)
AC_DEFINE_UNQUOTED(CONFIGDIR,"$_CONFIGDIR",[where to find the config files])

DATADIR="\${datadir}/tuxbox"
_DATADIR="${_targetdatadir}/tuxbox"
AC_SUBST(DATADIR)
AC_DEFINE_UNQUOTED(DATADIR,"$_DATADIR",[where to find data like icons])

FONTDIR="\${datadir}/fonts"
_FONTDIR="${_targetdatadir}/fonts"
AC_SUBST(FONTDIR)
AC_DEFINE_UNQUOTED(FONTDIR,"$_FONTDIR",[where to find the fonts])

GAMESDIR="\${localstatedir}/tuxbox/games"
_GAMESDIR="${_targetlocalstatedir}/tuxbox/games"
AC_SUBST(GAMESDIR)
AC_DEFINE_UNQUOTED(GAMESDIR,"$_GAMESDIR",[where games data is stored])

LIBDIR="\${libdir}/tuxbox"
_LIBDIR="${_targetlibdir}/tuxbox"
AC_SUBST(LIBDIR)
AC_SUBST(_LIBDIR)
AC_DEFINE_UNQUOTED(LIBDIR,"$_LIBDIR",[where to find the internal libs])

PLUGINDIR="\${libdir}/tuxbox/plugins"
_PLUGINDIR="${_targetlibdir}/tuxbox/plugins"
AC_SUBST(PLUGINDIR)
AC_DEFINE_UNQUOTED(PLUGINDIR,"$_PLUGINDIR",[where to find the plugins])

UCODEDIR="\${localstatedir}/tuxbox/ucodes"
_UCODEDIR="${_targetlocalstatedir}/tuxbox/ucodes"
AC_SUBST(UCODEDIR)
AC_DEFINE_UNQUOTED(UCODEDIR,"$_UCODEDIR",[where to find the ucodes (firmware)])
])

AC_DEFUN(TUXBOX_APPS_ENDIAN,[
AC_CHECK_HEADERS(endian.h)
AC_C_BIGENDIAN
])

AC_DEFUN(TUXBOX_APPS_DRIVER,[
AC_ARG_WITH(driver,
	[  --with-driver=PATH      path for driver sources[[NONE]]],
	[DRIVER="$withval"],[DRIVER=""])

if test -z "$DRIVER"; then
	AC_MSG_ERROR([can't find driver sources])
fi
CPPFLAGS="$CPPFLAGS -I$DRIVER/include"
AC_SUBST(DRIVER)
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
AC_REQUIRE([TUXBOX_APPS_PKGCONFIG])
AC_MSG_CHECKING(for package $2)
if PKG_CONFIG_PATH="${prefix}/lib/pkgconfig" $PKG_CONFIG --exists "$2" ; then
	AC_MSG_RESULT(yes)
	$1_CFLAGS=$(PKG_CONFIG_PATH="${prefix}/lib/pkgconfig" $PKG_CONFIG --cflags "$2")
	$1_LIBS=$(PKG_CONFIG_PATH="${prefix}/lib/pkgconfig" $PKG_CONFIG --libs "$2")
else
	AC_MSG_RESULT(no)
fi

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

