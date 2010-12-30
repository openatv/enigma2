AM_CPPFLAGS = \
	-I$(top_builddir) \
	-I$(top_srcdir) \
	-I$(top_srcdir)/include \
	-include Python.h \
	-include $(top_builddir)/enigma2_config.h

EXTRA_DIST = parseactions.py

noinst_LIBRARIES = libenigma_actions.a

libenigma_actions_a_SOURCES = \
	action.cpp

actionsincludedir = $(pkgincludedir)/lib/actions
actionsinclude_HEADERS = \
	action.h

nodist_actionsinclude_HEADERS = \
	actionids.h

BUILT_SOURCES = actionids.h
CLEANFILES = actionids.h

actionids.h: $(srcdir)/parseactions.py $(top_srcdir)/lib/gui/*.h
	$(AM_V_GEN)$(PYTHON) $(srcdir)/parseactions.py include $(top_srcdir)/lib/gui/*.h > $@
	$(AM_V_at)$(PYTHON) $(srcdir)/parseactions.py parse $(top_srcdir)/lib/gui/*.h >> $@
