# OpenATV 7.6

## Build status

[![enigma2 build](https://github.com/openatv/enigma2/actions/workflows/enigma2.yml/badge.svg)](https://github.com/openatv/enigma2/actions/workflows/enigma2.yml)

[Active Build Status](https://images.mynonpublic.com/openatv/build_status_arm_751.html "Active Build Status") - shows which box is currently being built 

## SonarCloud status
[![Vulnerabilities](https://sonarcloud.io/api/project_badges/measure?project=openatv_enigma2&metric=vulnerabilities)](https://sonarcloud.io/summary/new_code?id=openatv_enigma2)
[![Security Rating](https://sonarcloud.io/api/project_badges/measure?project=openatv_enigma2&metric=security_rating)](https://sonarcloud.io/summary/new_code?id=openatv_enigma2)
[![Bugs](https://sonarcloud.io/api/project_badges/measure?project=openatv_enigma2&metric=bugs)](https://sonarcloud.io/summary/new_code?id=openatv_enigma2)
[![Reliability Rating](https://sonarcloud.io/api/project_badges/measure?project=openatv_enigma2&metric=reliability_rating)](https://sonarcloud.io/summary/new_code?id=openatv_enigma2)
[![Maintainability Rating](https://sonarcloud.io/api/project_badges/measure?project=openatv_enigma2&metric=sqale_rating)](https://sonarcloud.io/summary/new_code?id=openatv_enigma2)
[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=openatv_enigma2&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=openatv_enigma2)

## Translation status

[![Translation status](https://hosted.weblate.org/widgets/openatv/-/enigma2-7-0-po/open-graph.png)](https://hosted.weblate.org/engage/openatv/)

# Build server specs

## Current OS

> Ubuntu 24.04.01 LTS (GNU/Linux 6.8.0-51-generic x86_64)

## Hardware requirements

> RAM:  16GB
>
> SWAP: 8GB
>
> CPU:  Multi core\thread Model
>
> HDD:  for Single Build 250GB Free, for Multibuild 500GB or more

## Git repositories involved

* [OE Alliance Core](https://github.com/oe-alliance/oe-alliance-core/tree/5.5.1 "OE Alliance Core") - Core framework
* [OpenATV 7.5.1](https://github.com/openatv/enigma2/tree/master "OpenATV 7.5.1") - OpenATV core
* [MetrixHD](https://github.com/openatv/MetrixHD/tree/master "OpenATV Skin") - Default OpenATV skin
* [OpenWebif](https://github.com/oe-alliance "OpenWebif") - OpenWebif
* [OE Alliance Plugins](https://github.com/oe-alliance/oe-alliance-plugins "OE Alliance Plugins") - OE Alliance Plugins
* [Enigm2 Plugins](https://github.com/oe-alliance/enigma2-plugins "Enigma2 Plugins") - Enigma2 Plugins
* [E2OpenPlugins](https://github.com/E2OpenPlugins "E2OpenPlugins") - E2OpenPlugins
* ...

## DOXYGEN Documentation

* [OpenATV enigma2](https://doxy.mynonpublic.com/ "OpenATV enigma2") -  OpenATV core

# Build instructions

1. Install required packages

    ```sh
    sudo apt-get install -y autoconf automake bison bzip2 chrpath cmake coreutils cpio curl cvs debianutils default-jre default-jre-headless diffstat flex g++ gawk gcc gcc-12 gcc-multilib g++-multilib gettext git gzip help2man info iputils-ping java-common libc6-dev libglib2.0-dev libncurses-dev libperl4-corelibs-perl libproc-processtable-perl libsdl1.2-dev libserf-dev libtool libxml2-utils make ncurses-bin patch perl pkg-config psmisc python3 python3-git python3-jinja2 python3-pexpect python3-pip python3-setuptools quilt socat sshpass subversion tar texi2html texinfo unzip wget xsltproc xterm xz-utils zip zlib1g-dev zstd fakeroot lz4 git-lfs
    ```

1. Set `python3` as preferred provider for `python`

    ```sh
    sudo update-alternatives --install /usr/bin/python python /usr/bin/python2 1

    sudo update-alternatives --install /usr/bin/python python /usr/bin/python3 2

    sudo update-alternatives --config python
    ↳ Select python3
    ```

1. Set your shell to `/bin/bash`

    ```sh
    sudo ln -sf /bin/bash /bin/sh
 
    ```

1. Modify `max_user_watches`

    ```sh
    echo fs.inotify.max_user_watches=524288 | sudo tee -a /etc/sysctl.conf

    sudo sysctl -n -w fs.inotify.max_user_watches=524288
    ```

1. Modify AppArmor config.

    ```sh
    echo 'kernel.apparmor_restrict_unprivileged_userns=0' | sudo tee /etc/sysctl.d/60-apparmor-namespace.conf > /dev/null && sudo sysctl --system

    sudo sysctl -w kernel.apparmor_restrict_unprivileged_userns=0
    ```

1. Add new user `openatvbuilder`

    ```sh
    sudo adduser openatvbuilder
    ```

1. Switch to new user `openatvbuilder`

    ```sh
    su - openatvbuilder
    ```

1. Add your git user and email

    ```sh
    git config --global user.email "you@example.com"

    git config --global user.name "Your Name"
    ```

1. Create folder openatv7.5.1

    ```sh
    mkdir -p openatv7.5.1
    ```

1. Switch to folder openatv7.5.1

    ```sh
    cd openatv7.5.1
    ```

1. Clone oe-alliance repository

    ```sh
    git clone https://github.com/oe-alliance/build-enviroment.git -b 5.5.1
    ```

1. Switch to folder build-enviroment

    ```sh
    cd build-enviroment
    ```

1. Update build-enviroment

    ```sh
    make update
    ```

1. Finally, you can either:

* Build an image with feed (build time 5-12h)

    ```sh
    MACHINE=zgemmah9combo DISTRO=openatv DISTRO_TYPE=release make image
    ```

* Build an image without feed (build time 1-2h)

    ```sh
    MACHINE=zgemmah9combo DISTRO=openatv DISTRO_TYPE=release make enigma2-image
    ```

* Build the feeds

    ```sh
    MACHINE=zgemmah9combo DISTRO=openatv DISTRO_TYPE=release make feeds
    ```

* Build specific packages

    ```sh
    MACHINE=zgemmah9combo DISTRO=openatv DISTRO_TYPE=release make init

    cd builds/openatv/release/zgemmah9combo/

    source env.source

    bitbake nfs-utils rpcbind ...
    ```
