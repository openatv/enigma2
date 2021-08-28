## Build Status - branch 7.0  develop: ##
[![Build Status](https://travis-ci.org/openatv/enigma2.svg?branch=7.0)](https://travis-ci.org/openatv/enigma2) [![enigma2 build](https://github.com/openatv/enigma2/actions/workflows/enigma2.yml/badge.svg)](https://github.com/openatv/enigma2/actions/workflows/enigma2.yml) [![Translation status](https://hosted.weblate.org/widgets/openatv/-/enigma2-7-0-po/svg-badge.svg)](https://hosted.weblate.org/engage/openatv/)

## Translation - branch 7.0  status: ##

[![Translation status](https://hosted.weblate.org/widgets/openatv/-/enigma2-7-0-po/open-graph.png)](https://hosted.weblate.org/engage/openatv/)

## Our buildserver is currently running on: ##

> Ubuntu 20.04.3 LTS (Kernel 5.4.0) 64 Bit Server OS

## minimum hardware requirement : ##

> RAM:  16GB
> 
> SWAP: 8GB
> 
> CPU:  Multi core\thread Model
> 
> HDD:  for Single Build 250GB Free, for Multibuild 500GB or more

## openATV 7.0 is build using oe-alliance build-environment and several git repositories: ##

> [https://github.com/oe-alliance/oe-alliance-core/tree/5.0](https://github.com/oe-alliance/oe-alliance-core/tree/5.0 "OE-Alliance")
> 
> [https://github.com/openatv/enigma2/tree/7.0](https://github.com/openatv/enigma2/tree/7.0 "openATV E2")
> 
> [https://github.com/openatv/MetrixHD](https://github.com/openatv/MetrixHD/tree/dev "openATV Skin")

> and a lot more...


----------

# Building Instructions #

1 - Install packages on your buildserver

    sudo apt-get install -y autoconf automake bison bzip2 chrpath coreutils cpio curl cvs debianutils default-jre default-jre-headless diffstat flex g++ gawk gcc gcc-8 gcc-multilib g++-multilib gettext git git-core gzip help2man info iputils-ping java-common libc6-dev libegl1-mesa libglib2.0-dev libncurses5-dev libperl4-corelibs-perl libproc-processtable-perl libsdl1.2-dev libserf-dev libtool libxml2-utils make ncurses-bin patch perl pkg-config psmisc python3 python3-git python3-jinja2 python3-pexpect python3-pip python-setuptools qemu quilt socat sshpass subversion tar texi2html texinfo unzip wget xsltproc xterm xz-utils zip zlib1g-dev zstd 
    
----------
2 - Set python3 as preferred provider for python

    sudo update-alternatives --install /usr/bin/python python /usr/bin/python2 1
    sudo update-alternatives --install /usr/bin/python python /usr/bin/python3 2
    sudo update-alternatives --config python
    select python3
    
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
8 - Create folder openatv7.0

    mkdir -p ~/openatv7.0

----------
9 - Switch to folder openatv7.0

    cd openatv7.0

----------
10 - Clone oe-alliance git

    git clone git://github.com/oe-alliance/build-enviroment.git -b 5.0

----------
11 - Switch to folder build-enviroment

    cd build-enviroment

----------
12 - Update build-enviroment

    make update

----------
13 - Finally you can start building a image with feed (Build time 5-12h)

    MACHINE=zgemmah9combo DISTRO=openatv DISTRO_TYPE=release make image

----------
14 - Finally you can start building a image without feed (Build time 1-2h)

    MACHINE=zgemmah9combo DISTRO=openatv DISTRO_TYPE=release make enigma2-image

----------
15 - Finally you can start building a feed only

    MACHINE=zgemmah9combo DISTRO=openatv DISTRO_TYPE=release make feed

