AC_INIT([enigma2],[3.0.0],[enigma2-devel@lists.elitedvb.net])
AM_INIT_AUTOMAKE([dist-bzip2 no-define tar-pax -Wno-portability])
AC_CONFIG_HEADERS([enigma2_config.h])

# Silent rules are available since 1.11, but older versions
# are still in use. So don't use them unconditionally.
m4_ifdef([AM_SILENT_RULES], [AM_SILENT_RULES([yes])])

AC_USE_SYSTEM_EXTENSIONS
AC_SYS_LARGEFILE

AC_PROG_CC
AC_PROG_CXX
m4_ifdef([LT_INIT], [LT_INIT], [AC_PROG_LIBTOOL])
AC_CONFIG_MACRO_DIR([m4])
AC_OPENMP()

AC_PATH_PROG(MSGFMT, msgfmt, AC_MSG_ERROR(Could not find msgfmt))
AC_PATH_PROG(MSGINIT, msginit, AC_MSG_ERROR(Could not find msginit))
AC_PATH_PROG(MSGMERGE, msgmerge, AC_MSG_ERROR(Could not find msgmerge))
AC_PATH_PROG(MSGUNIQ, msguniq, AC_MSG_ERROR(Could not find msguniq))
AC_PATH_PROG(XGETTEXT, xgettext, AC_MSG_ERROR(Could not find xgettext))

AM_PATH_PYTHON
AX_PYTHON_DEVEL
AX_PKG_SWIG
AX_SWIG_ENABLE_CXX
AX_SWIG_PYTHON
AX_PTHREAD

TUXBOX_APPS_DVB

AM_CONDITIONAL(HAVE_GIT_DIR, test -d "$srcdir/.git")
AM_CONDITIONAL(HAVE_FAKE_GIT_DIR, test -f "$srcdir/.git/last_commit_info")

dnl versions of gstreamer and plugins-base
AC_ARG_WITH(gstversion,
	AS_HELP_STRING([--with-gstversion],[use gstreamer version (major.minor)]),
	[GST_MAJORMINOR=$withval],[GST_MAJORMINOR=0.10])

PKG_CHECK_MODULES(BASE, [freetype2 fribidi gstreamer-$GST_MAJORMINOR gstreamer-pbutils-$GST_MAJORMINOR libdvbsi++ libpng libxml-2.0 sigc++-1.2 libssl libcrypto])
PKG_CHECK_MODULES(LIBDDVD, libdreamdvd, HAVE_LIBDDVD="yes", HAVE_LIBDDVD="no")
AM_CONDITIONAL(HAVE_LIBDDVD, test "$HAVE_LIBDDVD" = "yes")

AC_CHECK_LIB([dl], [dlopen], [LIBDL_LIBS="-ldl"], [AC_MSG_ERROR([Could not find libdl])])
AC_SUBST(LIBDL_LIBS)
AC_CHECK_LIB([jpeg], [jpeg_set_defaults], [LIBJPEG_LIBS="-ljpeg"], [AC_MSG_ERROR([Could not find libjpeg])])
AC_SUBST(LIBJPEG_LIBS)
AC_CHECK_LIB([ungif], [DGifOpen], [LIBGIF_LIBS="-lungif"], [AC_CHECK_LIB([gif], [DGifOpen], [LIBGIF_LIBS="-lgif"], [AC_MSG_ERROR([Could not find libgif or libungif])])])
AC_SUBST(LIBGIF_LIBS)

AC_LANG_PUSH([C++])
AC_CHECK_LIB([xmlccwrap], [exit], [LIBXMLCCWRAP_LIBS="-lxmlccwrap"], [AC_MSG_ERROR([Could not find libxmlccwrap])])
AC_SUBST(LIBXMLCCWRAP_LIBS)
AC_LANG_POP

AC_ARG_WITH(boxtype,
	[  --with-boxtype=NAME box type [[none,dm7025,dm800...]]],
	[BOXTYPE="$withval"],[BOXTYPE="dm800"])
AC_SUBST(BOXTYPE)
AC_DEFINE_UNQUOTED(BOXTYPE,"$BOXTYPE",[box type])

