AM_CPPFLAGS = \
	-I$(top_srcdir) \
	-I$(top_srcdir)/include \
	-include Python.h

bin_PROGRAMS = enigma2

enigma2_SOURCES = \
	enigma.cpp bsod.cpp

CLEANFILES = version.h

bsod.o: version.h

enigma.o: version.h

# when there is no ../CVS/Entries, don't worry.
../CVS/Entries:

../CVS/Root:

.PHONY: .svn/entries

entries: .svn/entries
	@if [ ! -f entries ]; then touch entries; fi
	@if [ -f .svn/entries ] && ! diff -q entries .svn/entries 2>/dev/null; then	\
		cp --no-preserve=mode .svn/entries entries;				\
	fi;

version.h: entries
	> version.h
	@if [ -d .svn ]; then \
		echo "#define ENIGMA2_LAST_CHANGE_DATE \"`LANG="en" svn info | grep 'Last Changed Date:' | cut -d' ' -f4`\"" >> version.h; \
	elif [ -d ../.git ]; then \
		if [ -f ../.git/last_commit_info ]; then \
			echo "#define ENIGMA2_LAST_CHANGE_DATE \"`cat ../.git/last_commit_info | grep 'Date:' | cut -d' ' -f4`\"" >> version.h; \
			echo "#define ENIGMA2_BRANCH \"`cat ../.git/branch`\"" >> version.h; \
		else \
			echo "#define ENIGMA2_LAST_CHANGE_DATE \"`LANG="en" git log --max-count=1 --date=short | grep 'Date:' | cut -d' ' -f4`\"" >> version.h; \
			echo "#define ENIGMA2_BRANCH \"`LANG="en" git branch | grep '* ' | cut -d' ' -f2`\"" >> version.h; \
		fi; \
	fi;

enigma2_LDADD = \
	$(top_builddir)/lib/libenigma.la \
	@BASE_LIBS@ \
	@LIBUNGIF_LIBS@ \
	@LIBXINE_LIBS@ \
	@PTHREAD_LIBS@ \
	@SDL_LIBS@ \
	@LIBS@ \
	-ltuxtxt32bpp

