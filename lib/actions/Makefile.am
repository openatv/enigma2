AM_CPPFLAGS = \
	-I$(top_builddir) \
	-I$(top_srcdir)/include \
	-include Python.h

EXTRA_DIST = parseactions.py

noinst_LTLIBRARIES = libenigma_actions.la

libenigma_actions_la_SOURCES = \
	action.cpp \
	action.h

BUILT_SOURCES = actionids.h
CLEANFILES = actionids.h

action.cpp: actionids.h

actionids.h: $(top_srcdir)/lib/gui/*.h
	$(PYTHON) $(srcdir)/parseactions.py include $(top_srcdir)/lib/gui/*.h > $@
	$(PYTHON) $(srcdir)/parseactions.py parse $(top_srcdir)/lib/gui/*.h >> $@