AM_CONDITIONAL(AZBOX, test `echo "$BOXTYPE" | cut -b 1-5` == "azbox")
AM_CONDITIONAL(CUBE, test `echo "$BOXTYPE" | cut -b 1-4` == "cube")
AM_CONDITIONAL(DAGS, test `echo "$BOXTYPE" | cut -b 1-4` == "dags")
AM_CONDITIONAL(DREAMBOX, test `echo "$BOXTYPE" | cut -b 1-2` == "dm")
AM_CONDITIONAL(VUPLUS, test `echo "$BOXTYPE" | cut -b 1-2` == "vu")
AM_CONDITIONAL(XTREND, test `echo "$BOXTYPE" | cut -b 1-2` == "et")
AM_CONDITIONAL(TECHNOMATE, test `echo "$BOXTYPE" | cut -b 1-2` == "tm")
AM_CONDITIONAL(INI, test `echo "$BOXTYPE" | cut -b 1-3` == "ini")
AM_CONDITIONAL(IQON, test `echo "$BOXTYPE" | cut -b 1-4` == "iqon")
AM_CONDITIONAL(GIGABLUE, test `echo "$BOXTYPE" | cut -b 1-5` == "gb800")
AM_CONDITIONAL(ODIN, test `echo "$BOXTYPE" | cut -b 1-4` == "odin")
AM_CONDITIONAL(VENTON, test `echo "$BOXTYPE" | cut -b 1-6` == "venton")
AM_CONDITIONAL(EBOX, test `echo "$BOXTYPE" | cut -b 1-4` == "ebox")
AM_CONDITIONAL(IXUSS, test `echo "$BOXTYPE" | cut -b 1-4` == "ixus")
AM_CONDITIONAL(EDISION, test `echo "$BOXTYPE" | cut -b 1-4` == "opti")
AM_CONDITIONAL(JEPSSEN, test `echo "$BOXTYPE" | cut -b 1-5` == "media")
AM_CONDITIONAL(SOGNO, test `echo "$BOXTYPE" | cut -b 1-5` == "sogno")
AM_CONDITIONAL(SKYLAKE, test `echo "$BOXTYPE" | cut -b 1-2` == "hd")
AM_CONDITIONAL(SPARK, test `echo "$BOXTYPE" | cut -b 1-5` == "spark")
AM_CONDITIONAL(UNIBOXHDE, test "$BOXTYPE" == uniboxhde)
AM_CONDITIONAL(EVO, test `echo "$BOXTYPE" | cut -b 1-4` == "enfi")
AM_CONDITIONAL(MIRACLEBOX, test `echo "$BOXTYPE" | cut -b 1-2` == "mb")
AM_CONDITIONAL(AZBOXME, test "$BOXTYPE" == azboxme)
AM_CONDITIONAL(AZBOXMINIME, test "$BOXTYPE" == azboxminime)
AM_CONDITIONAL(AZBOXHD, test "$BOXTYPE" == azboxhd)
AM_CONDITIONAL(DAGS1, test "$BOXTYPE" == dags1)
AM_CONDITIONAL(DAGS2, test "$BOXTYPE" == dags2)
AM_CONDITIONAL(DAGS3, test "$BOXTYPE" == dags3)
AM_CONDITIONAL(DAGS4, test "$BOXTYPE" == dags4)
AM_CONDITIONAL(DAGS5, test "$BOXTYPE" == dags5)
AM_CONDITIONAL(DM8000, test "$BOXTYPE" == dm8000)
AM_CONDITIONAL(DM7080, test "$BOXTYPE" == dm7080)
AM_CONDITIONAL(DM820, test "$BOXTYPE" == dm820)
AM_CONDITIONAL(DM7020HD, test "$BOXTYPE" == dm7020hd)
AM_CONDITIONAL(DM7020HDV2, test "$BOXTYPE" == dm7020hdv2)
AM_CONDITIONAL(DM800, test "$BOXTYPE" == dm800)
AM_CONDITIONAL(DM800SE, test "$BOXTYPE" == dm800se)
AM_CONDITIONAL(DM800SEV2, test "$BOXTYPE" == dm800sev2)
AM_CONDITIONAL(DM500HD, test "$BOXTYPE" == dm500hd)
AM_CONDITIONAL(DM500HDV2, test "$BOXTYPE" == dm500hdv2)
AM_CONDITIONAL(E3HD, test "$BOXTYPE" == e3hd)
AM_CONDITIONAL(VG1000, test "$BOXTYPE" == vg1000)
AM_CONDITIONAL(VG5000, test "$BOXTYPE" == vg5000)
AM_CONDITIONAL(MIXOSF5, test "$BOXTYPE" == mixosf5)
AM_CONDITIONAL(MIXOSF5MINI, test "$BOXTYPE" == mixosf5mini)
AM_CONDITIONAL(MIXOSLUMI, test "$BOXTYPE" == mixoslumi)
AM_CONDITIONAL(GI9196M, test "$BOXTYPE" == gi9196m)
AM_CONDITIONAL(GI9196LITE, test "$BOXTYPE" == gi9196lite)
AM_CONDITIONAL(MIXOSF7, test "$BOXTYPE" == mixosf7)
AM_CONDITIONAL(ENFINITY, test "$BOXTYPE" == enfinity)
AM_CONDITIONAL(BRE2ZE, test "$BOXTYPE" == bre2ze)
AM_CONDITIONAL(X2PLUS, test "$BOXTYPE" == x2plus)
AM_CONDITIONAL(XCOMBO, test "$BOXTYPE" == xcombo)
AM_CONDITIONAL(ET4X00, test "$BOXTYPE" == et4x00)
AM_CONDITIONAL(ET5X00, test "$BOXTYPE" == et5x00)
AM_CONDITIONAL(ET6X00, test "$BOXTYPE" == et6x00)
AM_CONDITIONAL(ET7X00, test "$BOXTYPE" == et7x00)
AM_CONDITIONAL(ET9X00, test "$BOXTYPE" == et9x00)
AM_CONDITIONAL(ET8000, test "$BOXTYPE" == et8000)
AM_CONDITIONAL(ET8500, test "$BOXTYPE" == et8500)
AM_CONDITIONAL(ET10000, test "$BOXTYPE" == et10000)
AM_CONDITIONAL(FORCE1, test "$BOXTYPE" == force1)
AM_CONDITIONAL(WORLDVISIONF1, test "$BOXTYPE" == worldvisionf1)
AM_CONDITIONAL(TRIPLEX, test "$BOXTYPE" == triplex)
AM_CONDITIONAL(FORMULER1, test "$BOXTYPE" == formuler1)
AM_CONDITIONAL(FORMULER3, test "$BOXTYPE" == formuler3)
AM_CONDITIONAL(GBIPBOX, test "$BOXTYPE" == gbipbox)
AM_CONDITIONAL(GB800SOLO, test "$BOXTYPE" == gb800solo)
AM_CONDITIONAL(GB800SE, test "$BOXTYPE" == gb800se)
AM_CONDITIONAL(GB800UE, test "$BOXTYPE" == gb800ue)
AM_CONDITIONAL(GB800SEPLUS, test "$BOXTYPE" == gb800seplus)
AM_CONDITIONAL(GB800UEPLUS, test "$BOXTYPE" == gb800ueplus)
AM_CONDITIONAL(GBULTRASE, test "$BOXTYPE" == gbultrase)
AM_CONDITIONAL(GBULTRAUE, test "$BOXTYPE" == gbultraue)
AM_CONDITIONAL(GBQUADPLUS, test "$BOXTYPE" == gbquadplus)
AM_CONDITIONAL(GBQUAD, test "$BOXTYPE" == gbquad)
AM_CONDITIONAL(INIHDE, test "$BOXTYPE" == inihde)
AM_CONDITIONAL(INIHDP, test "$BOXTYPE" == inihdp)
AM_CONDITIONAL(INIHDX, test "$BOXTYPE" == inihdx)
AM_CONDITIONAL(IQONIOS100HD, test "$BOXTYPE" == iqonios100hd)
AM_CONDITIONAL(IQONIOS200HD, test "$BOXTYPE" == iqonios200hd)
AM_CONDITIONAL(IQONIOS300HD, test "$BOXTYPE" == iqonios300hd)
AM_CONDITIONAL(IQONIOS300HDV2, test "$BOXTYPE" == iqonios300hdv2)
AM_CONDITIONAL(IXUSSONE, test "$BOXTYPE" == ixussone)
AM_CONDITIONAL(IXUSSZERO, test "$BOXTYPE" == ixusszero)
AM_CONDITIONAL(IXUSSDUO, test "$BOXTYPE" == ixussduo)
AM_CONDITIONAL(MEDIABOX, test "$BOXTYPE" == mediabox)
AM_CONDITIONAL(MBTWIN, test "$BOXTYPE" == mbtwin)
AM_CONDITIONAL(MUTANT2400, test "$BOXTYPE" == mutant2400)
AM_CONDITIONAL(ODINM6, test "$BOXTYPE" == odinm6)
AM_CONDITIONAL(ODINM7, test "$BOXTYPE" == odinm7)
AM_CONDITIONAL(ODINM9, test "$BOXTYPE" == odinm9)
AM_CONDITIONAL(QUADBOX2400, test "$BOXTYPE" == quadbox2400)
AM_CONDITIONAL(OPTIMUSSOS1, test "$BOXTYPE" == optimussos1)
AM_CONDITIONAL(OPTIMUSSOS2, test "$BOXTYPE" == optimussos2)
AM_CONDITIONAL(SOGNO8800HD, test "$BOXTYPE" == sogno8800hd)
AM_CONDITIONAL(TMTWINOE, test "$BOXTYPE" == tmtwin)
AM_CONDITIONAL(TM2TOE, test "$BOXTYPE" == tm2t)
AM_CONDITIONAL(TMSINGLE, test "$BOXTYPE" == tmsingle)
AM_CONDITIONAL(TMNANO, test "$BOXTYPE" == tmnano)
AM_CONDITIONAL(TMNANO2T, test "$BOXTYPE" == tmnano2t)
AM_CONDITIONAL(TMNANOSE, test "$BOXTYPE" == tmnanose)
AM_CONDITIONAL(VUUNO, test "$BOXTYPE" == vuuno)
AM_CONDITIONAL(VUULTIMO, test "$BOXTYPE" == vuultimo)
AM_CONDITIONAL(VUSOLO, test "$BOXTYPE" == vusolo)
AM_CONDITIONAL(VUSOLOSE, test "$BOXTYPE" == vusolose)
AM_CONDITIONAL(VUDUO, test "$BOXTYPE" == vuduo)
AM_CONDITIONAL(VUSOLO2, test "$BOXTYPE" == vusolo2)
AM_CONDITIONAL(VUDUO2, test "$BOXTYPE" == vuduo2)
AM_CONDITIONAL(VUZERO, test "$BOXTYPE" == vuzero)
AM_CONDITIONAL(VENTONHDX, test "$BOXTYPE" == ventonhdx)
AM_CONDITIONAL(XP1000, test "$BOXTYPE" == xp1000)
AM_CONDITIONAL(HAVE_COLORLCD3, test "$BOXTYPE" == dm7080)
AM_CONDITIONAL(HAVE_COLORLCD2, test "$BOXTYPE" == dm800se -o "$BOXTYPE" == dm800sev2 -o "$BOXTYPE" == dm820)
AM_CONDITIONAL(HAVE_COLORLCD1, test "$BOXTYPE" == dm8000 -o "$BOXTYPE" == dm800 -o "$BOXTYPE" == dm7020hd -o "$BOXTYPE" == dm7020hdv2)

