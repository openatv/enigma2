INCLUDES = \
	-I$(top_srcdir)/include \
	-I$(top_srcdir)/src

noinst_LIBRARIES = libenigma_python.a

libenigma_python_a_SOURCES = \
	python.cpp enigma_python_wrap.cxx connections.cpp

enigma_python_wrap.cxx: enigma_python.i
	swig -I$(top_srcdir)/ -c++ -python enigma_python.i
