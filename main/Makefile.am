INCLUDES = \
	-I$(top_srcdir)/include

bin_PROGRAMS = enigma2

enigma2_SOURCES = \
	enigma.cpp bsod.cpp

CLEANFILES = version.h

bsod.o: version.h

enigma.o: version.h

# when there is no ../CVS/Entries, don't worry.
../CVS/Entries:

../CVS/Root:

.PHONY: .svn/entries

entries: .svn/entries
	@if [ ! -f entries ]; then touch entries; fi
	@if [ -f .svn/entries ] && ! diff -q entries .svn/entries 2>/dev/null; then	\
		cp --no-preserve=mode .svn/entries entries;				\
	fi;

version.h: entries
	> version.h
	@if [ -d .svn ]; then \
		echo "#define ENIGMA2_LAST_CHANGE_DATE \"`LANG="en" svn info | grep 'Last Changed Date:' | cut -d' ' -f4`\"" >> version.h; \
	elif [ -d ../.git ]; then \
		if [ -f ../.git/last_commit_info ]; then \
			echo "#define ENIGMA2_LAST_CHANGE_DATE \"`cat ../.git/last_commit_info | grep 'Date:' | cut -d' ' -f4`\"" >> version.h; \
			echo "#define ENIGMA2_BRANCH \"`cat ../.git/branch`\"" >> version.h; \
		else \
			echo "#define ENIGMA2_LAST_CHANGE_DATE \"`LANG="en" git log --max-count=1 --date=short | grep 'Date:' | cut -d' ' -f4`\"" >> version.h; \
			echo "#define ENIGMA2_BRANCH \"`LANG="en" git branch | grep '* ' | cut -d' ' -f2`\"" >> version.h; \
		fi; \
	fi;

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
	@FREETYPE_LIBS@ \
	@ID3TAG_LIBS@ \
	@MAD_LIBS@ \
	@PNG_LIBS@ \
	@SDL_LIBS@ \
	@SIGC_LIBS@ \
	@DVBSI_LIBS@ \
	@FRIBIDI_LIBS@ \
	@GSTREAMER_LIBS@ \
	@GSTREAMERPBUTILS_LIBS@ \
	@JPEG_LIBS@ \
	@LIBUNGIF_LIBS@ \
	@XML2_LIBS@ \
	@XMLCCWRAP_LIBS@ \
	-ldl -lpthread -lcrypt -lresolv -lrt

enigma2$(EXEEXT): $(enigma2_OBJECTS) $(enigma2_DEPENDENCIES) $(enigma2_LDADD_WHOLE)
#	@rm -f enigma2$(EXEEXT)
	$(CXXLINK) $(enigma2_LDFLAGS) $(enigma2_OBJECTS) -Wl,--export-dynamic -Wl,--whole-archive $(enigma2_LDADD_WHOLE) -Wl,--no-whole-archive $(enigma2_LDADD) $(LIBS)
#	g++ -o enigma2$(EXEEXT) $(enigma2_LDFLAGS) $(enigma2_OBJECTS) -Wl,--export-dynamic -Wl,--whole-archive $(enigma2_LDADD_WHOLE) -Wl,--no-whole-archive $(enigma2_LDADD) $(LIBS)
