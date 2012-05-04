installdir = $(pkglibdir)/python/Plugins/Extensions/StreamTV

SUBDIRS = meta icons

install_PYTHON = \
	channel_background.png \
	stream.xml \
	rtmpdump \
	__init__.py \
	plugin.py 

install-data-hook:
	@chmod +x $(DESTDIR)$(installdir)/rtmpdump
