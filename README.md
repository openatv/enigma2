## Our buildserver is currently running on: ##

> Ubuntu 12.04.5 LTS (GNU/Linux 3.14.32-xxxx-grs-ipv6-64 x86_64)

## openMips 5.2 is build using oe-alliance build-environment "next" and several git repositories: ##

> [https://github.com/oe-alliance/oe-alliance-core/tree/next](https://github.com/oe-alliance/oe-alliance-core/tree/next "OE-Alliance")
> 
> [https://github.com/openmips/stbgui/tree/master](https://github.com/openmips/stbgui/tree/master "openMips E2")
> 
> [https://github.com/openmips/skin-pax/tree/master](https://github.com/openmips/skin-pax/tree/master "openMips Skin")

> and a lot more...


----------

# Building Instructions #

1 - Install packages on your buildserver

    sudo apt-get install -y autoconf automake bison bzip2 chrpath coreutils cvs default-jre default-jre-headless diffstat flex g++ gawk gcc gettext git-core gzip help2man htop info java-common libc6-dev libglib2.0-dev libperl4-corelibs-perl libproc-processtable-perl libtool libxml2-utils make ncdu ncurses-bin ncurses-dev patch perl pkg-config po4a python-setuptools quilt sgmltools-lite sshpass subversion swig tar texi2html texinfo wget xsltproc zip zlib1g-dev

----------
2 - Set your shell to /bin/bash

    sudo dpkg-reconfigure dash
    When asked: Install dash as /bin/sh?
    select "NO"

----------
3 - Add user openmipsbuilder

    sudo adduser openmipsbuilder

----------
4 - Switch to user openmipsbuilder

    su openmipsbuilder

----------
5 - Switch to home of openmipsbuilder

    cd ~

----------
6 - Create folder openmips

    mkdir -p ~/openmips

----------
7 - Switch to folder openmips

    cd openmips

----------
8 - Clone oe-alliance git

    git clone git://github.com/oe-alliance/build-enviroment.git -b next

----------
9 - Switch to folder build-enviroment

    cd build-enviroment

----------
10 - Update build-enviroment

    make update

----------
11 - Finally you can start building a image

    MACHINE=gbquadplus DISTRO=openmips make image