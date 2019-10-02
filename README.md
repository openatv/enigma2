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

    sudo apt-get install -y gcc-8 psmisc git-core diffstat iputils-ping cpio debianutils socat unzip gcc-multilib libegl1-mesa xz-utils texinfo autoconf automake bison bzip2 curl cvs diffstat flex g++ gawk gcc gettext git gzip help2man ncurses-bin libncurses5-dev libc6-dev libtool make texinfo patch perl pkg-config subversion tar texi2html wget zlib1g-dev chrpath libxml2-utils xsltproc libglib2.0-dev python-setuptools python3 python3-pip python3-pexpect python3-git python3-jinja2 zip info coreutils diffstat libproc-processtable-perl libperl4-corelibs-perl sshpass default-jre default-jre-headless java-common libserf-dev qemu quilt libsdl1.2-dev xterm
2 - Set your shell to /bin/bash.

    sudo dpkg-reconfigure dash
    When asked: Install dash as /bin/sh?
    select "NO"

3 - Use update-alternatives for having gcc redirected automatically to gcc-8:
    sudo update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-7 700 --slave /usr/bin/g++ g++ /usr/bin/g++-7
    sudo update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-8 800 --slave /usr/bin/g++ g++ /usr/bin/g++-8

----------

4 - modify max_user_watches

    echo fs.inotify.max_user_watches=524288 | sudo tee -a /etc/sysctl.conf

    sysctl -n -w fs.inotify.max_user_watches=524288

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

