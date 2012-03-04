plugin_LTLIBRARIES = timeshift/eitsave.la

timeshift_eitsave_la_SOURCES = timeshift/eitsave.cpp 
timeshift_eitsave_la_LDFLAGS = -avoid-version -module

pluginexec_PROGRAMS = timeshift/createapscfiles
timeshift_createapscfiles_SOURCES = timeshift/createapscfiles.cc

install-data-hook:
	rm $(DESTDIR)$(libdir)/enigma2/python/Components/eitsave.*a
