noinst_LIBRARIES += actions/libenigma_actions.a

actions_libenigma_actions_a_SOURCES = \
	actions/action.cpp

actionsincludedir = $(pkgincludedir)/lib/actions
actionsinclude_HEADERS = \
	actions/action.h \
	actions/actionids.h
