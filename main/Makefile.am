AM_CPPFLAGS = \
	-I$(top_srcdir) \
	-I$(top_srcdir)/include \
	-include Python.h \
	-include $(top_builddir)/enigma2_config.h

AM_CXXFLAGS = \
	$(LIBSDL_CFLAGS)

bin_PROGRAMS = enigma2

enigma2_SOURCES = \
	bsod.cpp \
	bsod.h \
	enigma.cpp \
	xmlgenerator.cpp \
	xmlgenerator.h \
	version_info.cpp \
	version_info.h \
	version.h

EXTRA_DIST = \
	enigma-dvbtest.cpp \
	enigma-gdi.cpp \
	enigma-gui.cpp \
	enigma-playlist.cpp \
	enigma-scan.cpp

enigma2_LDADD_WHOLE = \
	$(top_builddir)/lib/actions/libenigma_actions.a \
	$(top_builddir)/lib/base/libenigma_base.a \
	$(top_builddir)/lib/components/libenigma_components.a \
	$(top_builddir)/lib/driver/libenigma_driver.a \
	$(top_builddir)/lib/mmi/libenigma_mmi.a \
	$(top_builddir)/lib/dvb/libenigma_dvb.a \
	$(top_builddir)/lib/dvb_ci/libenigma_dvb_ci.a \
	$(top_builddir)/lib/gdi/libenigma_gdi.a \
	$(top_builddir)/lib/gui/libenigma_gui.a \
	$(top_builddir)/lib/python/libenigma_python.a \
	$(top_builddir)/lib/nav/libenigma_nav.a \
	$(top_builddir)/lib/network/libenigma_network.a \
	$(top_builddir)/lib/service/libenigma_service.a

enigma2_LDADD = \
	@BASE_LIBS@ \
	@LIBGIF_LIBS@ \
	@LIBJPEG_LIBS@ \
	@LIBVUGLES2_LIBS@ \
	@LIBSDL_LIBS@ \
	@LIBXINE_LIBS@ \
	@LIBXMLCCWRAP_LIBS@ \
	@PTHREAD_LIBS@ \
	@PYTHON_LDFLAGS@ \
	@LIBDDVD_LIBS@ \
	-ltuxtxt -ltuxtxt32bpp -lcrypt -lrt

if ENABLE_SH
enigma2_LDADD += -lmmeimage
endif

enigma2_LDFLAGS = -Wl,--export-dynamic

if HAVE_GIT_DIR
GIT_DIR = $(top_srcdir)/.git
GIT = git --git-dir=$(GIT_DIR)

if HAVE_FAKE_GIT_DIR
ENIGMA2_COMMIT_DATE = `grep '^CommitDate:' $(GIT_DIR)/last_commit_info | cut -d' ' -f2`
ENIGMA2_BRANCH = `cat $(GIT_DIR)/branch`
else
ENIGMA2_COMMIT_DATE = `$(GIT) log --no-color -n 1 --pretty=format:%cd --date=short`
ENIGMA2_BRANCH = `$(GIT) branch --no-color 2>/dev/null | sed -e '/^[^*]/d' -e 's/* \(.*\)/\1/'`
ENIGMA2_REV = `$(GIT) describe --abbrev=7 --always --long --tags`
endif
endif

BUILT_SOURCES = version-intermediate.h
.INTERMEDIATE: version-intermediate.h
.PHONY: version-intermediate.h
version-intermediate.h:
	$(AM_V_GEN)touch $@
	-$(AM_V_at)[ -n "$(ENIGMA2_COMMIT_DATE)" ] && echo "#define ENIGMA2_COMMIT_DATE \"$(ENIGMA2_COMMIT_DATE)\"" >> $@
	-$(AM_V_at)[ -n "$(ENIGMA2_BRANCH)" ] && echo "#define ENIGMA2_BRANCH \"$(ENIGMA2_BRANCH)\"" >> $@
	-$(AM_V_at)[ -n "$(ENIGMA2_REV)" ] && echo "#define ENIGMA2_REV \"$(ENIGMA2_REV)\"" >> $@
	$(AM_V_at)([ -f version.h ] && diff -q version.h $@ >/dev/null) || $(INSTALL_HEADER) $@ version.h

enigma2$(EXEEXT): $(enigma2_OBJECTS) $(enigma2_DEPENDENCIES) $(enigma2_LDADD_WHOLE)
	$(AM_V_CXXLD)$(CXXLD) $(AM_CXXFLAGS) $(CXXFLAGS) $(AM_LDFLAGS) $(LDFLAGS) -o $@ $(enigma2_LDFLAGS) $(enigma2_OBJECTS) \
		-Wl,--whole-archive $(enigma2_LDADD_WHOLE) -Wl,--no-whole-archive $(enigma2_LDADD) $(LIBS)