AC_ARG_WITH(machinebuild,
	[  --with-machinebuild=NAME machine build [[none,atemeo5200,atemeo6000...]]],
	[MACHINEBUILD="$withval"],[MACHINEBUILD="atemeo5200"])
AC_SUBST(MACHINEBUILD)
AC_DEFINE_UNQUOTED(MACHINEBUILD,"$MACHINEBUILD",[machine build])

AC_ARG_WITH(libvugles2,
	AS_HELP_STRING([--with-libvugles2],[use libvugles2, yes or no]),
	[with_libvugles2=$withval],[with_libvugles2=no])
if test "$with_libvugles2" = "yes"; then
	PKG_CHECK_MODULES(LIBVUGLES2, [libvugles2])
	GLES_CFLAGS="-DUSE_LIBVUGLES2"
fi
AM_CONDITIONAL(HAVE_LIBVUGLES2, test "$with_libvugles2" = "yes")

if test `echo "$BOXTYPE" | cut -b 1-2` == "dm"; then
	AC_DEFINE(DREAMBOX, 1, [Dreambox hardware])
	AC_DEFINE(KEY_PLAY_ACTUALLY_IS_KEY_PLAYPAUSE, 1,[define when rc sends a KEY_PLAY event for its KEY_PLAYPAUSE key])
fi

AC_ARG_ENABLE([sh],
	[AS_HELP_STRING(--enable-sh,    enable sh patches)],
	[case "${enableval}" in
		yes) enable_sh=true ;;
		no) enable_sh=false ;;
		*) AC_MSG_ERROR([bad value ${enableval} for --enable-sh]) ;;
	esac])
AM_CONDITIONAL([ENABLE_SH], [test x$enable_sh = xtrue])

AC_ARG_WITH(nolcd,
	AC_HELP_STRING([--with-nolcd], [disable ascii based lcd, yes or no]),
	[[withnolcd=$withval]],
	[[withnolcd=no]]
)
if test x"$withnolcd" != xno ; then
	AC_DEFINE(NO_LCD, 1,[Define when disable an ascii based lcd device])
fi
AM_CONDITIONAL(NO_LCD, test x"$withnolcd" != xno)

AC_ARG_WITH(textlcd,
	AC_HELP_STRING([--with-textlcd], [use ascii based lcd, yes or no]),
	[[withtextlcd=$withval]],
	[[withtextlcd=no]]
)
if test x"$withtextlcd" != xno ; then
	AC_DEFINE(HAVE_TEXTLCD, 1,[Define when using an ascii based lcd device])
fi
AM_CONDITIONAL(HAVE_TEXTLCD, test x"$withtextlcd" != xno)

