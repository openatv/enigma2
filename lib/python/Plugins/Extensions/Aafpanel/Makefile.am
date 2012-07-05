installdir = $(pkglibdir)/python/Plugins/Extensions/Aafpanel

SUBDIRS = meta Extra icons locale meta pics

install_PYTHON = *.py

install-data-hook: 
	@chmod +x $(DESTDIR)$(installdir)/sundtekinstall.sh

