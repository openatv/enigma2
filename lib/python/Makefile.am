AM_CPPFLAGS = \
	-I$(top_srcdir) \
	-I$(top_srcdir)/include \
	-include Python.h \
	-include $(top_builddir)/enigma2_config.h

SUBDIRS = Components Tools Screens Plugins

noinst_LIBRARIES = libenigma_python.a

libenigma_python_a_SOURCES = \
	connections.cpp \
	python.cpp

pythonincludedir = $(pkgincludedir)/lib/python
pythoninclude_HEADERS = \
	connections.h \
	python.h \
	swig.h

nodist_libenigma_python_a_SOURCES = \
	enigma_python.cpp

noinst_PYTHON = \
	enigma_py_patcher.py

EXTRA_DIST = \
	enigma_python.i

@AMDEP_TRUE@@am__include@ @am__quote@./$(DEPDIR)/enigma_python.Pcpp@am__quote@

.i.cpp:
	$(AM_V_GEN)$(SWIG) $(AX_SWIG_PYTHON_OPT) -MT $@ -MD -MF $(DEPDIR)/$*.Tpo -I$(top_srcdir) -O -nortti -nothreads -o $@ $<
	$(AM_V_at)mv -f $(DEPDIR)/$*.Tpo $(DEPDIR)/$*.Pcpp
	$(AM_V_at)$(PYTHON) $(srcdir)/enigma_py_patcher.py

enigma.py: enigma_python.cpp

CLEANFILES = enigma.py enigma_python.cpp

installdir = $(pkglibdir)/python

install_PYTHON = \
	enigma.py