AC_ARG_WITH(colorlcd,
	AC_HELP_STRING([--with-colorlcd], [use 96x64 16bpp color display, yes or no]),
	[[withcolorlcd=$withval]],
	[[withcolorlcd=no]]
)
if test x"$withcolorlcd" != xno ; then
	AC_DEFINE(HAVE_COLORLCD, 1,[Define when using a 96x64 color display device])
fi
AM_CONDITIONAL(HAVE_COLORLCD, test x"$withcolorlcd" != xno)

AC_ARG_WITH(colorlcd128,
	AC_HELP_STRING([--with-colorlcd128], [use 128x64 16bpp color display, yes or no]),
	[[withcolorlcd128=$withval]],
	[[withcolorlcd128=no]]
)
if test x"$withcolorlcd128" != xno ; then
	AC_DEFINE(HAVE_COLORLCD128, 1,[Define when using a 128x64 color display device])
fi
AM_CONDITIONAL(HAVE_COLORLCD128, test x"$withcolorlcd" != xno)

AC_ARG_WITH(colorlcd220,
	AC_HELP_STRING([--with-colorlcd220], [use 220x176 16bpp color display, yes or no]),
	[[withcolorlcd220=$withval]],
	[[withcolorlcd220=no]]
)
if test x"$withcolorlcd220" != xno ; then
	AC_DEFINE(HAVE_COLORLCD220, 1,[Define when using a 220x176 color display device])
fi
AM_CONDITIONAL(HAVE_COLORLCD220, test x"$withcolorlcd220" != xno)

AC_ARG_WITH(colorlcd400,
	AC_HELP_STRING([--with-colorlcd400], [use 400x176 16bpp color display, yes or no]),
	[[withcolorlcd400=$withval]],
	[[withcolorlcd400=no]]
)
if test x"$withcolorlcd400" != xno ; then
	AC_DEFINE(HAVE_COLORLCD400, 1,[Define when using a 400x176 color display device])
fi

AM_CONDITIONAL(HAVE_COLORLCD400, test x"$withcolorlcd400" != xno)

AC_ARG_WITH(colorlcd720,
	AC_HELP_STRING([--with-colorlcd720], [use 720x576 16bpp color display, yes or no]),
	[[withcolorlcd720=$withval]],
	[[withcolorlcd720=no]]
)
if test x"$withcolorlcd720" != xno ; then
	AC_DEFINE(HAVE_COLORLCD720, 1,[Define when using a 720x576 color display device])
fi

AM_CONDITIONAL(HAVE_COLORLCD720, test x"$withcolorlcd720" != xno)

AC_ARG_WITH(bwlcd255,
	AC_HELP_STRING([--with-bwlcd255], [use 255x64 1bpp black and white display, yes or no]),
	[[withbwlcd255=$withval]],
	[[withbwlcd255=no]]
)
if test x"$withbwlcd255" != xno ; then
	AC_DEFINE(HAVE_BWLCD255, 1,[Define when using a 255x64 black and white display device])
fi
AM_CONDITIONAL(HAVE_BWLCD255, test x"$withbwlcd255" != xno)

AC_ARG_WITH(bwlcd140,
	AC_HELP_STRING([--with-bwlcd140], [use 140x32 1bpp black and white display, yes or no]),
	[[withbwlcd140=$withval]],
	[[withbwlcd140=no]]
)
if test x"$withbwlcd140" != xno ; then
	AC_DEFINE(HAVE_BWLCD140, 1,[Define when using a 140x32 black and white display device])
fi
AM_CONDITIONAL(HAVE_BWLCD140, test x"$withbwlcd140" != xno)

AC_ARG_WITH(bwlcd128,
	AC_HELP_STRING([--with-bwlcd128], [use 128x32 1bpp black and white display, yes or no]),
	[[withbwlcd128=$withval]],
	[[withbwlcd128=no]]
)
if test x"$withbwlcd128" != xno ; then
	AC_DEFINE(HAVE_BWLCD128, 1,[Define when using a 128x32 black and white display device])
fi
AM_CONDITIONAL(HAVE_BWLCD128, test x"$withbwlcd128" != xno)

AC_ARG_WITH(fullgraphiclcd,
	AC_HELP_STRING([--with-fullgraphiclcd], [display right_half_vfd_icons from skin(for ultimo), yes or no]),
	[[withfullgraphiclcd=$withval]],
	[[withfullgraphiclcd=no]]
)
if test x"$withfullgraphiclcd" != xno ; then
	AC_DEFINE(HAVE_FULLGRAPHICLCD, 1,[Define when display right_half_vfd_icons from skin, for ultimo])
fi
AM_CONDITIONAL(HAVE_FULLGRAPHICLCD, test x"$withfullgraphiclcd" != xno)

AC_ARG_WITH(gigabluelcd,
	AC_HELP_STRING([--with-gigabluelcd], [use fix colour map in color display, yes or no]),
	[[withgigabluelcd=$withval]],
	[[withgigabluelcd=no]]
)
if test x"$withgigabluelcd" != xno ; then
	AC_DEFINE(HAVE_GIGABLUELCD, 1,[Define when using a 220x176 color display device])
fi
AM_CONDITIONAL(HAVE_GIGABLUELCD, test x"$withgigabluelcd" != xno)

AC_ARG_WITH(oldpvr,
	AC_HELP_STRING([--with-oldpvr], [use /dev/misc/pvr instead of /dev/dvb/adapterX/dvrX, yes or no]),
	[[witholdpvr=$withval]],
	[[witholdpvr=no]]
)
if test x"$witholdpvr" != xno ; then
	AC_DEFINE(HAVE_OLDPVR, 1,[Define when using /dev/misc/pvr])
fi
AM_CONDITIONAL(HAVE_OLDPVR, test x"$witholdpvr" != xno)

if test "$BOXTYPE" == "dm7080" -o "$BOXTYPE" == "dm820"; then
	AC_DEFINE(TUNER_DM7080, 1,[define BOXTYPE DM7080])
fi

