## Our buildserver is currently running on: ##

> Ubuntu 12.04.5 LTS (GNU/Linux 3.2.13-grsec-xxxx-grs-ipv6-64 x86_64)

## openMips is build using oe-alliance build-environment and several git repositories: ##

> [https://github.com/oe-alliance/oe-alliance-core](https://github.com/oe-alliance/oe-alliance-core "OE-Alliance")
> 
> [https://github.com/openmips/stbgui](https://github.com/openmips/stbgui "openMips E2")
> 
> [https://github.com/openmips/skin-pax](https://github.com/openmips/skin-pax "openMips Skin")

> and a lot more...


----------

# Building Instructions #

1 - Install packages on your buildserver

    sudo apt-get install -y autoconf automake bison bzip2 chrpath coreutils cvs default-jre default-jre-headless diffstat flex g++ gawk gcc gettext git-core gzip help2man htop info java-common libc6-dev libglib2.0-dev libperl4-corelibs-perl libproc-processtable-perl libtool libxml2-utils make ncdu ncurses-bin ncurses-dev patch perl pkg-config po4a python-setuptools quilt sgmltools-lite sshpass subversion swig tar texi2html texinfo wget xsltproc zip zlib1g-dev

----------
2 - Add user openmipsbuilder

    sudo adduser openmipsbuilder

----------
3 - Switch to user openmipsbuilder

    su openmipsbuilder

----------
4 - Switch to home of openmipsbuilder

    cd ~

----------
5 - Create folder openmips

    mkdir -p ~/openmips

----------
6 - Switch to folder openmips

    cd openmips

----------
7 - Clone oe-alliance git

    git clone git://github.com/oe-alliance/build-enviroment.git

----------
8 - Switch to folder build-enviroment

    cd build-enviroment

----------
9 - Update build-enviroment

    make update

----------
10 - Finally you can start building a image

    make MACHINE=gbquadplus DISTRO=openmips image