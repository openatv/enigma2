## Our buildserver is currently running on: ##

> Ubuntu 12.04.5 LTS (GNU/Linux 3.2.13-grsec-xxxx-grs-ipv6-64 x86_64)

## openATV is build using oe-alliance build-environment and several git repositories: ##

> [https://github.com/oe-alliance/oe-alliance-core](https://github.com/oe-alliance/oe-alliance-core "OE-Alliance")
> 
> [https://github.com/openatv/enigma2](https://github.com/openatv/enigma2 "openATV E2")
> 
> [https://github.com/openatv/MetrixHD](https://github.com/openatv/MetrixHD "openATV Skin")

> and a lot more...


----------

# Building Instructions #

1 - Install packages on your buildserver

    sudo apt-get install -y autoconf automake bison bzip2 chrpath coreutils cvs default-jre default-jre-headless diffstat flex g++ gawk gcc gettext git-core gzip help2man htop info java-common libc6-dev libglib2.0-dev libperl4-corelibs-perl libproc-processtable-perl libtool libxml2-utils make ncdu ncurses-bin ncurses-dev patch perl pkg-config po4a python-setuptools quilt sgmltools-lite sshpass subversion swig tar texi2html texinfo wget xsltproc zip zlib1g-dev

----------
2 - Add user openatvbuilder

    sudo adduser openmipsbuilder

----------
3 - Switch to user openatvbuilder

    su openmipsbuilder

----------
4 - Switch to home of openatvbuilder

    cd ~

----------
5 - Create folder openmips

    mkdir -p ~/openatv

----------
6 - Switch to folder openmips

    cd openatv

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

    make MACHINE=gbquadplus DISTRO=openatv image
