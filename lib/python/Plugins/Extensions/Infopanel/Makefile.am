installdir = $(pkglibdir)/python/Plugins/Extensions/Infopanel

SUBDIRS = Extra icons locale meta

install_PYTHON = *.py

dist_install_DATA = sundtekinstall.sh

install-data-hook:
	@chmod +x $(DESTDIR)$(installdir)/sundtekinstall.sh

