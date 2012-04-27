noinst_LIBRARIES += python/libenigma_python.a

python_libenigma_python_a_SOURCES = \
	python/connections.cpp \
	python/python.cpp

pythonincludedir = $(pkgincludedir)/lib/python
pythoninclude_HEADERS = \
	python/connections.h \
	python/python.h \
	python/swig.h

nodist_python_libenigma_python_a_SOURCES = \
	python/enigma_python.cpp

noinst_PYTHON += \
	python/enigma_py_patcher.py

EXTRA_DIST += \
	python/enigma_python.i

@AMDEP_TRUE@@am__include@ @am__quote@./$(DEPDIR)/python/enigma_python.Pcpp@am__quote@

.i.cpp:
	$(AM_V_GEN)$(SWIG) $(AX_SWIG_PYTHON_OPT) -MT $@ -MD -MF $(DEPDIR)/$*.Tpo -I$(top_srcdir) -O -nortti -nothreads -o $@ $<
	$(AM_V_at)mv -f $(DEPDIR)/$*.Tpo $(DEPDIR)/$*.Pcpp
	$(AM_V_at)$(PYTHON) $(srcdir)/python/enigma_py_patcher.py python/enigma.py

python/enigma.py: python/enigma_python.cpp

CLEANFILES += python/enigma.py python/enigma_python.cpp

nobase_install_PYTHON += \
	python/enigma.py
