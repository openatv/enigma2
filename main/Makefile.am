INCLUDES = \
	-I$(top_srcdir)/include

bin_PROGRAMS = enigma2

enigma2_SOURCES = \
	enigma.cpp bsod.cpp

bsod.o: version.h

enigma.o: version.h

# when there is no ../CVS/Entries, don't worry.
../CVS/Entries:

../CVS/Root:

# this depends on Entries and not on Tag because Tag isn't always there.
# Entries, however, will change then Tag is changed, so everything is fine.
version.h: ../CVS/Entries ../CVS/Root
	> version.h
	if [ -f ../CVS/Tag ]; then echo "#define ENIGMA2_CHECKOUT_TAG \"`cat ../CVS/Tag`\"" >> version.h; fi
	if [ -f ../CVS/Root ]; then echo "#define ENIGMA2_CHECKOUT_ROOT \"`cat ../CVS/Root`\"" >> version.h; fi

enigma2_LDADD_WHOLE = \
	$(top_builddir)/lib/actions/libenigma_actions.a \
	$(top_builddir)/lib/base/libenigma_base.a \
	$(top_builddir)/lib/components/libenigma_components.a \
	$(top_builddir)/lib/driver/libenigma_driver.a \
	$(top_builddir)/lib/dvb/libenigma_dvb.a \
	$(top_builddir)/lib/dvb_ci/libenigma_dvb_ci.a \
	$(top_builddir)/lib/gdi/libenigma_gdi.a \
	$(top_builddir)/lib/gui/libenigma_gui.a \
	$(top_builddir)/lib/python/libenigma_python.a \
	$(top_builddir)/lib/nav/libenigma_nav.a \
	$(top_builddir)/lib/service/libenigma_service.a \
	$(top_builddir)/lib/xml/libenigma_xml.a

enigma2_LDADD = \
	@FREETYPE_LIBS@ \
	@ID3TAG_LIBS@ \
	@MAD_LIBS@ \
	@PNG_LIBS@ \
	@SIGC_LIBS@ \
	@DVBSI_LIBS@ \
	@FRIBIDI_LIBS@ \
	@GSTREAMER_LIBS@ \
	@JPEG_LIBS@ \
	@LIBUNGIF_LIBS@ \
	-ldl -lpthread -lcrypt -lresolv -lxml2

enigma2$(EXEEXT): $(enigma2_OBJECTS) $(enigma2_DEPENDENCIES) $(enigma2_LDADD_WHOLE)
#	@rm -f enigma2$(EXEEXT)
	$(CXXLINK) $(enigma2_LDFLAGS) $(enigma2_OBJECTS) -Wl,--export-dynamic -Wl,--whole-archive $(enigma2_LDADD_WHOLE) -Wl,--no-whole-archive $(enigma2_LDADD) $(LIBS)
#	g++ -o enigma2$(EXEEXT) $(enigma2_LDFLAGS) $(enigma2_OBJECTS) -Wl,--export-dynamic -Wl,--whole-archive $(enigma2_LDADD_WHOLE) -Wl,--no-whole-archive $(enigma2_LDADD) $(LIBS)
