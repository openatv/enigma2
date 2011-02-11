To build enigma2 on Ubuntu 10.04, follow these steps:

0.) Consider using OE to build it for a Dreambox instead.

    To build this version for a Dreambox, you will need
    a recent OE (branch "opendreambox-1.6" will do, but "3.0" won't)
    or at least a backported BitBake recipe from there.

    See http://opendreambox.org/.

    Stop reading here. It's not very useful for most people
    to build enigma2 for a PC.

1.) Install these packages:

autoconf
automake
build-essential
gettext
libdvdnav-dev
libfreetype6-dev
libfribidi-dev
libgif-dev
libgstreamer0.10-dev
libgstreamer-plugins-base0.10-dev
libjpeg62-dev
libpng12-dev
libsdl1.2-dev
libsigc++-1.2-dev
libtool
libxml2-dev
libxslt1-dev
python-dev
swig

2.) Build and install libdvbsi++:

git clone git://git.opendreambox.org/git/obi/libdvbsi++.git
cd libdvbsi++
dpkg-buildpackage -uc -us
cd ..
sudo dpkg -i libdvbsi++*.deb

3.) Build and install libxmlccwrap:

git clone git://git.opendreambox.org/git/obi/libxmlccwrap.git
cd libxmlccwrap
dpkg-buildpackage -uc -us
cd ..
sudo dpkg -i libxmlccwrap*.deb

4.) Build and install libdreamdvd:

git clone git://schwerkraft.elitedvb.net/libdreamdvd/libdreamdvd.git
cd libdreamdvd
dpkg-buildpackage -uc -us
cd ..
sudo dpkg -i libdreamdvd*.deb

5.) Build and install enigma2:

git clone git://git.opendreambox.org/git/enigma2.git
cd enigma2
autoreconf -i
./configure --prefix=$HOME/enigma2 --with-libsdl
make
make install

