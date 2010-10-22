SUBDIRS = actions base components dvb dvb_ci gdi service driver nav gui python mmi

noinst_LTLIBRARIES = libenigma.la

libenigma_la_SOURCES =
libenigma_la_LIBADD = \
	$(top_builddir)/lib/actions/libenigma_actions.la \
	$(top_builddir)/lib/base/libenigma_base.la \
	$(top_builddir)/lib/components/libenigma_components.la \
	$(top_builddir)/lib/driver/libenigma_driver.la \
	$(top_builddir)/lib/mmi/libenigma_mmi.la \
	$(top_builddir)/lib/dvb/libenigma_dvb.la \
	$(top_builddir)/lib/dvb_ci/libenigma_dvb_ci.la \
	$(top_builddir)/lib/gdi/libenigma_gdi.la \
	$(top_builddir)/lib/gui/libenigma_gui.la \
	$(top_builddir)/lib/python/libenigma_python.la \
	$(top_builddir)/lib/nav/libenigma_nav.la \
	$(top_builddir)/lib/service/libenigma_service.la
