AM_CPPFLAGS = \
	-I$(top_builddir) \
	-I$(top_srcdir)/include \
	-include Python.h \
	-include $(top_builddir)/enigma2_config.h

EXTRA_DIST = parseactions.py

noinst_LTLIBRARIES = libenigma_actions.la

libenigma_actions_la_SOURCES = \
	action.cpp \
	action.h

nodist_libenigma_actions_la_SOURCES = \
	actionids.h

BUILT_SOURCES = actionids.h
CLEANFILES = actionids.h

actionids.h: $(srcdir)/parseactions.py $(top_srcdir)/lib/gui/*.h
	$(PYTHON) $(srcdir)/parseactions.py include $(top_srcdir)/lib/gui/*.h > $@
	$(PYTHON) $(srcdir)/parseactions.py parse $(top_srcdir)/lib/gui/*.h >> $@
