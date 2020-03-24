## Our buildserver is currently running on: ##

> Ubuntu 18.04.1 LTS (Kernel 4.15.0)

## openATV 6.4 is build using oe-alliance build-environment and several git repositories: ##

> [https://github.com/oe-alliance/oe-alliance-core/tree/4.4](https://github.com/oe-alliance/oe-alliance-core/tree/4.4 "OE-Alliance")
> 
> [https://github.com/openatv/enigma2/tree/6.4](https://github.com/openatv/enigma2/tree/6.4 "openATV E2")
> 
> [https://github.com/openatv/MetrixHD](https://github.com/openatv/MetrixHD "openATV Skin")

> and a lot more...


----------

# Building Instructions #

1 - Install packages on your buildserver

    sudo apt-get install -y autoconf automake bison bzip2 chrpath coreutils cpio curl cvs debianutils default-jre default-jre-headless diffstat flex g++ gawk gcc gcc-8 gettext git git-core gzip help2man info iputils-ping java-common libc6-dev libegl1-mesa libglib2.0-dev libncurses5-dev libperl4-corelibs-perl libproc-processtable-perl libsdl1.2-dev libserf-dev libtool libxml2-utils make ncurses-bin patch perl pkg-config psmisc python3 python3-git python3-jinja2 python3-pexpect python3-pip python-setuptools qemu quilt socat sshpass subversion tar texi2html texinfo unzip wget xsltproc xterm xz-utils zip zlib1g-dev 

----------
2 - Set your shell to /bin/bash.

    sudo dpkg-reconfigure dash
    When asked: Install dash as /bin/sh?
    select "NO"

----------
3 - Use update-alternatives for having gcc redirected automatically to gcc-8

    sudo update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-7 700 --slave /usr/bin/g++ g++ /usr/bin/g++-7
    sudo update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-8 800 --slave /usr/bin/g++ g++ /usr/bin/g++-8

----------
4 - Repair g++ after gcc8 installation

    sudo apt-get remove -y  g++
    sudo apt-get install -y  g++

----------
5 - modify max_user_watches

    echo fs.inotify.max_user_watches=524288 | sudo tee -a /etc/sysctl.conf

    sudo sysctl -n -w fs.inotify.max_user_watches=524288

----------
6 - Add user openatvbuilder

    sudo adduser openatvbuilder

----------
7 - Switch to user openatvbuilder

    su openatvbuilder

----------
8 - Switch to home of openatvbuilder

    cd ~

----------
9 - Create folder openatv

    mkdir -p ~/openatv

----------
10 - Switch to folder openatv

    cd openatv

----------
11 - Clone oe-alliance git

    git clone git://github.com/oe-alliance/build-enviroment.git -b 4.4

----------
12 - Switch to folder build-enviroment

    cd build-enviroment

----------
13 - Update build-enviroment

    make update

----------
14 - Finally you can start building a image

    MACHINE=zgemmah9combo DISTRO=openatv DISTRO_TYPE=release make image

