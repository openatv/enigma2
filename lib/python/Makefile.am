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
	enigma_python_wrap.cxx

noinst_PYTHON = \
	enigma_py_patcher.py

EXTRA_DIST = \
	enigma_python.i

enigma_python_wrap.cxx: $(srcdir)/enigma_python.i
	$(AM_V_GEN)$(SWIG) $(AX_SWIG_PYTHON_OPT) -I$(top_srcdir) -O -nortti -nothreads -o $@ $<
	$(AM_V_at)$(PYTHON) $(srcdir)/enigma_py_patcher.py

enigma.py: enigma_python_wrap.cxx

CLEANFILES = enigma.py enigma_python_wrap.cxx

installdir = $(pkglibdir)/python

install_PYTHON = \
	enigma.py

