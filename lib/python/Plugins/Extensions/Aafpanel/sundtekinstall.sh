#!/bin/sh

if [ -e "/tmp/sundtek_installer_development.sh" ]; then
    #installer script already exits
    #so we remove it
    rm /tmp/sundtek_installer_development.sh > /dev/null 2>&1
fi
    ## install development driver
    cd /tmp
    wget http://www.sundtek.de/media/sundtek_installer_development.sh
    chmod 755 sundtek_installer_development.sh
    /tmp/sundtek_installer_development.sh -easyvdr
