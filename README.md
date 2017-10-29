## Our buildserver is currently running on: ##

> Ubuntu 16.04.1 LTS (GNU/3.14.32-xxxx-grs-ipv6-64)

## openATV 6.1 is build using oe-alliance build-environment and several git repositories: ##

> [https://github.com/oe-alliance/oe-alliance-core/tree/4.1](https://github.com/oe-alliance/oe-alliance-core/tree/4.1 "OE-Alliance")
> 
> [https://github.com/openatv/enigma2/tree/DEV](https://github.com/openatv/enigma2/tree/DEV "openATV E2")
> 
> [https://github.com/openatv/MetrixHD](https://github.com/openatv/MetrixHD "openATV Skin")

> and a lot more...


----------

# Building Instructions #

1 - Install packages on your buildserver

    sudo apt-get install -y autoconf automake bison bzip2 curl cvs diffstat flex g++ gawk gcc gettext git-core gzip help2man ncurses-bin ncurses-dev libc6-dev libtool make texinfo patch perl pkg-config subversion tar texi2html wget zlib1g-dev chrpath libxml2-utils xsltproc libglib2.0-dev python-setuptools zip info coreutils diffstat chrpath libproc-processtable-perl libperl4-corelibs-perl sshpass default-jre default-jre-headless java-common libserf-dev qemu quilt
----------
2 - Set your shell to /bin/bash.

    sudo dpkg-reconfigure dash
    When asked: Install dash as /bin/sh?
    select "NO"

----------
3 - Add user openatvbuilder

    sudo adduser openatvbuilder

----------
4 - Switch to user openatvbuilder

    su openatvbuilder

----------
5 - Switch to home of openatvbuilder

    cd ~

----------
6 - Create folder openatv

    mkdir -p ~/openatv

----------
7 - Switch to folder openatv

    cd openatv

----------
8 - Clone oe-alliance git

    git clone git://github.com/oe-alliance/build-enviroment.git -b 4.1

----------
9 - Switch to folder build-enviroment

    cd build-enviroment

----------
10 - Update build-enviroment

    make update

----------
11 - Finally you can start building a image

    MACHINE=mutant2400 DISTRO=openatv DISTRO_TYPE=release make image
