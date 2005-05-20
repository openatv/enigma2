INCLUDES = \
	-I$(top_srcdir)/include \
	-I/usr/include/python2.3

bin_PROGRAMS = enigma2

enigma2_SOURCES = \
	enigma.cpp 

enigma2_LDADD_WHOLE = \
	$(top_builddir)/lib/actions/libenigma_actions.a \
	$(top_builddir)/lib/base/libenigma_base.a \
	$(top_builddir)/lib/components/libenigma_components.a \
	$(top_builddir)/lib/driver/libenigma_driver.a \
	$(top_builddir)/lib/dvb/libenigma_dvb.a \
	$(top_builddir)/lib/dvb_si/libenigma_dvb_si.a \
	$(top_builddir)/lib/gdi/libenigma_gdi.a \
	$(top_builddir)/lib/gui/libenigma_gui.a \
	$(top_builddir)/lib/python/libenigma_python.a \
	$(top_builddir)/lib/nav/libenigma_nav.a \
	$(top_builddir)/lib/network/libenigma_network.a \
	$(top_builddir)/lib/service/libenigma_service.a

enigma2_LDADD = \
	@FREETYPE_LIBS@ \
	@ID3TAG_LIBS@ \
	@MAD_LIBS@ \
	@PNG_LIBS@ \
	@SIGC_LIBS@ \
	@SDL_LIBS@ \
	-ldl -lpthread -lcrypt -lresolv -lpython2.3

enigma2$(EXEEXT): $(enigma2_OBJECTS) $(enigma2_DEPENDENCIES) $(enigma2_LDADD_WHOLE)
	@rm -f enigma2$(EXEEXT)
#	$(CXXLINK) $(enigma2_LDFLAGS) $(enigma2_OBJECTS) -Wl,--export-dynamic -Wl,--whole-archive $(enigma2_LDADD_WHOLE) -Wl,--no-whole-archive $(enigma2_LDADD) $(LIBS)
	g++ -o enigma2$(EXEEXT) $(enigma2_LDFLAGS) $(enigma2_OBJECTS) -Wl,--export-dynamic -Wl,--whole-archive $(enigma2_LDADD_WHOLE) -Wl,--no-whole-archive $(enigma2_LDADD) $(LIBS)
