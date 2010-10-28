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
	$(top_builddir)/lib/service/libenigma_service.a

enigma2_LDADD = \
	@BASE_LIBS@ \
	@LIBGIF_LIBS@ \
	@LIBJPEG_LIBS@ \
	@LIBSDL_LIBS@ \
	@LIBXINE_LIBS@ \
	@LIBXMLCCWRAP_LIBS@ \
	@PTHREAD_LIBS@ \
	@PYTHON_LDFLAGS@

enigma2_LDFLAGS = -Wl,--export-dynamic

BUILT_SOURCES = version.h

GIT_DIR = $(top_srcdir)/.git

version.h:
	if [ -d $(GIT_DIR) ]; then \
		if [ -f $(GIT_DIR)/last_commit_info ]; then \
			echo "#define ENIGMA2_LAST_CHANGE_DATE \"`cat $(GIT_DIR)/last_commit_info | grep 'Date:' | cut -d' ' -f4`\"" > $@; \
			echo "#define ENIGMA2_BRANCH \"`cat $(GIT_DIR)/branch`\"" >> $@; \
		else \
			echo "#define ENIGMA2_LAST_CHANGE_DATE \"`git --git-dir=$(top_srcdir)/.git log --no-color -n 1 --format=format:%cd --date=short`\"" > $@; \
			echo "#define ENIGMA2_BRANCH \"`git --git-dir=$(top_srcdir)/.git branch --no-color 2>/dev/null | sed -e '/^[^*]/d' -e 's/* \(.*\)/\1/'`\"" >> $@; \
		fi; \
	elif [ ! -f $@ ]; then \
		echo "#define ENIGMA2_LAST_CHANGE_DATE \"`date --rfc-3339=date`\"" > $@; \
		echo "#define ENIGMA2_BRANCH \"$(PACKAGE_VERSION)\"" >> $@; \
	fi;

dist-hook:
	echo "#define ENIGMA2_LAST_CHANGE_DATE \"`date --rfc-3339=date`\"" > version.h;
	echo "#define ENIGMA2_BRANCH \"$(PACKAGE_VERSION)\"" >> version.h;

enigma2$(EXEEXT): $(enigma2_OBJECTS) $(enigma2_DEPENDENCIES) $(enigma2_LDADD_WHOLE)
	$(CXXLD) $(AM_CXXFLAGS) $(CXXFLAGS) $(AM_LDFLAGS) $(LDFLAGS) -o $@ $(enigma2_LDFLAGS) $(enigma2_OBJECTS) \
		-Wl,--whole-archive $(enigma2_LDADD_WHOLE) -Wl,--no-whole-archive $(enigma2_LDADD) $(LIBS)
