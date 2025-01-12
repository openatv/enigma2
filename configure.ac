AC_INIT([enigma2],[7.4],[https://www.opena.tv])
AM_INIT_AUTOMAKE([dist-bzip2 no-define tar-pax -Wno-portability])
AC_CONFIG_HEADERS([enigma2_config.h])

# Silent rules are available since 1.11, but older versions
# are still in use. So don't use them unconditionally.
m4_ifdef([AM_SILENT_RULES], [AM_SILENT_RULES([yes])])

AC_USE_SYSTEM_EXTENSIONS
AC_SYS_LARGEFILE

AC_PROG_CC
AC_PROG_CXX
AX_CXX_COMPILE_STDCXX_17
m4_ifdef([LT_INIT], [LT_INIT], [AC_PROG_LIBTOOL])
AC_CONFIG_MACRO_DIR([m4])
AC_OPENMP()

AC_PATH_PROG(MSGFMT, msgfmt, AC_MSG_ERROR(Could not find msgfmt))
AC_PATH_PROG(MSGINIT, msginit, AC_MSG_ERROR(Could not find msginit))
AC_PATH_PROG(MSGMERGE, msgmerge, AC_MSG_ERROR(Could not find msgmerge))
AC_PATH_PROG(MSGUNIQ, msguniq, AC_MSG_ERROR(Could not find msguniq))
AC_PATH_PROG(MSGATTRIB, msgattrib, AC_MSG_ERROR(Could not find msgattrib))
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

PKG_CHECK_MODULES(TUXTXT, tuxbox-tuxtxt)
PKG_CHECK_MODULES(GSTREAMER, gstreamer-$GST_MAJORMINOR gstreamer-pbutils-$GST_MAJORMINOR)
PKG_CHECK_MODULES(BASE, [freetype2 fribidi gstreamer-$GST_MAJORMINOR gstreamer-pbutils-$GST_MAJORMINOR libdvbsi++ libpng libxml-2.0 sigc++-2.0 libssl libcrypto libcurl])
PKG_CHECK_MODULES(LIBDDVD, libdreamdvd, HAVE_LIBDDVD="yes", HAVE_LIBDDVD="no")
AM_CONDITIONAL(HAVE_LIBDDVD, test "$HAVE_LIBDDVD" = "yes")
PKG_CHECK_MODULES(AVAHI, avahi-client)

AC_CHECK_LIB([udfread], [udfread_init])
AC_CHECK_LIB([dl], [dlopen], [LIBDL_LIBS="-ldl"], [AC_MSG_ERROR([Could not find libdl])])
AC_SUBST(LIBDL_LIBS)
AC_CHECK_LIB([jpeg], [jpeg_set_defaults], [LIBJPEG_LIBS="-ljpeg"], [AC_MSG_ERROR([Could not find libjpeg])])
AC_SUBST(LIBJPEG_LIBS)
AC_CHECK_LIB([ungif], [DGifOpen], [LIBGIF_LIBS="-lungif"], [AC_CHECK_LIB([gif], [DGifOpen], [LIBGIF_LIBS="-lgif"], [AC_MSG_ERROR([Could not find libgif or libungif])])])
AC_SUBST(LIBGIF_LIBS)

AC_ARG_WITH(e2rev,
	AS_HELP_STRING([--with-e2rev],[value of E2REV, $withval]),
	[E2REV="$withval"],[E2REV=""])
AC_SUBST(E2REV)
AC_DEFINE_UNQUOTED(E2REV,"$E2REV",[enigma2 revision])

AC_ARG_WITH(oarev,
	AS_HELP_STRING([--with-oarev],[value of OAREV, $withval]),
	[OAREV="$withval"],[OAREV=""])
AC_SUBST(OAREV)
AC_DEFINE_UNQUOTED(OAREV,"$OAREV",[oa-core revision])

AC_ARG_WITH(boxtype,
	[  --with-boxtype=NAME box type [[none,dm800...]]],
	[BOXTYPE="$withval"],[BOXTYPE="dm800"])
AC_SUBST(BOXTYPE)
AC_DEFINE_UNQUOTED(BOXTYPE,"$BOXTYPE",[box type])

AC_ARG_WITH(machinebuild,
	[  --with-machinebuild=NAME machine build [[none,atemeo5200,atemeo6000...]]],
	[MACHINEBUILD="$withval"],[MACHINEBUILD="atemeo5200"])
AC_SUBST(MACHINEBUILD)
AC_DEFINE_UNQUOTED(MACHINEBUILD,"$MACHINEBUILD",[machine build])

AM_CONDITIONAL(DAGS, test `echo "$BOXTYPE" | cut -b 1-4` == "dags")
AM_CONDITIONAL(DREAMBOX, test `echo "$BOXTYPE" | cut -b 1-2` == "dm" -o `echo "$BOXTYPE" | cut -b 1-5` == "dream")
AM_CONDITIONAL(VUPLUS, test `echo "$BOXTYPE" | cut -b 1-2` == "vu")
AM_CONDITIONAL(XTREND, test `echo "$BOXTYPE" | cut -b 1-2` == "et")
AM_CONDITIONAL(TECHNOMATE, test `echo "$BOXTYPE" | cut -b 1-2` == "tm")
AM_CONDITIONAL(INI, test `echo "$BOXTYPE" | cut -b 1-3` == "ini")
AM_CONDITIONAL(IQON, test `echo "$BOXTYPE" | cut -b 1-4` == "iqon")
AM_CONDITIONAL(GIGABLUE, test `echo "$BOXTYPE" | cut -b 1-5` == "gb800")
AM_CONDITIONAL(ODIN, test `echo "$BOXTYPE" | cut -b 1-4` == "odin")
AM_CONDITIONAL(VENTON, test `echo "$BOXTYPE" | cut -b 1-6` == "venton")
AM_CONDITIONAL(EDISION, test `echo "$BOXTYPE" | cut -b 1-4` == "opti")
AM_CONDITIONAL(JEPSSEN, test `echo "$BOXTYPE" | cut -b 1-5` == "media")
AM_CONDITIONAL(SOGNO, test `echo "$BOXTYPE" | cut -b 1-5` == "sogno")
AM_CONDITIONAL(SKYLAKE, test `echo "$BOXTYPE" | cut -b 1-2` == "hd")
AM_CONDITIONAL(UNIBOXHDE, test "$BOXTYPE" == uniboxhde)
AM_CONDITIONAL(EVO, test `echo "$BOXTYPE" | cut -b 1-4` == "enfi")
AM_CONDITIONAL(MIRACLEBOX, test `echo "$BOXTYPE" | cut -b 1-2` == "mb")
AM_CONDITIONAL(DAGS1, test "$BOXTYPE" == dags1)
AM_CONDITIONAL(DAGS2, test "$BOXTYPE" == dags2)
AM_CONDITIONAL(DAGS3, test "$BOXTYPE" == dags3)
AM_CONDITIONAL(DAGS4, test "$BOXTYPE" == dags4)
AM_CONDITIONAL(DAGS5, test "$BOXTYPE" == dags5)
AM_CONDITIONAL(DM900, test "$BOXTYPE" == dm900)
AM_CONDITIONAL(DM920, test "$BOXTYPE" == dm920)
AM_CONDITIONAL(DM8000, test "$BOXTYPE" == dm8000)
AM_CONDITIONAL(DM7080, test "$BOXTYPE" == dm7080)
AM_CONDITIONAL(DM820, test "$BOXTYPE" == dm820)
AM_CONDITIONAL(DM520, test "$BOXTYPE" == dm520)
AM_CONDITIONAL(DM7020HD, test "$BOXTYPE" == dm7020hd)
AM_CONDITIONAL(DM7020HDV2, test "$BOXTYPE" == dm7020hdv2)
AM_CONDITIONAL(DM800, test "$BOXTYPE" == dm800)
AM_CONDITIONAL(DM800SE, test "$BOXTYPE" == dm800se)
AM_CONDITIONAL(DM800SEV2, test "$BOXTYPE" == dm800sev2)
AM_CONDITIONAL(DM500HD, test "$BOXTYPE" == dm500hd)
AM_CONDITIONAL(DM500HDV2, test "$BOXTYPE" == dm500hdv2)
AM_CONDITIONAL(DREAMONE, test "$BOXTYPE" == dreamone)
AM_CONDITIONAL(DREAMTWO, test "$BOXTYPE" == dreamtwo)
AM_CONDITIONAL(E3HD, test "$BOXTYPE" == e3hd)
AM_CONDITIONAL(VG1000, test "$BOXTYPE" == vg1000)
AM_CONDITIONAL(VG5000, test "$BOXTYPE" == vg5000)
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
AM_CONDITIONAL(ET8500S, test "$BOXTYPE" == et8500s)
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
AM_CONDITIONAL(GBULTRAUEH, test "$BOXTYPE" == gbultraueh)
AM_CONDITIONAL(GBQUADPLUS, test "$BOXTYPE" == gbquadplus)
AM_CONDITIONAL(GBQUAD, test "$BOXTYPE" == gbquad)
AM_CONDITIONAL(GB7252, test "$BOXTYPE" == gb7252)
AM_CONDITIONAL(GB72604, test "$BOXTYPE" == gb72604)
AM_CONDITIONAL(GBX1, test "$BOXTYPE" == gbx1)
AM_CONDITIONAL(GBX2, test "$BOXTYPE" == gbx2)
AM_CONDITIONAL(GBX3, test "$BOXTYPE" == gbx3)
AM_CONDITIONAL(GBX3H, test "$BOXTYPE" == gbx3h)
AM_CONDITIONAL(INIHDE, test "$BOXTYPE" == inihde)
AM_CONDITIONAL(INIHDP, test "$BOXTYPE" == inihdp)
AM_CONDITIONAL(INIHDX, test "$BOXTYPE" == inihdx)
AM_CONDITIONAL(IQONIOS100HD, test "$BOXTYPE" == iqonios100hd)
AM_CONDITIONAL(IQONIOS200HD, test "$BOXTYPE" == iqonios200hd)
AM_CONDITIONAL(IQONIOS300HD, test "$BOXTYPE" == iqonios300hd)
AM_CONDITIONAL(IQONIOS300HDV2, test "$BOXTYPE" == iqonios300hdv2)
AM_CONDITIONAL(MEDIABOX, test "$BOXTYPE" == mediabox)
AM_CONDITIONAL(MBTWIN, test "$BOXTYPE" == mbtwin)
AM_CONDITIONAL(MUTANT2400, test "$BOXTYPE" == mutant2400)
AM_CONDITIONAL(ODINM6, test "$BOXTYPE" == odinm6)
AM_CONDITIONAL(ODINM7, test "$BOXTYPE" == odinm7)
AM_CONDITIONAL(ODINM9, test "$BOXTYPE" == odinm9)
AM_CONDITIONAL(OSMIO4KPLUS, test "$BOXTYPE" == osmio4kplus)
AM_CONDITIONAL(QUADBOX2400, test "$BOXTYPE" == quadbox2400)
AM_CONDITIONAL(OPTIMUSSOS1, test "$BOXTYPE" == optimussos1)
AM_CONDITIONAL(OPTIMUSSOS2, test "$BOXTYPE" == optimussos2)
AM_CONDITIONAL(SOGNO8800HD, test "$BOXTYPE" == sogno8800hd)
AM_CONDITIONAL(S8100, test "$BOXTYPE" == 8100s)
AM_CONDITIONAL(PROTEK9900LX, test "$BOXTYPE" == 9900lx)
AM_CONDITIONAL(TMTWINOE, test "$BOXTYPE" == tmtwin)
AM_CONDITIONAL(TM2TOE, test "$BOXTYPE" == tm2t)
AM_CONDITIONAL(TMSINGLE, test "$BOXTYPE" == tmsingle)
AM_CONDITIONAL(TMNANO, test "$BOXTYPE" == tmnano)
AM_CONDITIONAL(TMNANO2T, test "$BOXTYPE" == tmnano2t)
AM_CONDITIONAL(TMNANOSE, test "$BOXTYPE" == tmnanose)
AM_CONDITIONAL(TMNANOSEM2, test "$BOXTYPE" == tmnanosem2)
AM_CONDITIONAL(TMNANOSEM2PLUS, test "$BOXTYPE" == tmnanosem2plus)
AM_CONDITIONAL(TIVIARMIN, test "$BOXTYPE" == tiviarmin)
AM_CONDITIONAL(VUUNO, test "$BOXTYPE" == vuuno)
AM_CONDITIONAL(VUULTIMO, test "$BOXTYPE" == vuultimo)
AM_CONDITIONAL(VUSOLO, test "$BOXTYPE" == vusolo)
AM_CONDITIONAL(VUSOLOSE, test "$BOXTYPE" == vusolose)
AM_CONDITIONAL(VUDUO, test "$BOXTYPE" == vuduo)
AM_CONDITIONAL(VUSOLO2, test "$BOXTYPE" == vusolo2)
AM_CONDITIONAL(VUSOLO4K, test "$BOXTYPE" == vusolo4k)
AM_CONDITIONAL(VUUNO4K, test "$BOXTYPE" == vuuno4k)
AM_CONDITIONAL(VUUNO4KSE, test "$BOXTYPE" == vuuno4kse)
AM_CONDITIONAL(VUULTIMO4K, test "$BOXTYPE" == vuultimo4k)
AM_CONDITIONAL(VUZERO4K, test "$BOXTYPE" == vuzero4k)
AM_CONDITIONAL(VUDUO2, test "$BOXTYPE" == vuduo2)
AM_CONDITIONAL(VUDUO4K, test "$BOXTYPE" == vuduo4k)
AM_CONDITIONAL(VUDUO4KSE, test "$BOXTYPE" == vuduo4kse)
AM_CONDITIONAL(VUZERO, test "$BOXTYPE" == vuzero)
AM_CONDITIONAL(VENTONHDX, test "$BOXTYPE" == ventonhdx)
AM_CONDITIONAL(XP1000, test "$BOXTYPE" == xp1000)
AM_CONDITIONAL(HAVE_COLORLCD3, test "$BOXTYPE" == dm7080)
AM_CONDITIONAL(HAVE_COLORLCD240, test "$BOXTYPE" == dreamtwo)
AM_CONDITIONAL(HAVE_COLORLCD2, test "$BOXTYPE" == dm800se -o "$BOXTYPE" == dm800sev2 -o "$BOXTYPE" == dm820)
AM_CONDITIONAL(HAVE_COLORLCD1, test "$BOXTYPE" == dm8000 -o "$BOXTYPE" == dm800 -o "$BOXTYPE" == dm7020hd -o "$BOXTYPE" == dm7020hdv2)
AM_CONDITIONAL(HAVE_GRAUTEC8000, test "$BOXTYPE" == dm8000)
AM_CONDITIONAL(HAVE_GRAUTEC70X0, test "$BOXTYPE" == dm7020hd -o "$BOXTYPE" == dm7020hdv2 -o "$BOXTYPE" == dm7080)
AM_CONDITIONAL(LCD_FRAMEBUFFER_MODE, test "$BOXTYPE" == et8500 -o "$BOXTYPE" == et8500s -o "$BOXTYPE" == 8100s)

AS_IF([test "$BOXTYPE" == "dreamone"],[AC_DEFINE(HWDREAMONE, 1,[dreamone])])
AS_IF([test "$BOXTYPE" == "dreamtwo"],[AC_DEFINE(HWDREAMTWO, 1,[dreamtwo])])
AS_IF([test "$BOXTYPE" == "dm8000"],[AC_DEFINE(HWDM8000, 1,[dm8000])])
AS_IF([test "$BOXTYPE" == "dm7020hd" -o "$BOXTYPE" == "dm7020hdv2"],[AC_DEFINE(HWDM7020HD, 1,[dm7020hd])])
AS_IF([test "$BOXTYPE" == "dm7080"],[AC_DEFINE(HWDM7080, 1,[dm7080])])
AS_IF([test "$BOXTYPE" == "dm820"],[AC_DEFINE(HWDM820, 1,[dm820])])
AS_IF([test "$BOXTYPE" == "dm520" -o "$BOXTYPE" == "dm525"],[AC_DEFINE(HWDM520, 1,[dm520])])
AS_IF([test "$BOXTYPE" == "dm900"],[AC_DEFINE(HWDM900, 1,[dm900])])
AS_IF([test "$BOXTYPE" == "dm920"],[AC_DEFINE(HWDM920, 1,[dm920])])
AS_IF([test "$BOXTYPE" == "dm800se"],[AC_DEFINE(HWDM800SE, 1,[dm800se])])
AS_IF([test "$BOXTYPE" == "dm500hd"],[AC_DEFINE(HWDM500HD, 1,[dm500hd])])
AS_IF([test "$BOXTYPE" == "dm800sev2"],[AC_DEFINE(HWDM800SEV2, 1,[dm800sev2])])
AS_IF([test "$BOXTYPE" == "dm500hdv2"],[AC_DEFINE(HWDM500HDV2, 1,[dm500hdv2])])
AS_IF([test "$BOXTYPE" == "vusolo4k"],[AC_DEFINE(HWVUSOLO4K, 1,[vusolo4k])])
AS_IF([test "$BOXTYPE" == "vuultimo4k"],[AC_DEFINE(HWULTIMO4K, 1,[vuultimo4k])])
AS_IF([test "$BOXTYPE" == "vuduo4k"],[AC_DEFINE(HWDUO4K, 1,[vuduo4k])])
AS_IF([test "$BOXTYPE" == "vuduo4kse"],[AC_DEFINE(HWDUO4KSE, 1,[vuduo4kse])])
AS_IF([test "$BOXTYPE" == "vuduo2"],[AC_DEFINE(HWDUO2, 1,[vuduo2])])
AS_IF([test "$BOXTYPE" == "vuuno4kse"],[AC_DEFINE(HWUNO4KSE, 1,[vuuno4kse])])
AS_IF([test "$BOXTYPE" == "h7"],[AC_DEFINE(HWH7, 1,[h7])])
AS_IF([test "$BOXTYPE" == "h17"],[AC_DEFINE(HWH17, 1,[h17])])
AS_IF([test "$BOXTYPE" == "pulse4k"],[AC_DEFINE(HWPULSE4K, 1,[pulse4k])])
AS_IF([test "$BOXTYPE" == "pulse4kmini"],[AC_DEFINE(HWPULSE4KMINI, 1,[pulse4kmini])])
AS_IF([test "$MACHINEBUILD" == "gbue4k"],[AC_DEFINE(HWGBUE4K, 1,[gbue4k])])
AS_IF([test "$MACHINEBUILD" == "gbtrio4kpro"],[AC_DEFINE(HWGBTRIO4KPRO, 1,[gbtrio4kpro])])
AS_IF([test "$MACHINEBUILD" == "gbquad4kpro"],[AC_DEFINE(HWGBQUAD4KPRO, 1,[gbquad4kpro])])
AS_IF([test "$MACHINEBUILD" == "beyonwizt2"],[AC_DEFINE(HWBEYONWIZT2, 1,[beyonwizt2])])
AS_IF([test "$MACHINEBUILD" == "gbquad4k"],[AC_DEFINE(HWGBQUAD4K, 1,[gbquad4k])])
AS_IF([test "$BOXTYPE" == "u5"],[AC_DEFINE(HWU5, 1,[u5])])
AS_IF([test "$BOXTYPE" == "hd51"],[AC_DEFINE(HWHD51, 1,[hd51])])
AS_IF([test "$BOXTYPE" == "hd61"],[AC_DEFINE(HWHD61, 1,[hd61])])
AS_IF([test "$BOXTYPE" == "sfx6008"],[AC_DEFINE(HWSFX6008, 1,[sfx6008])])
AS_IF([test "$BOXTYPE" == "osnino"],[AC_DEFINE(HWOSNINO, 1,[osnino])])
AS_IF([test "$BOXTYPE" == "h10"],[AC_DEFINE(HWH10, 1,[h10])])
AS_IF([test "$BOXTYPE" == "multiboxpro"],[AC_DEFINE(HWMULTIBOXPRO, 1,[multiboxpro])])
AS_IF([test "$BOXTYPE" == "sf8008"],[AC_DEFINE(HWSF8008, 1,[sf8008])])


AC_ARG_WITH(accelerationthreshold,
	AS_HELP_STRING([--with-accelerationthreshold=n], [use acceleration threshold of n bytes]),
	[[with_accelerationthreshold=$withval]],
	[[with_accelerationthreshold=48000]]
)

AC_DEFINE_UNQUOTED(GFX_SURFACE_ACCELERATION_THRESHOLD, $with_accelerationthreshold,[Configure threshold for accelerated surfaces (in bytes)])

AC_ARG_WITH(fillaccelerationthreshold,
	AS_HELP_STRING([--with-fillaccelerationthreshold=n], [use fill acceleration threshold of n bytes]),
	[[with_fillaccelerationthreshold=$withval]],
	[[with_fillaccelerationthreshold=80000]]
)

AC_DEFINE_UNQUOTED(GFX_SURFACE_FILL_ACCELERATION_THRESHOLD, $with_fillaccelerationthreshold,[Configure threshold for accelerated fill operations (in bytes)])

AC_ARG_WITH(blitaccelerationthreshold,
	AS_HELP_STRING([--with-blitaccelerationthreshold=n], [use blit acceleration threshold of n bytes]),
	[[with_blitaccelerationthreshold=$withval]],
	[[with_blitaccelerationthreshold=0]]
)

AC_DEFINE_UNQUOTED(GFX_SURFACE_BLIT_ACCELERATION_THRESHOLD, $with_blitaccelerationthreshold,[Configure threshold for accelerated blit operations (in bytes)])

AC_ARG_WITH(alphablendingacceleration,
	AS_HELP_STRING([--with-alphablendingacceleration=never/always/auto], [alphablending acceleration strategy: never accelerate / always accelerate / automatically decide when to accelerate (default)]),
	[[with_alphablendingacceleration=$withval]],
	[[with_alphablendingacceleration=auto]]
)

if test x"$with_alphablendingacceleration" = xnever ; then
	AC_DEFINE_UNQUOTED(FORCE_NO_BLENDING_ACCELERATION, 1, [Do not attempt to accelerate alphablending blits])
elif test x"$with_alphablendingacceleration" = xalways ; then
	AC_DEFINE_UNQUOTED(FORCE_ALPHABLENDING_ACCELERATION, 1, [Accelerate alphablending blits])
fi

AC_ARG_WITH(accelerationaccumulation,
	AS_HELP_STRING([--with-accelerationaccumulation], [accumulate blit/fill acceleration operations]),
	[[with_accelerationaccumulation=$withval]],
	[[with_accelerationaccumulation=no]]
)

if test x"$with_accelerationaccumulation" = xyes ; then
	AC_DEFINE(SUPPORT_ACCUMULATED_ACCELERATION_OPERATIONS, 1,[Accumulate blit/fill acceleration operations])
fi


AC_ARG_WITH(libvugles2,
	AS_HELP_STRING([--with-libvugles2],[use libvugles2, yes or no]),
	[with_libvugles2=$withval],[with_libvugles2=no])
if test "$with_libvugles2" = "yes"; then
	PKG_CHECK_MODULES(LIBVUGLES2, [libvugles2])
	GLES_CFLAGS="-DUSE_LIBVUGLES2"
fi
AM_CONDITIONAL(HAVE_LIBVUGLES2, test "$with_libvugles2" = "yes")

AC_ARG_WITH(libhiaccel,
	AS_HELP_STRING([--with-libhiaccel],[use libhiaccel, yes or no]),
	[with_libhiaccel=$withval],[with_libhiaccel=no])
if test "$with_libhiaccel" = "yes"; then
	PKG_CHECK_MODULES(LIBHIACCEL, [libhiaccel])
	HIACCEL_CFLAGS="-DUSE_LIBHIACCEL"
fi

if test x"$with_libhiaccel" != xno ; then
	AC_DEFINE(HAVE_HISILICON_ACCEL, 1,[define add HISILICON ACCEL])
fi

AC_ARG_WITH(osdanimation,
	AS_HELP_STRING([--with-osdanimation], [use osd animation, yes or no]),
	[[withosdanimation=$withval]],
	[[withosdanimation=no]]
)
if test x"$withosdanimation" != xno ; then

	AC_DEFINE(HAVE_OSDANIMATION, 1,[Define if driver supports animation of osd])
fi
AM_CONDITIONAL(HAVE_OSDANIMATION, test x"$withosdanimation" != xno)


if test `echo "$BOXTYPE" | cut -b 1-2` == "dm" -o `echo "$BOXTYPE" | cut -b 1-5` == "dream"; then
	AC_DEFINE(DREAMBOX, 1, [Dreambox hardware])
	AC_DEFINE(KEY_PLAY_ACTUALLY_IS_KEY_PLAYPAUSE, 1,[define when rc sends a KEY_PLAY event for its KEY_PLAYPAUSE key])
fi

AC_ARG_WITH(nolcd,
	AS_HELP_STRING([--with-nolcd], [disable ascii based lcd, yes or no]),
	[[withnolcd=$withval]],
	[[withnolcd=no]]
)
if test x"$withnolcd" != xno ; then
	AC_DEFINE(NO_LCD, 1,[Define when disable an ascii based lcd device])
fi
AM_CONDITIONAL(NO_LCD, test x"$withnolcd" != xno)

AC_ARG_WITH(textlcd,
	AS_HELP_STRING([--with-textlcd], [use ascii based lcd, yes or no]),
	[[withtextlcd=$withval]],
	[[withtextlcd=no]]
)
if test x"$withtextlcd" != xno ; then
	AC_DEFINE(HAVE_TEXTLCD, 1,[Define when using an ascii based lcd device])
fi
AM_CONDITIONAL(HAVE_TEXTLCD, test x"$withtextlcd" != xno)

AC_ARG_WITH(7segment,
	AS_HELP_STRING([--with-7segment], [use ascii based lcd, yes or no]),
	[[with7segment=$withval]],
	[[with7segment=no]]
)
if test x"$with7segment" != xno ; then
	AC_DEFINE(HAVE_7SEGMENT, 1,[Define when using an ascii based lcd device])
fi
AM_CONDITIONAL(HAVE_7SEGMENT, test x"$with7segment" != xno)

AC_ARG_WITH(bwlcd96,
	AS_HELP_STRING([--with-bwlcd96], [use 96x64 1bpp black and white display, yes or no]),
	[[withbwlcd96=$withval]],
	[[withbwlcd96=no]]
)
if test x"$withbwlcd96" != xno ; then
	AC_DEFINE(HAVE_BWLCD96, 1,[Define when using a 96x64 black and white display device])
fi
AM_CONDITIONAL(HAVE_BWLCD96, test x"$withbwlcd96" != xno)

AC_ARG_WITH(colorlcd,
	AS_HELP_STRING([--with-colorlcd], [use 96x64 16bpp color display, yes or no]),
	[[withcolorlcd=$withval]],
	[[withcolorlcd=no]]
)
if test x"$withcolorlcd" != xno ; then
	AC_DEFINE(HAVE_COLORLCD, 1,[Define when using a 96x64 color display device])
fi
AM_CONDITIONAL(HAVE_COLORLCD, test x"$withcolorlcd" != xno)

AC_ARG_WITH(colorlcd128,
	AS_HELP_STRING([--with-colorlcd128], [use 128x64 16bpp color display, yes or no]),
	[[withcolorlcd128=$withval]],
	[[withcolorlcd128=no]]
)
if test x"$withcolorlcd128" != xno ; then
	AC_DEFINE(HAVE_COLORLCD128, 1,[Define when using a 128x64 color display device])
fi
AM_CONDITIONAL(HAVE_COLORLCD128, test x"$withcolorlcd" != xno)

AC_ARG_WITH(colorlcd220,
	AS_HELP_STRING([--with-colorlcd220], [use 220x176 16bpp color display, yes or no]),
	[[withcolorlcd220=$withval]],
	[[withcolorlcd220=no]]
)
if test x"$withcolorlcd220" != xno ; then
	AC_DEFINE(HAVE_COLORLCD220, 1,[Define when using a 220x176 color display device])
fi
AM_CONDITIONAL(HAVE_COLORLCD220, test x"$withcolorlcd220" != xno)

AC_ARG_WITH(colorlcd240,
	AS_HELP_STRING([--with-colorlcd240], [use 240x80 16bpp color display, yes or no]),
	[[withcolorlcd240=$withval]],
	[[withcolorlcd240=no]]
)
if test x"$withcolorlcd240" != xno ; then
	AC_DEFINE(HAVE_COLORLCD240, 1,[Define when using a 240x80 color display device])
fi
AM_CONDITIONAL(HAVE_COLORLCD240, test x"$withcolorlcd240" != xno)

AC_ARG_WITH(colorlcd390,
	AS_HELP_STRING([--with-colorlcd390], [use 390x240 16bpp color display, yes or no]),
	[[withcolorlcd390=$withval]],
	[[withcolorlcd390=no]]
)
if test x"$withcolorlcd390" != xno ; then
	AC_DEFINE(HAVE_COLORLCD390, 1,[Define when using a 390x240 color display device])
fi

AM_CONDITIONAL(HAVE_COLORLCD390, test x"$withcolorlcd390" != xno)

AC_ARG_WITH(colorlcd400,
	AS_HELP_STRING([--with-colorlcd400], [use 400x176 16bpp color display, yes or no]),
	[[withcolorlcd400=$withval]],
	[[withcolorlcd400=no]]
)
if test x"$withcolorlcd400" != xno ; then
	AC_DEFINE(HAVE_COLORLCD400, 1,[Define when using a 400x176 color display device])
fi

AM_CONDITIONAL(HAVE_COLORLCD400, test x"$withcolorlcd400" != xno)

AC_ARG_WITH(colorlcd480,
	AS_HELP_STRING([--with-colorlcd480], [use 480x320 16bpp color display, yes or no]),
	[[withcolorlcd480=$withval]],
	[[withcolorlcd480=no]]
)
if test x"$withcolorlcd480" != xno ; then
	AC_DEFINE(HAVE_COLORLCD480, 1,[Define when using a 480x320 color display device])
fi

AM_CONDITIONAL(HAVE_COLORLCD480, test x"$withcolorlcd480" != xno)

AC_ARG_WITH(colorlcd720,
	AS_HELP_STRING([--with-colorlcd720], [use 720x576 16bpp color display, yes or no]),
	[[withcolorlcd720=$withval]],
	[[withcolorlcd720=no]]
)
if test x"$withcolorlcd720" != xno ; then
	AC_DEFINE(HAVE_COLORLCD720, 1,[Define when using a 720x576 color display device])
fi

AM_CONDITIONAL(HAVE_COLORLCD720, test x"$withcolorlcd720" != xno)

AC_ARG_WITH(colorlcd800,
	AS_HELP_STRING([--with-colorlcd800], [use 800x480 16bpp color display, yes or no]),
	[[withcolorlcd800=$withval]],
	[[withcolorlcd800=no]]
)
if test x"$withcolorlcd800" != xno ; then
	AC_DEFINE(HAVE_COLORLCD800, 1,[Define when using a 800x480 color display device])
fi

AM_CONDITIONAL(HAVE_COLORLCD800, test x"$withcolorlcd800" != xno)

AC_ARG_WITH(bwlcd255,
	AS_HELP_STRING([--with-bwlcd255], [use 255x64 1bpp black and white display, yes or no]),
	[[withbwlcd255=$withval]],
	[[withbwlcd255=no]]
)
if test x"$withbwlcd255" != xno ; then
	AC_DEFINE(HAVE_BWLCD255, 1,[Define when using a 255x64 black and white display device])
fi
AM_CONDITIONAL(HAVE_BWLCD255, test x"$withbwlcd255" != xno)

AC_ARG_WITH(bwlcd140,
	AS_HELP_STRING([--with-bwlcd140], [use 140x32 1bpp black and white display, yes or no]),
	[[withbwlcd140=$withval]],
	[[withbwlcd140=no]]
)
if test x"$withbwlcd140" != xno ; then
	AC_DEFINE(HAVE_BWLCD140, 1,[Define when using a 140x32 black and white display device])
fi
AM_CONDITIONAL(HAVE_BWLCD140, test x"$withbwlcd140" != xno)

AC_ARG_WITH(bwlcd128,
	AS_HELP_STRING([--with-bwlcd128], [use 128x32 1bpp black and white display, yes or no]),
	[[withbwlcd128=$withval]],
	[[withbwlcd128=no]]
)
if test x"$withbwlcd128" != xno ; then
	AC_DEFINE(HAVE_BWLCD128, 1,[Define when using a 128x32 black and white display device])
fi
AM_CONDITIONAL(HAVE_BWLCD128, test x"$withbwlcd128" != xno)

AC_ARG_WITH(fullgraphiclcd,
	AS_HELP_STRING([--with-fullgraphiclcd], [display right_half_vfd_icons from skin(for ultimo), yes or no]),
	[[withfullgraphiclcd=$withval]],
	[[withfullgraphiclcd=no]]
)
if test x"$withfullgraphiclcd" != xno ; then
	AC_DEFINE(HAVE_FULLGRAPHICLCD, 1,[Define when display right_half_vfd_icons from skin, for ultimo])
fi
AM_CONDITIONAL(HAVE_FULLGRAPHICLCD, test x"$withfullgraphiclcd" != xno)

AC_ARG_WITH(gigabluelcd,
	AS_HELP_STRING([--with-gigabluelcd], [use fix color map in color display, yes or no]),
	[[withgigabluelcd=$withval]],
	[[withgigabluelcd=no]]
)
if test x"$withgigabluelcd" != xno ; then
	AC_DEFINE(HAVE_GIGABLUELCD, 1,[Define when using a 220x176 color display device])
fi
AM_CONDITIONAL(HAVE_GIGABLUELCD, test x"$withgigabluelcd" != xno)

AC_ARG_WITH(alsa,
	AS_HELP_STRING([--with-alsa], [Enable ALSA support]),
	[[with_alse=$withval]],
	[[with_alse=no]]
)
if test x"$with_alsa" == xyes ; then
	AC_DEFINE(HAVE_ALSA, 1,[Enables ALSA support])
	PKG_CHECK_MODULES(ALSA, alsa)
fi

AC_ARG_WITH(alsacard,
	AS_HELP_STRING([--with-alsacard=card], [use 'card' for alsa card device, e.g. hw:0]),
	[[with_alsacard=$withval]],
	[[with_alsacard=no]]
)
if test x"$with_alsacard" != xno ; then
	AC_DEFINE_UNQUOTED(ALSA_CARD, "$withval",[Defines which alsa card to use])
fi

AC_ARG_WITH(alsamixer,
	AS_HELP_STRING([--with-alsamixer=mixername], [use alsa 'mixername' for volume control, e.g. Master]),
	[[with_alsamixer=$withval]],
	[[with_alsamixer=no]]
)
if test x"$with_alsamixer" != xno ; then
	AC_DEFINE_UNQUOTED(ALSA_VOLUME_MIXER, "$withval",[Defines which alsa mixer to use for volume control])
fi

AC_ARG_WITH(fbdev,
	AS_HELP_STRING([--with-fbdev=devicename], [use devicename for framebuffer device, e.g. /dev/fb0 ]),
	[[with_fbdev=$withval]],
	[[with_fbdev=no]]
)
if test x"$with_fbdev" != xno ; then
	AC_DEFINE_UNQUOTED(FB_DEV, "$withval", [Defines which device to use for main framebuffer (e.g. /dev/fb0)])
fi

AC_ARG_WITH(lcddev,
	AS_HELP_STRING([--with-lcddev=devicename], [use devicename for lcd framebuffer device, e.g. /dev/fb1 ]),
	[[with_lcddev=$withval]],
	[[with_lcddev=no]]
)
if test x"$with_lcddev" != xno ; then
	AC_DEFINE_UNQUOTED(LCD_DEV, "$withval", [Defines which device to use for lcd (e.g. /dev/fb1)])
fi

AC_ARG_WITH(amlogic,
	AS_HELP_STRING([--with-amlogic], [use amlogic MPEG decoder]),
	[[with_amlogic=$withval]],
	[[with_amlogic=no]]
)

FFMPEG_CFLAGS=" "

AM_CONDITIONAL(DREAMNEXTGEN, test "$BOXTYPE" == dreamone -o "$BOXTYPE" == dreamtwo)
if test "$BOXTYPE" == "dreamone" -o "$BOXTYPE" == "dreamtwo"; then
	ALSA_CFLAGS="-lasound"
	FFMPEG_CFLAGS=" -lavdevice -lavformat -lavcodec -lswresample -lswscale -lavutil -lm "
	#AC_DEFINE(DREAMNEXTGEN, 1, [Dreambox NexT Generation Hardware])
fi

AC_ARG_WITH(fcc,
	AS_HELP_STRING([--with-fcc], [add FCC system plugin]),
	[[with_fcc=$withval]],
	[[with_fcc=no]]
)
AM_CONDITIONAL(HAVE_FCC, test x"$with_fcc" = xyes)
if test x"$with_fcc" = xyes ; then
	AC_DEFINE(HAVE_FCC, 1,[add FCC system plugin])
fi

AC_ARG_WITH(subttxtabnormalptsdiffs,
	AS_HELP_STRING([--with-subttxtabnormalptsdiffs=n], [use n/90 msec diffs for subtitle and teletext abnormal pts]),
	[[with_subttxtabnormalptsdiffs=$withval]],
	[[with_subttxtabnormalptsdiffs=1800000]]
)

AC_DEFINE_UNQUOTED(SUBT_TXT_ABNORMAL_PTS_DIFFS, $with_subttxtabnormalptsdiffs,[Configure abnormal pts for subtitle and teletext])

if test "$BOXTYPE" == "dm7080" -o "$BOXTYPE" == "dm820" -o "$BOXTYPE" == "dm800se" -o "$BOXTYPE" == "dm800sev2" -o "$BOXTYPE" == "dm7020hd" -o "$BOXTYPE" == "dm7020hdv2" -o "$BOXTYPE" == "dreamone" -o "$BOXTYPE" == "dreamtwo" -o "$BOXTYPE" == "dm900" -o "$BOXTYPE" == "dm920"; then
	AC_DEFINE(DREAMBOX_DUAL_TUNER, 1,[define BOXTYPE DM7080])
fi

if test "$BOXTYPE" == "dm7080" -o "$BOXTYPE" == "dm820" -o "$BOXTYPE" == "dm900" -o "$BOXTYPE" == "dm920" -o "$BOXTYPE" == "dm520"; then
	AC_DEFINE(CONFIG_ION, 1,[define BOX use ION Allocator])
fi

if test "$BOXTYPE" == "vusolo4k" -o "$BOXTYPE" == "vuuno4k" -o "$BOXTYPE" == "vuuno4kse" -o "$BOXTYPE" == "vuultimo4k" -o "$BOXTYPE" == "vuzero4k" -o "$BOXTYPE" == "vuduo4k" -o "$BOXTYPE" == "vuduo4kse" -o "$BOXTYPE" == "sf8008" -o "$BOXTYPE" == "sf8008m" -o "$BOXTYPE" == "sx988" -o "$BOXTYPE" == "ip8" -o "$BOXTYPE" == "ustym4kpro" -o "$BOXTYPE" == "ustym4kottpremium" -o "$BOXTYPE" == "ustym4ks2ottx" -o "$BOXTYPE" == "gbmv200" -o "$BOXTYPE" == "beyonwizv2" -o "$BOXTYPE" == "viper4k" -o "$BOXTYPE" == "dagsmv200" -o "$BOXTYPE" == "og2ott4k" -o "$BOXTYPE" == "og2s4k" -o "$BOXTYPE" == "sfx6008" -o "$BOXTYPE" == "sx88v2"; then
	AC_DEFINE(VMSG_TYPE2, 1,[define vtuner_message type 2])
fi

if test "$BOXTYPE" == "vuzero" -o "$BOXTYPE" == "vuuno" -o "$BOXTYPE" == "vuultimo" -o "$BOXTYPE" == "vusolose" -o "$BOXTYPE" == "vusolo2" -o "$BOXTYPE" == "vusolo" -o "$BOXTYPE" == "vuduo2" -o "$BOXTYPE" == "vuduo"; then
	AC_DEFINE(FORCE_AUTO_INV, 1,[force Inversion auto for vu mipsel boxes])
fi

if test "$BOXTYPE" == "u5" -o "$BOXTYPE" == "u5pvr" -o "$BOXTYPE" == "u51" -o "$BOXTYPE" == "u52" -o "$BOXTYPE" == "u54" -o "$BOXTYPE" == "u55" -o "$BOXTYPE" == "u56" -o "$BOXTYPE" == "u57" -o "$BOXTYPE" == "u571" -o "$BOXTYPE" == "u41" -o "$BOXTYPE" == "u42" -o "$BOXTYPE" == "u43" -o "$BOXTYPE" == "u45"; then
	AC_DEFINE(HAVE_HISILICON, 1,[define add HISILICON chip])
	AC_DEFINE(KEY_F6_TO_KEY_VIDEO, 1,[define when rc VIDEO key sends a KEY_F6 event for its KEY_VIDEO key])
fi

if test "$BOXTYPE" == "u41" -o "$BOXTYPE" == "u42" -o "$BOXTYPE" == "u43" -o "$BOXTYPE" == "u45"; then
	AC_DEFINE(USE_VIDEO_MODE_HD, 1,[define use valid Video Modes])
fi

if test "$BOXTYPE" == "u53" -o "$BOXTYPE" == "u532" -o "$BOXTYPE" == "u533"; then
	AC_DEFINE(KEY_F6_TO_KEY_FAVORITES, 1,[define when rc FAV key sends a KEY_F6 event for its KEY_FAVORITES key])
	AC_DEFINE(KEY_CONTEXT_MENU_TO_KEY_BACK, 1,[define when rc MOUSE key sends a KEY_CONTEXT_MENU event for its KEY_BACK key])
	AC_DEFINE(KEY_WWW_TO_KEY_FILE, 1,[define when rc HOME key sends a KEY_WWW event for its KEY_FILE key])
	AC_DEFINE(KEY_HELP_TO_KEY_AUDIO, 1,[define when rc SETTINGS key sends a KEY_HELP event for its KEY_AUDIO key])
	AC_DEFINE(HAVE_HISILICON, 1,[define add HISILICON chip])
fi

if test "$BOXTYPE" == "sf8008" -o "$BOXTYPE" == "sf8008m" -o "$BOXTYPE" == "sx988" -o "$BOXTYPE" == "ip8" -o "$BOXTYPE" == "ustym4kpro" -o "$BOXTYPE" == "ustym4kottpremium" -o "$BOXTYPE" == "ustym4ks2ottx" -o "$BOXTYPE" == "gbmv200" -o "$BOXTYPE" == "beyonwizv2" -o "$BOXTYPE" == "viper4k" -o "$BOXTYPE" == "dagsmv200" -o "$BOXTYPE" == "og2ott4k" -o "$BOXTYPE" == "og2s4k" -o "$BOXTYPE" == "sfx6008" -o "$BOXTYPE" == "sx88v2"; then
	AC_DEFINE(HAVE_HISILICON, 1,[define add HISILICON chip])
	AC_DEFINE(CONFIG_HISILICON_FB, 1,[define add HISILICON framebuffer blit])
	AC_DEFINE(FORCE_ALPHABLENDING_ACCELERATION, 1,[define when the framebuffer acceleration has alphablending support, but detection slow down all])
fi

if test "$BOXTYPE" == "et4x00" -o "$BOXTYPE" == "et5x00" -o "$BOXTYPE" == "et6x00" -o "$BOXTYPE" == "et7x00" -o "$BOXTYPE" == "et9x00" -o "$BOXTYPE" == "et8000" -o "$BOXTYPE" == "et8500" -o "$BOXTYPE" == "et8500s" -o "$BOXTYPE" == "et10000"; then
	AC_DEFINE(KEY_PLAY_ACTUALLY_IS_KEY_PLAYPAUSE, 1,[define when rc sends a KEY_PLAY event for its KEY_PLAYPAUSE key])
	AC_DEFINE(KEY_F3_TO_KEY_LIST, 1,[define when rc sends a KEY_F3 event for its KEY_LIST key])
fi

if test "$BOXTYPE" == "et8500" -o "$BOXTYPE" == "et8500s"; then
	AC_DEFINE(FORCE_ALPHABLENDING_ACCELERATION, 1,[define when the framebuffer acceleration has alphablending support, but detection slow down all])
	AC_DEFINE(LCD_FRAMEBUFFER_MODE, 1,[define the framebuffer LCD mode])
fi

if test "$BOXTYPE" == "ultramini" -o "$BOXTYPE" == "et1x000" -o "$BOXTYPE" == "et7x00"; then
	AC_DEFINE(KEY_F1_TO_KEY_F2, 1,[define when rc sends a KEY_F1 event for its KEY_F2 key])
	AC_DEFINE(FORCE_ALPHABLENDING_ACCELERATION, 1,[define when the framebuffer acceleration has alphablending support, but detection slow down all])
fi

if test "$BOXTYPE" == "9900lx"; then
	AC_DEFINE(KEY_F1_TO_KEY_F2, 1,[define when rc sends a KEY_F1 event for its KEY_F2 key])
	AC_DEFINE(FORCE_ALPHABLENDING_ACCELERATION, 1,[define when the framebuffer acceleration has alphablending support, but detection slow down all])
fi

if test "$BOXTYPE" == "g300" -o "$BOXTYPE" == "g100" -o "$BOXTYPE" == "sf4008" -o "$BOXTYPE" == "g101" -o "$BOXTYPE" == "et1x000"; then
	AC_DEFINE(FORCE_ALPHABLENDING_ACCELERATION, 1,[define when the framebuffer acceleration has alphablending support, but detection slow down all])
fi

if test "$BOXTYPE" == "et13000"; then
	AC_DEFINE(KEY_PLAY_ACTUALLY_IS_KEY_PLAYPAUSE, 1,[define when rc sends a KEY_PLAY event for its KEY_PLAYPAUSE key])
	AC_DEFINE(KEY_BOOKMARKS_IS_KEY_DIRECTORY, 1,[define when rc sends a KEY_BOOKMARKS but other box use this key for different mapping we remap to KEY_DIRECTORY])
	AC_DEFINE(FORCE_ALPHABLENDING_ACCELERATION, 1,[define when the framebuffer acceleration has alphablending support, but detection slow down all])
fi

if test "$BOXTYPE" == "xc7362" -o "$BOXTYPE" == "xc7346" -o "$BOXTYPE" == "xc7439"; then
	AC_DEFINE(KEY_MEDIA_TO_KEY_LIST, 1,[define MEDIA to LIST])
fi

if test "$BOXTYPE" == "osnino" -o "$BOXTYPE" == "osninoplus" -o "$BOXTYPE" == "osninopro" -o "$BOXTYPE" == "osmio4k" -o "$BOXTYPE" == "osmio4kplus" -o "$BOXTYPE" == "osmini4k"; then
	AC_DEFINE(KEY_MEDIA_TO_KEY_LIST, 1,[define MEDIA to LIST])
	AC_DEFINE(KEY_VIDEO_TO_KEY_ANGLE, 1,[define VIDEO to ANGLE])
fi

if test "$BOXTYPE" == "osmio4k" -o "$BOXTYPE" == "osmio4kplus" -o "$BOXTYPE" == "osmini4k"; then
	AC_DEFINE(KEY_PLAY_ACTUALLY_IS_KEY_PLAYPAUSE, 1,[define when rc sends a KEY_PLAY event for its KEY_PLAYPAUSE key])
fi

if test "$BOXTYPE" == "hd2400" -o "$BOXTYPE" == "hd11" -o "$BOXTYPE" == "hd1100" -o "$BOXTYPE" == "hd1200" -o "$BOXTYPE" == "hd500c" -o "$BOXTYPE" == "hd530c" -o "$BOXTYPE" == "hd1265" -o "$BOXTYPE" == "hd1500" -o "$BOXTYPE" == "hd51" -o "$BOXTYPE" == "hd60" -o "$BOXTYPE" == "hd61" -o "$BOXTYPE" == "hd66se" -o "$BOXTYPE" == "pulse4k" -o "$BOXTYPE" == "pulse4kmini" -o "$BOXTYPE" == "hd52" -o "$BOXTYPE" == "vs1000" -o "$BOXTYPE" == "vs1500"; then
	AC_DEFINE(KEY_PLAY_ACTUALLY_IS_KEY_PLAYPAUSE, 1,[define when rc sends a KEY_PLAY event for its KEY_PLAYPAUSE key])
	AC_DEFINE(KEY_F3_TO_KEY_LIST, 1,[define when rc sends a KEY_F3 event for its KEY_LIST key])
fi

if test "$BOXTYPE" == "formuler1" -o "$BOXTYPE" == "formuler3" -o "$BOXTYPE" == "formuler4" -o "$BOXTYPE" == "formuler4turbo" -o "$BOXTYPE" == "triplex" -o "$BOXTYPE" == "sf108" -o "$BOXTYPE" == "ultrabox" -o "$BOXTYPE" == "formuler1tc" -o "$BOXTYPE" == "formuler3ip" -o "$BOXTYPE" == "formuler4ip"; then
	AC_DEFINE(KEY_F3_TO_KEY_LIST, 1,[define when rc sends a KEY_F3 event for its KEY_LIST key])
	AC_DEFINE(KEY_LAST_TO_KEY_BACK, 1,[define when rc sends a KEY_LAST event for its KEY_BACK key])
	AC_DEFINE(KEY_BOOKMARKS_TO_KEY_MEDIA, 1,[define when rc Playlist sends a KEY_BOOKMARKS event for its KEY_MEDIA key])
	AC_DEFINE(KEY_VIDEO_TO_KEY_FAVORITES, 1,[define when rc FAV key sends a KEY_VIDEO event for its KEY_FAVORITES key])
fi

if test "$BOXTYPE" == "tiviarmin" ; then
	AC_DEFINE(TIVIARRC, 1,[define use TIVIARRC KEY MAPPING])
fi

if test "$BOXTYPE" == "ew7358" -o "$BOXTYPE" == "ew7362"; then
	AC_DEFINE(KEY_PLAY_ACTUALLY_IS_KEY_PLAYPAUSE, 1,[define when rc sends a KEY_PLAY event for its KEY_PLAYPAUSE key])
	AC_DEFINE(KEY_MEDIA_TO_KEY_LIST, 1,[define when rc sends a KEY_MEDIA event for its KEY_LIST key])
fi

if test "$BOXTYPE" == "ew7356" ; then
	AC_DEFINE(KEY_PLAY_ACTUALLY_IS_KEY_PLAYPAUSE, 1,[define when rc sends a KEY_PLAY event for its KEY_PLAYPAUSE key])
fi

if test "$BOXTYPE" == "sh1" -o "$BOXTYPE" == "lc"; then
	AC_DEFINE(KEY_PLAY_ACTUALLY_IS_KEY_PLAYPAUSE, 1,[define when rc sends a KEY_PLAY event for its KEY_PLAYPAUSE key])
fi

if test "$BOXTYPE" == "7000s" -o "$BOXTYPE" == "7100s" -o "$BOXTYPE" == "7105s" -o "$BOXTYPE" == "7200s" -o "$BOXTYPE" == "7205s" -o "$BOXTYPE" == "7210s" -o "$BOXTYPE" == "7215s" -o "$BOXTYPE" == "7300s" -o "$BOXTYPE" == "7400s"; then
	AC_DEFINE(KEY_PLAY_ACTUALLY_IS_KEY_PLAYPAUSE, 1,[define when rc sends a KEY_PLAY event for its KEY_PLAYPAUSE key])
	AC_DEFINE(LCD_COLOR_BITORDER_RGB565, 1,[define if lcd uses RGB565 bitorder])
fi

if test "$BOXTYPE" == "8100s"; then
	AC_DEFINE(KEY_VIDEO_TO_KEY_BOOKMARKS, 1,[define when rc sends a KEY_VIDEO event for its KEY_BOOKMARKS])
	AC_DEFINE(LCD_FRAMEBUFFER_MODE, 1,[define the framebuffer LCD mode])
fi

if test "$MACHINEBUILD" == "e4hd" -o "$MACHINEBUILD" == "e4hdhybrid"; then
	AC_DEFINE(KEY_POWER2_TO_KEY_WWW, 1,[define when rc sends a KEY_POWER2 event for its KEY_WWW key])
	AC_DEFINE(KEY_DIRECTORY_TO_KEY_FILE, 1,[define when rc sends a KEY_DIRECTORY event for its KEY_FILE key])
fi

if test "$MACHINEBUILD" == "beyonwizv2" -o "$MACHINEBUILD" == "beyonwizu4" -o "$MACHINEBUILD" == "beyonwizt2" -o "$MACHINEBUILD" == "beyonwizt3" -o "$MACHINEBUILD" == "beyonwizt4"; then
	AC_DEFINE(AUSTRALIA, 1,[define AUSTRALIA to enable country config])
fi

if test "$BOXTYPE" == "odinm9"; then
	AC_DEFINE(KEY_PLAY_ACTUALLY_IS_KEY_PLAYPAUSE, 1,[define when rc sends a KEY_PLAY event for its KEY_PLAYPAUSE key])
	AC_DEFINE(FORCE_NO_BLENDING_ACCELERATION, 1,[define when the framebuffer acceleration does not have alphablending support, though the autodetection might indicate that it does])
fi

if test "$BOXTYPE" == "odinm7" ; then
	AC_DEFINE(FORCE_ALPHABLENDING_ACCELERATION, 1,[define when the framebuffer acceleration has alphablending support, but detection slow down all])
	AC_DEFINE(KEY_POWER2_TO_KEY_WWW, 1,[define when rc sends a KEY_POWER2 event for its KEY_WWW key])
	AC_DEFINE(KEY_DIRECTORY_TO_KEY_FILE, 1,[define when rc sends a KEY_DIRECTORY event for its KEY_FILE key])
fi

if test "$BOXTYPE" == "e3hd"; then
	AC_DEFINE(FORCE_ALPHABLENDING_ACCELERATION, 1,[define when the framebuffer acceleration has alphablending support, but detection slow down all])
	AC_DEFINE(KEY_POWER2_TO_KEY_WWW, 1,[define when rc sends a KEY_POWER2 event for its KEY_WWW key])
	AC_DEFINE(KEY_DIRECTORY_TO_KEY_FILE, 1,[define when rc sends a KEY_DIRECTORY event for its KEY_FILE key])
fi

if test "$BOXTYPE" == "vuduo" -o "$BOXTYPE" == "vusolo" -o "$BOXTYPE" == "vuduo2" -o "$BOXTYPE" == "vusolo2" -o "$BOXTYPE" == "vuuno" -o "$BOXTYPE" == "vuultimo" -o "$BOXTYPE" == "vusolose" -o "$BOXTYPE" == "vuzero" -o "$BOXTYPE" == "vusolo4k" -o "$BOXTYPE" == "vuuno4k" -o "$BOXTYPE" == "vuuno4kse" -o "$BOXTYPE" == "vuultimo4k" -o "$BOXTYPE" == "vuzero4k" -o "$BOXTYPE" == "vuduo4k" -o "$BOXTYPE" == "vuduo4kse"; then
	AC_DEFINE(FORCE_NO_BLENDING_ACCELERATION, 1,[define when the framebuffer acceleration does not have alphablending support, though the autodetection might indicate that it does])
	AC_DEFINE(FORCE_ADVANCED_REMOTE, 1,[define to fixup the input device identification when the remote control is actually an 'advanced' remote (with play/forward/rewind keys)])
	AC_DEFINE(KEY_HELP_TO_KEY_INFO, 1,[define when rc sends a KEY_HELP event we need KEY_INFO])
	AC_DEFINE(KEY_INFO_TO_KEY_EPG, 1,[define when rc sends a KEY_INFO event for its KEY_EPG key])
	AC_DEFINE(KEY_EDIT_TO_KEY_TIME, 1,[define when rc sends a KEY_TIME event for its KEY_EDIT key])
fi

if test "$BOXTYPE" == "vp7358ci" ; then
	AC_DEFINE(FORCE_ADVANCED_REMOTE, 1,[define to fixup the input device identification when the remote control is actually an 'advanced' remote (with play/forward/rewind keys)])
	AC_DEFINE(KEY_HELP_TO_KEY_INFO, 1,[define when rc sends a KEY_HELP event we need KEY_INFO])
	AC_DEFINE(KEY_INFO_TO_KEY_EPG, 1,[define when rc sends a KEY_INFO event for its KEY_EPG key])
fi

if test "$BOXTYPE" == "gb800solo" -o "$BOXTYPE" == "gb800se" -o "$BOXTYPE" == "gb800ue" -o "$BOXTYPE" == "gbquad" -o "$BOXTYPE" == "gb800seplus" -o "$BOXTYPE" == "gb800ueplus" -o "$BOXTYPE" == "gbquadplus" -o "$BOXTYPE" == "gbipbox" -o "$BOXTYPE" == "gbultrase" -o "$BOXTYPE" == "gbultraue" -o "$BOXTYPE" == "gbultraueh" -o "$BOXTYPE" == "gbx1" -o "$BOXTYPE" == "gbx2" -o "$BOXTYPE" == "gbx3" -o "$BOXTYPE" == "gbx3h" -o "$BOXTYPE" == "gb7358" -o "$BOXTYPE" == "gb7325" -o "$BOXTYPE" == "gb7362" -o "$BOXTYPE" == "gb73625" -o "$BOXTYPE" == "gb7356" ; then
	AC_DEFINE(KEY_PLAY_ACTUALLY_IS_KEY_PLAYPAUSE, 1,[define when rc sends a KEY_PLAY event for its KEY_PLAYPAUSE key])
	AC_DEFINE(KEY_GUIDE_TO_KEY_EPG, 1,[define when rc sends a KEY_HELP event for its KEY_EPG key])
	AC_DEFINE(KEY_F2_TO_KEY_F6, 1,[define when rc sends a KEY_F2 event for its KEY_F6 key])
	AC_DEFINE(KEY_SCREEN_TO_KEY_MODE, 1,[define when rc sends a KEY_MODE event for its KEY_ASPECT key])
	AC_DEFINE(KEY_HOME_TO_KEY_UNKNOWN, 1,[define when rc sends a KEY_UNKNOWN event for its KEY_HOME key])
fi

if test "$BOXTYPE" == "gb7252" -o "$BOXTYPE" == "gb72604"; then
	AC_DEFINE(KEY_PLAY_ACTUALLY_IS_KEY_PLAYPAUSE, 1,[define when rc sends a KEY_PLAY event for its KEY_PLAYPAUSE key])
	AC_DEFINE(KEY_GUIDE_TO_KEY_EPG, 1,[define when rc sends a KEY_HELP event for its KEY_EPG key])
	AC_DEFINE(KEY_F2_TO_KEY_F6, 1,[define when rc sends a KEY_F2 event for its KEY_F6 key])
	AC_DEFINE(KEY_SCREEN_TO_KEY_MODE, 1,[define when rc sends a KEY_MODE event for its KEY_ASPECT key])
	AC_DEFINE(KEY_CONTEXT_MENU_TO_KEY_AUX, 1,[define when rc sends a KEY_CONTEXT_MENU event for its KEY_AUX key])
	AC_DEFINE(VIDEO_MODE_50, 1,[gigablue workaround for wrong videomode proc])
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

if test "$MACHINEBUILD" == "bwidowx"; then
	AC_DEFINE(FORCE_NO_BLENDING_ACCELERATION, 1,[define when the framebuffer acceleration does not have alphablending support, though the autodetection might indicate that it does])
	AC_DEFINE(KEY_ZOOM_TO_KEY_SCREEN, 1,[define when rc sends a KEY_ZOOM event for its KEY_SCREEN key])
	AC_DEFINE(KEY_LAST_TO_KEY_PVR, 1,[define when rc sends a KEY_LAST event for its KEY_PVR key])
fi

if test "$BOXTYPE" == "vg1000" -o "$BOXTYPE" == "vg2000" -o "$BOXTYPE" == "vg5000"; then
	AC_DEFINE(KEY_PLAY_ACTUALLY_IS_KEY_PLAYPAUSE, 1,[define when rc sends a KEY_PLAY event for its KEY_PLAYPAUSE key])
	AC_DEFINE(KEY_F3_TO_KEY_LIST, 1,[define when rc sends a KEY_F3 event for its KEY_LIST key])
fi

if test "$BOXTYPE" == "blackbox7405"; then
	AC_DEFINE(FORCE_ADVANCED_REMOTE, 1,[define to fixup the input device identification when the remote control is actually an 'advanced' remote (with play/forward/rewind keys)])
	AC_DEFINE(KEY_PLAY_IS_KEY_PLAYPAUSE, 1,[define when rc sends a KEY_PLAY event for its KEY_PLAYPAUSE key])
	AC_DEFINE(KEY_MEDIA_TO_KEY_BOOKMARKS, 1,[define when rc sends a KEY_MEDIA event for its KEY_BOOKMARKS key])
	AC_DEFINE(KEY_VIDEO_IS_KEY_SCREEN, 1,[define when rc sends a KEY_VIDEO event for its KEY_SCREEN key])
	AC_DEFINE(KEY_ARCHIVE_TO_KEY_DIRECTORY, 1,[define when rc sends a KEY_MEDIA event for its KEY_BOOKMARKS key])
	AC_DEFINE(KEY_TIME_TO_KEY_SLOW, 1,[define when rc sends a KEY_TOME event for its KEY_SLOW key])
fi

if test "$BOXTYPE" == "dags7335" -o "$BOXTYPE" == "dags7356" -o "$BOXTYPE" == "dags7362" -o "$BOXTYPE" == "dags73625" -o "$BOXTYPE" == "dags7252" -o "$BOXTYPE" == "dags72604"; then
	AC_DEFINE(HAVE_LINUXSOCKADDR, 1,[define it use sockaddr_un instead of sockaddr_in on linux domain socket.])
	AC_DEFINE(FORCE_NO_BLENDING_ACCELERATION, 1,[define when the framebuffer acceleration does not have alphablending support, though the autodetection might indicate that it does])
	AC_DEFINE(FORCE_ADVANCED_REMOTE, 1,[define to fixup the input device identification when the remote control is actually an 'advanced' remote (with play/forward/rewind keys)])
fi

if test "$BOXTYPE" == "dags7335" -o "$BOXTYPE" == "dags7356"; then
	AC_DEFINE(KEY_F1_TO_KEY_PC, 1,[define when rc sends a KEY_F1 event for its KEY_PC key])
	AC_DEFINE(KEY_F5_TO_KEY_ANGLE, 1,[define when rc sends a KEY_F5 event for its KEY_ANGLE key])
	AC_DEFINE(KEY_DOT_TO_KEY_HOMEPAGE, 1,[define when rc sends a KEY_DOT event for its KEY_KEY_HOMEPAGE key])
	AC_DEFINE(KEY_MEDIA_TO_KEY_KEY_F2, 1,[define when rc sends a KEY_MEDIA event for its KEY_KEY_F1 key])
fi

if test "$BOXTYPE" == "gb800solo" -o "$BOXTYPE" == "gb800se" -o "$BOXTYPE" == "gb800ue"; then
	AC_DEFINE(HAVE_NO_RTC, 1,[enable no RTC stuff])
fi

if test "$BOXTYPE" == "dm7080" -o "$BOXTYPE" == "dm820" -o "$BOXTYPE" == "dm900" -o "$BOXTYPE" == "dm920"; then
	AC_DEFINE(HAVE_HDMIIN_DM, 1,[has hdmi in dm])
fi

if test "$BOXTYPE" == "dm900" -o "$BOXTYPE" == "dm920"; then
	AC_DEFINE(LCD_DM900_Y_OFFSET, 4,[define LCD Y offset for dm900 and dm920])
	AC_DEFINE(HAVE_DM_FBC, 1,[define for dm900 and dm920])
fi

if test "$BOXTYPE" == "sf4008" -o "$BOXTYPE" == "beyonwizu4"; then
	AC_DEFINE(LCD_SCROLL_HEX, 1,[define LCD scroll values in hex])
fi

AS_IF([test "$MACHINEBUILD" == "classm" -o "$MACHINEBUILD" == "axodin" -o "$MACHINEBUILD" == "axodinc" -o "$MACHINEBUILD" == "starsatlx" -o "$MACHINEBUILD" == "evo" -o "$MACHINEBUILD" == "genius" -o "$MACHINEBUILD" == "galaxym6"],[AC_DEFINE(PROFILE1, 1,[profile1])])
AS_IF([test "$MACHINEBUILD" == "gb800solo" -o "$MACHINEBUILD" == "gb800se" -o "$MACHINEBUILD" == "gb800seplus" -o "$MACHINEBUILD" == "gbultrase"],[AC_DEFINE(PROFILE2, 1,[profile2])])
AS_IF([test "$MACHINEBUILD" == "osmini" -o "$MACHINEBUILD" == "spycatmini" -o "$MACHINEBUILD" == "osminiplus" -o "$MACHINEBUILD" == "spycatminiplus"],[AC_DEFINE(PROFILE3, 1,[profile3])])
AS_IF([test "$MACHINEBUILD" == "xpeedlx3" -o "$MACHINEBUILD" == "sezammarvel" -o "$MACHINEBUILD" == "atemionemesis"],[AC_DEFINE(PROFILE4, 1,[profile4])])

# VFD Symbols Poll Time
if test "$MACHINEBUILD" == "9910lx" -o "$MACHINEBUILD" == "9911lx" -o "$MACHINEBUILD" == "9920lx" -o "$MACHINEBUILD" == "dm7020hd" -o "$MACHINEBUILD" == "dm7020hdv2" -o "$MACHINEBUILD" == "dual" -o "$MACHINEBUILD" == "e4hd" -o "$MACHINEBUILD" == "e4hdhybrid" -o "$MACHINEBUILD" == "force3uhd" -o "$MACHINEBUILD" == "mbmicro" -o "$MACHINEBUILD" == "mbmicrov2" -o "$MACHINEBUILD" == "osnino" -o "$MACHINEBUILD" == "osninoplus" -o "$MACHINEBUILD" == "osninopro" -o "$MACHINEBUILD" == "revo4k" -o "$MACHINEBUILD" == "tmtwin4k" -o "$BOXTYPE" == "beyonwizv2" -o "$BOXTYPE" == "dags7362" -o "$BOXTYPE" == "dags73625" -o "$BOXTYPE" == "gbmv200" -o "$BOXTYPE" == "sf8008" -o "$BOXTYPE" == "sf8008m" -o "$BOXTYPE" == "sfx6008" -o "$BOXTYPE" == "sx888" -o "$BOXTYPE" == "sx88v2" -o "$BOXTYPE" == "ustym4kpro" -o "$BOXTYPE" == "ustym4ks2ottx" -o "$BOXTYPE" == "viper4k"; then
	AC_DEFINE(VFDSymbolsPoll, 1,[define VFD Symbols Poll])
else
	if test "$BOXTYPE" == "u41" -o "$MACHINEBUILD" == "alphatriple" -o "$MACHINEBUILD" == "atemio5x00" -o "$MACHINEBUILD" == "beyonwizt3" -o "$MACHINEBUILD" == "et7500" -o "$MACHINEBUILD" == "maram9" -o "$MACHINEBUILD" == "mbmini" -o "$MACHINEBUILD" == "mbtwin" -o "$MACHINEBUILD" == "osmega" -o "$MACHINEBUILD" == "osminiplus" -o "$MACHINEBUILD" == "sezam1000hd" -o "$MACHINEBUILD" == "sezam5000hd" -o "$MACHINEBUILD" == "sf3038" -o "$MACHINEBUILD" == "spycat" -o "$MACHINEBUILD" == "spycat4kmini" -o "$MACHINEBUILD" == "uniboxhd1" -o "$MACHINEBUILD" == "uniboxhd2" -o "$MACHINEBUILD" == "uniboxhd3"; then
		AC_DEFINE(VFDSymbolsPoll, 5,[define VFD Symbols Poll])
	else
		AC_DEFINE(VFDSymbolsPoll, 0,[define VFD Symbols Poll])
	fi
fi

AC_ARG_WITH(libsdl,
	AS_HELP_STRING([--with-libsdl],[use libsdl, yes or no]),
	[with_libsdl=$withval],[with_libsdl=no])
if test "$with_libsdl" = "yes"; then
	PKG_CHECK_MODULES(LIBSDL, sdl2)
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
	AC_DEFINE([DEBUG],[1],[Define to 1 to enable debugging code])
fi

AC_ARG_WITH(memcheck,
	AS_HELP_STRING([--with-memcheck],[enable memory leak checks]),
	[with_memcheck="$withval"],[with_memcheck="no"])
if test "$with_memcheck" = "yes"; then
	AC_DEFINE([MEMLEAK_CHECK],[1],[Define to 1 to enable memory leak checks])
fi

AC_ARG_WITH(po,
	AS_HELP_STRING([--with-po],[enable updating of po files]),
	[with_po="$withval"],[with_po="no"])
AM_CONDITIONAL(UPDATE_PO, test "$with_po" = "yes")

ENIGMA2_CFLAGS="-fno-rtti -fno-exceptions -rdynamic -funwind-tables"
AC_SUBST(ENIGMA2_CFLAGS)

CPPFLAGS="$CPPFLAGS $PYTHON_CPPFLAGS"
CFLAGS="$CFLAGS -Wall"

CXXFLAGS="$CXXFLAGS -Wall $BASE_CFLAGS $ENIGMA2_CFLAGS $PTHREAD_CFLAGS $OPENMP_CFLAGS $GLES_CFLAGS $ALSA_CFLAGS $FFMPEG_CFLAGS"

AX_SWIG_PYTHON_OPT="$AX_SWIG_PYTHON_OPT -DSWIG_PYTHON_LEGACY_BOOL"

AC_CONFIG_FILES([
Makefile
data/Makefile
data/icons/Makefile
data/fonts/Makefile
data/keymaps/Makefile
data/7segment/Makefile
data/displaytext/Makefile
data/display96/Makefile
data/display128/Makefile
data/display128dm/Makefile
data/display220/Makefile
data/display240/Makefile
data/display390/Makefile
data/display400/Makefile
data/display480/Makefile
data/display720/Makefile
data/display800/Makefile
data/display800/Default_with_Picon_Fullscreen/Makefile
data/grautec70x0/Makefile
data/grautec70x0/fonts/Makefile
data/grautec8000/Makefile
data/grautec8000/fonts/Makefile
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
lib/python/Plugins/Extensions/AtileHD/Makefile
lib/python/Plugins/Extensions/AtileHD/pic/Makefile
lib/python/Plugins/Extensions/CutListEditor/Makefile
lib/python/Plugins/Extensions/DVDBurn/Makefile
lib/python/Plugins/Extensions/DVDPlayer/Makefile
lib/python/Plugins/Extensions/FileCommander/Makefile
lib/python/Plugins/Extensions/MediaPlayer/Makefile
lib/python/Plugins/Extensions/MediaScanner/Makefile
lib/python/Plugins/Extensions/MiniTV/Makefile
lib/python/Plugins/Extensions/PicturePlayer/Makefile
lib/python/Plugins/Extensions/ProgrammlistenUpdater/Makefile
lib/python/Plugins/Extensions/SocketMMI/Makefile
lib/python/Plugins/Extensions/SocketMMI/src/Makefile
lib/python/Plugins/Extensions/TuxboxPlugins/Makefile
lib/python/Plugins/Extensions/QuadPip/Makefile
lib/python/Plugins/Extensions/StreamlinkWrapper/Makefile
lib/python/Plugins/Extensions/YTDLWrapper/Makefile
lib/python/Plugins/Extensions/YTDLPWrapper/Makefile
lib/python/Plugins/SystemPlugins/Makefile
lib/python/Plugins/SystemPlugins/AnimationSetup/Makefile
lib/python/Plugins/SystemPlugins/AmlFRQ/Makefile
lib/python/Plugins/SystemPlugins/CableScan/Makefile
lib/python/Plugins/SystemPlugins/CommonInterfaceAssignment/Makefile
lib/python/Plugins/SystemPlugins/DefaultServicesScanner/Makefile
lib/python/Plugins/SystemPlugins/DiseqcTester/Makefile
lib/python/Plugins/SystemPlugins/FastChannelChange/Makefile
lib/python/Plugins/SystemPlugins/FastScan/Makefile
lib/python/Plugins/SystemPlugins/FrontprocessorUpgrade/Makefile
lib/python/Plugins/SystemPlugins/FSBLUpdater/Makefile
lib/python/Plugins/SystemPlugins/Hotplug/Makefile
lib/python/Plugins/SystemPlugins/IceTV/Makefile
lib/python/Plugins/SystemPlugins/LCNScanner/Makefile
lib/python/Plugins/SystemPlugins/NetworkWizard/Makefile
lib/python/Plugins/SystemPlugins/PositionerSetup/Makefile
lib/python/Plugins/SystemPlugins/SatelliteEquipmentControl/Makefile
lib/python/Plugins/SystemPlugins/Satfinder/Makefile
lib/python/Plugins/SystemPlugins/SoftwareManager/Makefile
lib/python/Plugins/SystemPlugins/VideoClippingSetup/Makefile
lib/python/Plugins/SystemPlugins/VideoEnhancement/Makefile
lib/python/Plugins/SystemPlugins/VideoEnhancementAML/Makefile
lib/python/Plugins/SystemPlugins/VideoTune/Makefile
lib/python/Plugins/SystemPlugins/WirelessLan/Makefile
lib/python/Plugins/SystemPlugins/vps/Makefile
lib/python/Plugins/SystemPlugins/vps/src_cc/Makefile
lib/python/Plugins/SystemPlugins/vps/src_py/Makefile
lib/python/Tools/Makefile
po/Makefile
main/Makefile
tools/Makefile
tools/enigma2.sh
hotplug/Makefile
enigma2.pc
])
AC_OUTPUT
