AM_CPPFLAGS = \
	-I$(top_srcdir) \
	-I$(top_srcdir)/include \
	-include Python.h \
	-include $(top_builddir)/enigma2_config.h

SUBDIRS = Components Tools Screens Plugins

noinst_LTLIBRARIES = libenigma_python.la

libenigma_python_la_SOURCES = \
	connections.cpp \
	connections.h \
	python.cpp \
	python.h \
	swig.h

nodist_libenigma_python_la_SOURCES = \
	enigma_python_wrap.cxx

EXTRA_DIST = \
	enigma_py_patcher.py \
	enigma_python.i

enigma_python_wrap.cxx: $(srcdir)/enigma_python.i
	$(SWIG) $(AX_SWIG_PYTHON_OPT) -I$(top_srcdir) -O -nortti -nothreads -o $@ $<
	$(PYTHON) $(srcdir)/enigma_py_patcher.py

enigma.py: enigma_python_wrap.cxx

CLEANFILES = enigma.py enigma_python_wrap.cxx

installdir = $(pkglibdir)/python

install_PYTHON = \
	enigma.py

