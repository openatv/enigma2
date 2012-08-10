EXTRA_DIST += actions/parseactions.py

noinst_LIBRARIES += actions/libenigma_actions.a

actions_libenigma_actions_a_SOURCES = \
	actions/action.cpp

actionsincludedir = $(pkgincludedir)/lib/actions
actionsinclude_HEADERS = \
	actions/action.h

nodist_actionsinclude_HEADERS = \
	actions/actionids.h

BUILT_SOURCES += actions/actionids.h
CLEANFILES += actions/actionids.h

$(srcdir)/actions/actionids.h: $(srcdir)/actions/parseactions.py $(top_srcdir)/lib/gui/*.h
	$(AM_V_GEN)$(PYTHON) $(srcdir)/actions/parseactions.py include $(top_srcdir)/lib/gui/*.h > $@
	$(AM_V_at)$(PYTHON) $(srcdir)/actions/parseactions.py parse $(top_srcdir)/lib/gui/*.h >> $@
