INCLUDES = \
	-I$(top_srcdir)/include

bin_PROGRAMS = enigma2

enigma2_SOURCES = \
	enigma.cpp 

enigma2_LDADD_WHOLE = \
	$(top_builddir)/lib/base/libenigma_base.a \
	$(top_builddir)/lib/driver/libenigma_driver.a \
	$(top_builddir)/lib/dvb/libenigma_dvb.a \
	$(top_builddir)/lib/dvb_si/libenigma_dvb_si.a \
	$(top_builddir)/lib/gui/libenigma_gui.a \
	$(top_builddir)/lib/gdi/libenigma_gdi.a \
	$(top_builddir)/lib/network/libenigma_network.a \
	$(top_builddir)/lib/service/libenigma_service.a

enigma2_LDADD = \
	@FREETYPE_LIBS@ \
	@ID3TAG_LIBS@ \
	@MAD_LIBS@ \
	@MD5SUM_LIBS@ \
	@PNG_LIBS@ \
	@SIGC_LIBS@ \
	@XMLTREE_LIBS@ \
	-ldl -lpthread -lcrypt -lresolv

enigma2$(EXEEXT): $(enigma2_OBJECTS) $(enigma2_DEPENDENCIES) $(enigma2_LDADD_WHOLE)
	@rm -f enigma2$(EXEEXT)
	$(CXXLINK) $(enigma2_LDFLAGS) $(enigma2_OBJECTS) -Wl,--export-dynamic -Wl,--whole-archive $(enigma2_LDADD_WHOLE) -Wl,--no-whole-archive $(enigma2_LDADD) $(LIBS)