if test "$BOXTYPE" == "azboxme" -o "$BOXTYPE" == "azboxminime"; then
	AC_DEFINE(FORCE_ADVANCED_REMOTE, 1,[define to fixup the input device identification when the remote control is actually an 'advanced' remote (with play/forward/rewind keys)])
	AC_DEFINE(FORCE_NO_BLENDING_ACCELERATION, 1,[define when the framebuffer acceleration does not have alphablending support, though the autodetection might indicate that it does])
	AC_DEFINE(FORCE_NO_ACCELNEVER, 1,[define when the framebuffer acceleration auto not working correct])
	AC_DEFINE(KEY_PLAY_ACTUALLY_IS_KEY_PLAYPAUSE, 1,[define when rc sends a KEY_PLAY event for its KEY_PLAYPAUSE key])
	AC_DEFINE(KEY_TV_TO_KEY_STOP, 1,[define when rc sends a KEY_TV event for its KEY_STOP])
	AC_DEFINE(KEY_VIDEO_TO_KEY_SUBTITLE, 1,[define when rc sends a KEY_VIDEO event for its KEY_SUBTITLE])
	AC_DEFINE(KEY_RADIO_TO_KEY_RECORD, 1,[define when rc sends a KEY_RADIO event for its KEY_RECORD])
	AC_DEFINE(KEY_HOME_TO_KEY_OPEN, 1,[define when rc sends a KEY_HOME event for its KEY_OPEN])
fi

if test "$BOXTYPE" == "azboxhd"; then
	AC_DEFINE(FORCE_ADVANCED_REMOTE, 1,[define to fixup the input device identification when the remote control is actually an 'advanced' remote (with play/forward/rewind keys)])
	AC_DEFINE(FORCE_NO_BLENDING_ACCELERATION, 1,[define when the framebuffer acceleration does not have alphablending support, though the autodetection might indicate that it does])
	AC_DEFINE(FORCE_NO_ACCELNEVER, 1,[define when the framebuffer acceleration auto not working correct])
	AC_DEFINE(KEY_PLAY_ACTUALLY_IS_KEY_PLAYPAUSE, 1,[define when rc sends a KEY_PLAY event for its KEY_PLAYPAUSE key])
	AC_DEFINE(KEY_HOME_TO_KEY_OPEN, 1,[define when rc sends a KEY_HOME event for its KEY_OPEN])
	AC_DEFINE(KEY_VIDEO_TO_KEY_EPG, 1,[define when rc sends a KEY_VIDEO event for its KEY_EPG])
	AC_DEFINE(KEY_TV_TO_KEY_MODE, 1,[define when rc sends a KEY_TV event for its KEY_MODE key])
	AC_DEFINE(KEY_TEXT_TO_KEY_AUDIO, 1,[define when rc sends a KEY_TEXT event for its KEY_AUDIO key])
fi

if test "$BOXTYPE" == "ebox5000" -o "$BOXTYPE" == "ebox7358" -o "$BOXTYPE" == "ebox5100" -o "$BOXTYPE" == "eboxlumi"; then
	AC_DEFINE(KEY_SCREEN_TO_KEY_ANGLE, 1,[define when rc sends a KEY_SCREEN event for its KEY_ANGLE key])
	AC_DEFINE(KEY_TIME_TO_KEY_SLEEP, 1,[define when rc sends a KEY_TIME event for its KEY_SLEEP])
	AC_DEFINE(KEY_MODE_TO_KEY_AUDIO, 1,[define when rc sends a KEY_MODE event for its AV plus])
fi


if test "$BOXTYPE" == "et4x00" -o "$BOXTYPE" == "et5x00" -o "$BOXTYPE" == "et6x00"  -o "$BOXTYPE" == "et7x00" -o "$BOXTYPE" == "et9x00" -o "$BOXTYPE" == "et8000" -o "$BOXTYPE" == "et8500" -o "$BOXTYPE" == "et10000"; then
	AC_DEFINE(KEY_PLAY_ACTUALLY_IS_KEY_PLAYPAUSE, 1,[define when rc sends a KEY_PLAY event for its KEY_PLAYPAUSE key])
	AC_DEFINE(KEY_F3_TO_KEY_LIST, 1,[define when rc sends a KEY_F3 event for its KEY_LIST key])
fi

if test "$BOXTYPE" == "et8500"; then
	AC_DEFINE(FORCE_BLENDING_ACCELERATION, 1,[define when the framebuffer acceleration has alphablending support, but detection slow down all])
fi

if test "$BOXTYPE" == "et7x00"; then
	AC_DEFINE(KEY_F1_TO_KEY_F2, 1,[define when rc sends a KEY_F1 event for its KEY_F2 key])
	AC_DEFINE(FORCE_BLENDING_ACCELERATION, 1,[define when the framebuffer acceleration has alphablending support, but detection slow down all])
fi

if test "$BOXTYPE" == "xc7362"; then
	AC_DEFINE(KEY_FAV_TO_KEY_PVR, 1,[define FAV KEY to PVR])
fi

if test "$BOXTYPE" == "hd2400" -o "$BOXTYPE" == "hd1100" -o "$BOXTYPE" == "hd1200" -o "$BOXTYPE" == "hd500c"; then
	AC_DEFINE(KEY_PLAY_ACTUALLY_IS_KEY_PLAYPAUSE, 1,[define when rc sends a KEY_PLAY event for its KEY_PLAYPAUSE key])
	AC_DEFINE(KEY_F3_TO_KEY_LIST, 1,[define when rc sends a KEY_F3 event for its KEY_LIST key])
fi

if test "$BOXTYPE" == "formuler1" -o "$BOXTYPE" == "formuler3" -o "$BOXTYPE" == "triplex" -o "$BOXTYPE" == "sf108"; then
	AC_DEFINE(KEY_F3_TO_KEY_LIST, 1,[define when rc sends a KEY_F3 event for its KEY_LIST key])
fi

if test "$BOXTYPE" == "ew7358" -o "$BOXTYPE" == "ew7362"; then
	AC_DEFINE(KEY_PLAY_ACTUALLY_IS_KEY_PLAYPAUSE, 1,[define when rc sends a KEY_PLAY event for its KEY_PLAYPAUSE key])
	AC_DEFINE(KEY_MEDIA_TO_KEY_LIST, 1,[define when rc sends a KEY_MEDIA event for its KEY_LIST key])
fi

if test "$BOXTYPE" == "ew7356" ; then
	AC_DEFINE(KEY_PLAY_ACTUALLY_IS_KEY_PLAYPAUSE, 1,[define when rc sends a KEY_PLAY event for its KEY_PLAYPAUSE key])
