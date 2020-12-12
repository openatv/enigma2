## Build Status - branch 6.4  develop: ##
[![Build Status](https://travis-ci.org/openatv/enigma2.svg?branch=6.4)](https://travis-ci.org/openatv/enigma2)

## Our buildserver is currently running on: ##

> Ubuntu 20.04.1 LTS (Kernel 5.4.0)

## openATV 6.4 is build using oe-alliance build-environment and several git repositories: ##

> [https://github.com/oe-alliance/oe-alliance-core/tree/4.4](https://github.com/oe-alliance/oe-alliance-core/tree/4.4 "OE-Alliance")
> 
> [https://github.com/openatv/enigma2/tree/6.4](https://github.com/openatv/enigma2/tree/6.4 "openATV E2")
> 
> [https://github.com/openatv/MetrixHD](https://github.com/openatv/MetrixHD/tree/master "openATV Skin")

> and a lot more...


----------

# Building Instructions #

1 - Install packages on your buildserver

    sudo apt-get install -y autoconf automake bison bzip2 chrpath coreutils cpio curl cvs debianutils default-jre default-jre-headless diffstat flex g++ gawk gcc gcc-8 gettext git git-core gzip help2man info iputils-ping java-common libc6-dev libegl1-mesa libglib2.0-dev libncurses5-dev libperl4-corelibs-perl libproc-processtable-perl libsdl1.2-dev libserf-dev libtool libxml2-utils make ncurses-bin patch perl pkg-config psmisc python3 python3-git python3-jinja2 python3-pexpect python3-pip python-setuptools qemu quilt socat sshpass subversion tar texi2html texinfo unzip wget xsltproc xterm xz-utils zip zlib1g-dev 
    
----------
2 - Set python2 as preferred provider for python

    sudo update-alternatives --install /usr/bin/python python /usr/bin/python2 1
    sudo update-alternatives --install /usr/bin/python python /usr/bin/python3 2
    sudo update-alternatives --config python
    select python2
    
----------    
3 - Set your shell to /bin/bash.

    sudo dpkg-reconfigure dash
    When asked: Install dash as /bin/sh?
    select "NO"

----------
4 - modify max_user_watches

    echo fs.inotify.max_user_watches=524288 | sudo tee -a /etc/sysctl.conf

    sudo sysctl -n -w fs.inotify.max_user_watches=524288

----------
5 - Add user openatvbuilder

    sudo adduser openatvbuilder

----------
6 - Switch to user openatvbuilder

    su openatvbuilder

----------
7 - Switch to home of openatvbuilder

    cd ~

----------
8 - Create folder openatv

    mkdir -p ~/openatv

----------
9 - Switch to folder openatv

    cd openatv

----------
10 - Clone oe-alliance git

    git clone git://github.com/oe-alliance/build-enviroment.git -b 4.4

----------
11 - Switch to folder build-enviroment

    cd build-enviroment

----------
12 - Update build-enviroment

    make update

----------
13 - Finally you can start building a image

    MACHINE=zgemmah9combo DISTRO=openatv DISTRO_TYPE=release make image

