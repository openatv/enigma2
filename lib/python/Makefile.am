INCLUDES = \
	-I$(top_srcdir)/include \
	-I$(top_srcdir)/src

SUBDIRS = Components Tools Screens Plugins

noinst_LIBRARIES = libenigma_python.a

libenigma_python_a_SOURCES = \
	python.cpp enigma_python_wrap.cxx connections.cpp

enigma_python_wrap.cxx: enigma_python.i
	swig -I$(top_srcdir)/ -c++ -python enigma_python.i
	echo "#include <lib/python/python.h>" > bla.cxx
	cat enigma_python_wrap.cxx >> bla.cxx
	mv bla.cxx enigma_python_wrap.cxx

installdir = $(LIBDIR)/enigma2/python

install_DATA = \
	enigma.py