fi

if test "$BOXTYPE" == "sh1" ; then
	AC_DEFINE(KEY_PLAY_ACTUALLY_IS_KEY_PLAYPAUSE, 1,[define when rc sends a KEY_PLAY event for its KEY_PLAYPAUSE key])
fi

if test "$BOXTYPE" == "7000s" ; then
	AC_DEFINE(KEY_PLAY_ACTUALLY_IS_KEY_PLAYPAUSE, 1,[define when rc sends a KEY_PLAY event for its KEY_PLAYPAUSE key])
fi

if test "$BOXTYPE" == "odinm9"; then
	AC_DEFINE(KEY_PLAY_ACTUALLY_IS_KEY_PLAYPAUSE, 1,[define when rc sends a KEY_PLAY event for its KEY_PLAYPAUSE key])
	AC_DEFINE(FORCE_NO_BLENDING_ACCELERATION, 1,[define when the framebuffer acceleration does not have alphablending support, though the autodetection might indicate that it does])
fi

if test "$BOXTYPE" == "odinm7"  -o "$BOXTYPE" == "e3hd"; then
	AC_DEFINE(FORCE_NO_BLENDING_ACCELERATION, 1,[define when the framebuffer acceleration does not have alphablending support, though the autodetection might indicate that it does])
	AC_DEFINE(KEY_POWER2_TO_KEY_WWW, 1,[define when rc sends a KEY_POWER2 event for its KEY_WWW key])
	AC_DEFINE(KEY_DIRECTORY_TO_KEY_FILE, 1,[define when rc sends a KEY_DIRECTORY event for its KEY_FILE key])
fi

if test "$BOXTYPE" == "vuduo" -o "$BOXTYPE" == "vusolo" -o "$BOXTYPE" == "vuduo2" -o "$BOXTYPE" == "vusolo2" -o "$BOXTYPE" == "vuuno" -o "$BOXTYPE" == "vuultimo" -o "$BOXTYPE" == "vusolose" -o "$BOXTYPE" == "vuzero"; then
	AC_DEFINE(FORCE_NO_BLENDING_ACCELERATION, 1,[define when the framebuffer acceleration does not have alphablending support, though the autodetection might indicate that it does])
	AC_DEFINE(FORCE_ADVANCED_REMOTE, 1,[define to fixup the input device identification when the remote control is actually an 'advanced' remote (with play/forward/rewind keys)])
	AC_DEFINE(KEY_HELP_TO_KEY_INFO, 1,[define when rc sends a KEY_HELP event we need KEY_INFO])
	AC_DEFINE(KEY_INFO_TO_KEY_EPG, 1,[define when rc sends a KEY_INFO event for its KEY_EPG key])
fi

if test "$BOXTYPE" == "vp7358ci" ; then
	AC_DEFINE(FORCE_ADVANCED_REMOTE, 1,[define to fixup the input device identification when the remote control is actually an 'advanced' remote (with play/forward/rewind keys)])
	AC_DEFINE(KEY_HELP_TO_KEY_INFO, 1,[define when rc sends a KEY_HELP event we need KEY_INFO])
	AC_DEFINE(KEY_INFO_TO_KEY_EPG, 1,[define when rc sends a KEY_INFO event for its KEY_EPG key])
fi

if test "$BOXTYPE" == "gb800solo" -o "$BOXTYPE" == "gb800se" -o "$BOXTYPE" == "gb800ue" -o "$BOXTYPE" == "gbquad" -o "$BOXTYPE" == "gb800seplus" -o "$BOXTYPE" == "gb800ueplus" -o "$BOXTYPE" == "gbquadplus" -o "$BOXTYPE" == "gbipbox" -o "$BOXTYPE" == "gbultrase" -o "$BOXTYPE" == "gbultraue"; then
	AC_DEFINE(KEY_PLAY_ACTUALLY_IS_KEY_PLAYPAUSE, 1,[define when rc sends a KEY_PLAY event for its KEY_PLAYPAUSE key])
	AC_DEFINE(KEY_GUIDE_TO_KEY_EPG, 1,[define when rc sends a KEY_HELP event for its KEY_EPG key])
	AC_DEFINE(KEY_F2_TO_KEY_F6, 1,[define when rc sends a KEY_F2 event for its KEY_F6 key])
	AC_DEFINE(KEY_SCREEN_TO_KEY_MODE, 1,[define when rc sends a KEY_MODE event for its KEY_ASPECT key])
fi

if test "$BOXTYPE" == "inihde" -o "$BOXTYPE" == "inihdx" -o "$BOXTYPE" == "inihdp" -o "$BOXTYPE" == "inihde2"; then
	AC_DEFINE(KEY_PLAY_ACTUALLY_IS_KEY_PLAYPAUSE, 1,[define when rc sends a KEY_PLAY event for its KEY_PLAYPAUSE key])
	AC_DEFINE(FORCE_NO_BLENDING_ACCELERATION, 1,[define when the framebuffer acceleration does not have alphablending support, though the autodetection might indicate that it does])
	AC_DEFINE(KEY_MEDIA_TO_KEY_OPEN, 1,[define when rc sends a KEY_MEDIA event for its KEY_OPEN key])
	AC_DEFINE(KEY_SEARCH_TO_KEY_WWW, 1,[define when rc sends a KEY_SEARCH event for its KEY_WWW key])
	AC_DEFINE(KEY_OPTION_TO_KEY_PC, 1,[define when rc sends a KEY_OPTION event for its KEY_PC key])
	AC_DEFINE(KEY_ZOOM_TO_KEY_SCREEN, 1,[define when rc sends a KEY_ZOOM event for its KEY_SCREEN key])
	AC_DEFINE(KEY_VIDEO_TO_KEY_MODE, 1,[define when rc sends a KEY_VIDEO event for its KEY_MODE key])
	AC_DEFINE(KEY_BOOKMARKS_TO_KEY_DIRECTORY, 1,[define when rc sends a KEY_BOOKMARKS event for its KEY_DIRECTORY key])
	AC_DEFINE(KEY_LIST_TO_KEY_PVR, 1,[define when rc sends a KEY_LIST event for its KEY_PVR key])
fi

