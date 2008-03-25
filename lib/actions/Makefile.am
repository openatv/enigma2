INCLUDES = \
	-I$(top_srcdir)/include

noinst_LIBRARIES = libenigma_actions.a

libenigma_actions_a_SOURCES = \
	action.cpp 

CLEANFILES = actionids.h

action.cpp: actionids.h

actionids.h:
	 python ./parseactions.py include ../gui/*.h > actionids.h
	 python ./parseactions.py parse ../gui/*.h >> actionids.h
