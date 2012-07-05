installdir = $(pkglibdir)/python/Plugins/SystemPlugins/SoftwareManager

SUBDIRS = meta

install_PYTHON =	\
	__init__.py \
	plugin.py \
	BackupRestore.py \
	ImageWizard.py \
	SoftwareTools.py \
	ImageBackup.py

dist_install_DATA = \
	imagewizard.xml \
	installable.png \
	installed.png \
	install.png \
	noprev.png \
	remove.png \
	update.png \
	upgradeable.png \
	upgrade.png \
	backup-hdd.sh \
	backup-usb.sh \
	backup.sh

install-data-hook:
	chmod +x $(DESTDIR)$(installdir)/backup-hdd.sh; \
	chmod +x $(DESTDIR)$(installdir)/backup-usb.sh; \
	chmod +x $(DESTDIR)$(installdir)/backup.sh