if test "$MACHINEBUILD" == "bwidowx" ; then
	AC_DEFINE(FORCE_NO_BLENDING_ACCELERATION, 1,[define when the framebuffer acceleration does not have alphablending support, though the autodetection might indicate that it does])
	AC_DEFINE(KEY_ZOOM_TO_KEY_SCREEN, 1,[define when rc sends a KEY_ZOOM event for its KEY_SCREEN key])
	AC_DEFINE(KEY_LAST_TO_KEY_PVR, 1,[define when rc sends a KEY_LAST event for its KEY_PVR key])
fi

if test "$BOXTYPE" == "vg1000" -o "$BOXTYPE" == "vg2000" -o "$BOXTYPE" == "vg5000"; then
	AC_DEFINE(KEY_PLAY_ACTUALLY_IS_KEY_PLAYPAUSE, 1,[define when rc sends a KEY_PLAY event for its KEY_PLAYPAUSE key])
	AC_DEFINE(KEY_F3_TO_KEY_LIST, 1,[define when rc sends a KEY_F3 event for its KEY_LIST key])
fi

if test `echo "$BOXTYPE" | cut -b 1-4` == "ixus"; then
	AC_DEFINE(FORCE_NO_BLENDING_ACCELERATION, 1,[define when the framebuffer acceleration does not have alphablending support, though the autodetection might indicate that it does])
fi

if test "$BOXTYPE" == "blackbox7405"; then
	AC_DEFINE(FORCE_ADVANCED_REMOTE, 1,[define to fixup the input device identification when the remote control is actually an 'advanced' remote (with play/forward/rewind keys)])
	AC_DEFINE(KEY_PLAY_IS_KEY_PLAYPAUSE, 1,[define when rc sends a KEY_PLAY event for its KEY_PLAYPAUSE key])
	AC_DEFINE(KEY_MEDIA_TO_KEY_BOOKMARKS, 1,[define when rc sends a KEY_MEDIA event for its KEY_BOOKMARKS key])
	AC_DEFINE(KEY_VIDEO_IS_KEY_SCREEN, 1,[define when rc sends a KEY_VIDEO event for its KEY_SCREEN key])
	AC_DEFINE(KEY_ARCHIVE_TO_KEY_DIRECTORY, 1,[define when rc sends a KEY_MEDIA event for its KEY_BOOKMARKS key])
	AC_DEFINE(KEY_TIME_TO_KEY_SLOW, 1,[define when rc sends a KEY_TOME event for its KEY_SLOW key])
fi

if test "$BOXTYPE" == "dags1" -o "$BOXTYPE" == "dags2" -o "$BOXTYPE" == "dags3" -o "$BOXTYPE" == "dags4" -o "$BOXTYPE" == "dags5"; then
	AC_DEFINE(KEY_F1_TO_KEY_PC, 1,[define when rc sends a KEY_F1 event for its KEY_PC key])
	AC_DEFINE(KEY_F5_TO_KEY_ANGLE, 1,[define when rc sends a KEY_F5 event for its KEY_ANGLE key])
	AC_DEFINE(KEY_DOT_TO_KEY_HOMEPAGE, 1,[define when rc sends a KEY_DOT event for its KEY_KEY_HOMEPAGE key])
	AC_DEFINE(KEY_HOME_TO_KEY_HOMEPAGE, 1,[define when rc sends a KEY_HOME event for its KEY_KEY_HOMEPAGE key])
	AC_DEFINE(KEY_MEDIA_TO_KEY_KEY_F2, 1,[define when rc sends a KEY_MEDIA event for its KEY_KEY_F1 key])
	AC_DEFINE(HAVE_LINUXSOCKADDR, 1,[define it use sockaddr_un instead of sockaddr_in on linux domain socket.])
	AC_DEFINE(FORCE_NO_BLENDING_ACCELERATION, 1,[define when the framebuffer acceleration does not have alphablending support, though the autodetection might indicate that it does])
	AC_DEFINE(FORCE_ADVANCED_REMOTE, 1,[define to fixup the input device identification when the remote control is actually an 'advanced' remote (with play/forward/rewind keys)])
fi

if test "$BOXTYPE" == "spark" -o "$BOXTYPE" == "spark7162"; then
	AC_DEFINE(FORCE_ADVANCED_REMOTE, 1,[define to fixup the input device identification when the remote control is actually an 'advanced' remote (with play/forward/rewind keys)])
fi

AC_ARG_WITH(libsdl,
	AS_HELP_STRING([--with-libsdl],[use libsdl, yes or no]),
	[with_libsdl=$withval],[with_libsdl=no])
if test "$with_libsdl" = "yes"; then
	PKG_CHECK_MODULES(LIBSDL, sdl)
fi
AM_CONDITIONAL(HAVE_LIBSDL, test "$with_libsdl" = "yes")

AC_ARG_WITH(libxine,
	AS_HELP_STRING([--with-libxine],[use libxine, yes or no]),
	[with_libxine=$withval],[with_libxine=no])
if test "$with_libxine" = "yes"; then
	PKG_CHECK_MODULES(LIBXINE, libxine)
	AC_DEFINE([WITH_XINE],[1],[Define to 1 if you have libxine])
fi
AM_CONDITIONAL(HAVE_LIBXINE, test "$with_libxine" = "yes")

AC_ARG_WITH(debug,
	AS_HELP_STRING([--without-debug],[disable debugging code]),
	[with_debug="$withval"],[with_debug="yes"])
if test "$with_debug" = "yes"; then
	DEBUG_CFLAGS="-ggdb3"
	AC_DEFINE([DEBUG],[1],[Define to 1 to enable debugging code])
fi

AC_ARG_WITH(memcheck,
	AS_HELP_STRING([--with-memcheck],[enable memory leak checks]),
	[with_memcheck="$withval"],[with_memcheck="no"])
if test "$with_memcheck" = "yes"; then
	AC_DEFINE([MEMLEAK_CHECK],[1],[Define to 1 to enable memory leak checks])
fi

ENIGMA2_CFLAGS="-fno-rtti -fno-exceptions"
AC_SUBST(ENIGMA2_CFLAGS)

