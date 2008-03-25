#!/bin/sh

package="enigma2"

srcdir=`dirname $0`
test -z "$srcdir" && srcdir=.

cd "$srcdir"
DIE=0

(autoconf --version) < /dev/null > /dev/null 2>&1 || {
	echo
	echo "You must have autoconf installed to compile $package."
	echo "Download the appropriate package for your system,"
	echo "or get the source from one of the GNU ftp sites"
	echo "listed in http://www.gnu.org/order/ftp.html"
	DIE=1
}

(automake --version) < /dev/null > /dev/null 2>&1 || {
	echo
	echo "You must have automake installed to compile $package."
	echo "Download the appropriate package for your system,"
	echo "or get the source from one of the GNU ftp sites"
	echo "listed in http://www.gnu.org/order/ftp.html"
	DIE=1
}

(libtool --version) < /dev/null > /dev/null 2>&1 || {
	echo
	echo "You must have libtool installed to compile $package."
	echo "Download the appropriate package for your system,"
	echo "or get the source from one of the GNU ftp sites"
	echo "listed in http://www.gnu.org/order/ftp.html"
	DIE=1
}

if test "$DIE" -eq 1; then
	exit 1
fi

if [ ! -e acinclude.m4 ]; then
	for i in .. ../.. ../../..; do
		if [ -e `pwd`/$i/acinclude.m4 ]; then
			ln -s `pwd`/$i/acinclude.m4 .
		fi
	done
fi

echo "Generating configuration files for $package, please wait...."

echo "  aclocal"
aclocal
echo "  libtoolize --automake"
libtoolize --automake
echo "  autoconf"
autoconf
echo "  automake --add-missing"
automake --add-missing 

