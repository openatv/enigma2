AM_CPPFLAGS = \
	-I$(top_srcdir) \
	-I$(top_srcdir)/include \
	-include Python.h

SUBDIRS = Components Tools Screens Plugins

noinst_LTLIBRARIES = libenigma_python.la

libenigma_python_la_SOURCES = \
	python.cpp enigma_python_wrap.cxx connections.cpp

enigma_python_wrap.cxx: enigma_python.i
	swig -I$(top_srcdir)/ -c++ -python -O -nortti -nothreads enigma_python.i
	python enigma_py_patcher.py

enigma.py: enigma_python_wrap.cxx

CLEANFILES = enigma.py enigma_python_wrap.cxx

installdir = $(pkglibdir)/python

install_PYTHON = \
	enigma.py