CPPFLAGS="$CPPFLAGS $PYTHON_CPPFLAGS"
CFLAGS="$CFLAGS $DEBUG_CFLAGS -Wall"
CXXFLAGS="$CXXFLAGS $DEBUG_CFLAGS -Wall $BASE_CFLAGS $ENIGMA2_CFLAGS $PTHREAD_CFLAGS $OPENMP_CFLAGS $GLES_CFLAGS"
AX_SWIG_PYTHON_OPT="$AX_SWIG_PYTHON_OPT -DSWIG_PYTHON_LEGACY_BOOL"

AC_CONFIG_FILES([
Makefile
data/Makefile
data/fonts/Makefile
data/keymaps/Makefile
data/displaytext/Makefile
data/displaydualtext/Makefile
data/display96/Makefile
data/display128/Makefile
data/display128dm/Makefile
data/display220/Makefile
data/display400/Makefile
data/display720/Makefile
data/vfd128/Makefile
data/vfd140/Makefile
data/vfd255/Makefile
include/Makefile
lib/Makefile
lib/base/eenv.cpp
lib/python/Makefile
lib/python/Components/Makefile
lib/python/Components/Converter/Makefile
lib/python/Components/Renderer/Makefile
lib/python/Components/Sources/Makefile
lib/python/Screens/Makefile
lib/python/Plugins/Makefile
lib/python/Plugins/Extensions/Makefile
lib/python/Plugins/Extensions/CutListEditor/Makefile
lib/python/Plugins/Extensions/CutListEditor/meta/Makefile
lib/python/Plugins/Extensions/DVDBurn/Makefile
lib/python/Plugins/Extensions/DVDBurn/meta/Makefile
lib/python/Plugins/Extensions/DVDPlayer/Makefile
lib/python/Plugins/Extensions/DVDPlayer/meta/Makefile
lib/python/Plugins/Extensions/MediaPlayer/Makefile
lib/python/Plugins/Extensions/MediaPlayer/meta/Makefile
lib/python/Plugins/Extensions/MediaScanner/Makefile
lib/python/Plugins/Extensions/MediaScanner/meta/Makefile
lib/python/Plugins/Extensions/PicturePlayer/Makefile
lib/python/Plugins/Extensions/PicturePlayer/meta/Makefile
lib/python/Plugins/Extensions/PicturePlayer/data/Makefile
lib/python/Plugins/Extensions/SocketMMI/Makefile
lib/python/Plugins/Extensions/SocketMMI/meta/Makefile
lib/python/Plugins/Extensions/SocketMMI/src/Makefile
lib/python/Plugins/Extensions/TuxboxPlugins/Makefile
lib/python/Plugins/Extensions/TuxboxPlugins/meta/Makefile
lib/python/Plugins/Extensions/Infopanel/Makefile
lib/python/Plugins/Extensions/Infopanel/meta/Makefile
lib/python/Plugins/Extensions/Infopanel/locale/Makefile
lib/python/Plugins/Extensions/Infopanel/icons/Makefile
lib/python/Plugins/Extensions/Volume_adjust/Makefile
lib/python/Plugins/Extensions/Volume_adjust/nl/Makefile
lib/python/Plugins/SystemPlugins/CableScan/Makefile
lib/python/Plugins/SystemPlugins/CommonInterfaceAssignment/Makefile
lib/python/Plugins/SystemPlugins/CommonInterfaceAssignment/meta/Makefile
lib/python/Plugins/SystemPlugins/DefaultServicesScanner/Makefile
lib/python/Plugins/SystemPlugins/DefaultServicesScanner/meta/Makefile
lib/python/Plugins/SystemPlugins/DiseqcTester/Makefile
lib/python/Plugins/SystemPlugins/DiseqcTester/meta/Makefile
lib/python/Plugins/SystemPlugins/FastScan/Makefile
lib/python/Plugins/SystemPlugins/FrontprocessorUpgrade/Makefile
lib/python/Plugins/SystemPlugins/FrontprocessorUpgrade/meta/Makefile
lib/python/Plugins/SystemPlugins/HdmiCEC/Makefile
lib/python/Plugins/SystemPlugins/Hotplug/Makefile
lib/python/Plugins/SystemPlugins/Hotplug/meta/Makefile
lib/python/Plugins/SystemPlugins/LCNScanner/Makefile
lib/python/Plugins/SystemPlugins/Makefile
lib/python/Plugins/SystemPlugins/NetworkWizard/Makefile
lib/python/Plugins/SystemPlugins/NetworkWizard/meta/Makefile
lib/python/Plugins/SystemPlugins/NFIFlash/Makefile
lib/python/Plugins/SystemPlugins/NFIFlash/meta/Makefile
lib/python/Plugins/SystemPlugins/PositionerSetup/Makefile
lib/python/Plugins/SystemPlugins/PositionerSetup/meta/Makefile
lib/python/Plugins/SystemPlugins/SatelliteEquipmentControl/Makefile
lib/python/Plugins/SystemPlugins/SatelliteEquipmentControl/meta/Makefile
lib/python/Plugins/SystemPlugins/Satfinder/Makefile
lib/python/Plugins/SystemPlugins/Satfinder/meta/Makefile
lib/python/Plugins/SystemPlugins/SoftwareManager/Makefile
lib/python/Plugins/SystemPlugins/SoftwareManager/meta/Makefile
lib/python/Plugins/SystemPlugins/VideoClippingSetup/Makefile
lib/python/Plugins/SystemPlugins/VideoEnhancement/Makefile
lib/python/Plugins/SystemPlugins/VideoEnhancement/meta/Makefile
lib/python/Plugins/SystemPlugins/VideoTune/Makefile
lib/python/Plugins/SystemPlugins/VideoTune/meta/Makefile
lib/python/Plugins/SystemPlugins/WirelessLan/Makefile
lib/python/Plugins/SystemPlugins/WirelessLan/meta/Makefile
lib/python/Plugins/SystemPlugins/SkinSelector/Makefile
lib/python/Plugins/SystemPlugins/SkinSelector/meta/Makefile
lib/python/Plugins/SystemPlugins/AnimationSetup/Makefile
lib/python/Tools/Makefile
po/Makefile
main/Makefile
tools/Makefile
tools/enigma2.sh
enigma2.pc
])
AC_OUTPUT
