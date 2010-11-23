DESCRIPTION = "Enigma2 is an experimental, but useful framebuffer-based frontend for DVB functions"
DESCRIPTION_append_enigma2-plugin-extensions-cutlisteditor = "enables you to cut your movies."
DESCRIPTION_append_enigma2-plugin-extensions-graphmultiepg = "shows a graphical timeline EPG."
DESCRIPTION_append_enigma2-plugin-extensions-pictureplayer = "displays photos on the TV."
DESCRIPTION_append_enigma2-plugin-systemplugins-frontprocessorupdate = "keeps your frontprocessor up to date."
DESCRIPTION_append_enigma2-plugin-systemplugins-positionersetup = "helps you installing a motorized dish."
DESCRIPTION_append_enigma2-plugin-systemplugins-satelliteequipmentcontrol = "allows you to fine-tune DiSEqC-settings."
DESCRIPTION_append_enigma2-plugin-systemplugins-satfinder = "helps you to align your dish."
DESCRIPTION_append_enigma2-plugin-systemplugins-skinselector = "shows a menu with selectable skins."
DESCRIPTION_append_enigma2-plugin-systemplugins-videomode = "selects advanced video modes"
DESCRIPTION_append_enigma2-plugin-systemplugins-crashlogautosubmit = "automatically send crashlogs to Dream Multimedia"
DESCRIPTION_append_enigma2-plugin-systemplugins-cleanupwizard = "informs you on low internal memory on system startup."
DESCRIPTION_append_enigma2-plugin-extenstions-modem = "opens a menu to connect to internet via builtin modem."
DESCRIPTION_append_enigma2-plugin-systemplugins-wirelesslan = "helps you configuring your wireless lan"
DESCRIPTION_append_enigma2-plugin-systemplugins-networkwizard = "provides easy step by step network configuration"

DEPENDS = "jpeg libungif libpng libsigc++-1.2 gettext-native \
        dreambox-dvbincludes freetype libdvbsi++ python swig-native \
        libfribidi libxmlccwrap libdreamdvd gstreamer gst-plugin-dvbmediasink \
        gst-plugins-bad gst-plugins-good gst-plugins-ugly python-wifi"

RDEPENDS = "python-codecs python-core python-lang python-re python-threading \
        python-xml python-fcntl gst-plugin-decodebin gst-plugin-decodebin2 python-stringold \
        python-pickle gst-plugin-app \
        gst-plugin-id3demux gst-plugin-mad gst-plugin-ogg gst-plugin-playbin \
        gst-plugin-typefindfunctions gst-plugin-audioconvert gst-plugin-audioresample \
        gst-plugin-wavparse python-netclient gst-plugin-mpegstream gst-plugin-selector \
        gst-plugin-flac gst-plugin-dvbmediasink gst-plugin-mpegdemux \
        gst-plugin-souphttpsrc gst-plugin-mpegaudioparse gst-plugin-subparse \
        gst-plugin-apetag gst-plugin-icydemux gst-plugin-autodetect \
        glibc-gconv-iso8859-15 ethtool"

GST_ALSA_RDEPENDS = "gst-plugin-alsa alsa-conf"
GST_DVD_RDEPENDS = "gst-plugin-cdxaparse gst-plugin-cdio gst-plugin-vcdsrc"
GST_MISC_RDEPENDS = "gst-plugin-matroska gst-plugin-qtdemux gst-plugin-vorbis gst-plugin-audioparsersbad"
GST_RTSP_RDEPENDS = "gst-plugin-udp gst-plugin-rtsp gst-plugin-rtp gst-plugin-rtpmanager"
GST_BASE_RDEPENDS = "${GST_ALSA_RDEPENDS} ${GST_MISC_RDEPENDS} ${GST_RTSP_RDEPENDS}"

RDEPENDS_append_dm800 = " ${GST_BASE_RDEPENDS} gst-plugin-ivorbisdec"
RDEPENDS_append_dm8000 = " ${GST_BASE_RDEPENDS} ${GST_DVD_RDEPENDS} gst-plugin-avi"
RDEPENDS_append_dm500hd = " ${GST_BASE_RDEPENDS} ${GST_DVD_RDEPENDS} gst-plugin-avi"
RDEPENDS_append_dm800se = " ${GST_BASE_RDEPENDS} ${GST_DVD_RDEPENDS} gst-plugin-avi"

RDEPENDS_enigma2-plugin-extensions-cutlisteditor = "aio-grab"
RDEPENDS_enigma2-plugin-extensions-dvdplayer = "libdreamdvd0"
RDEPENDS_enigma2-plugin-systemplugins-nfiflash = "python-twisted-web"
RDEPENDS_enigma2-plugin-systemplugins-softwaremanager = "python-twisted-web"
RDEPENDS_enigma2-plugin-systemplugins-crashlogautosubmit = "twisted-mail twisted-names python-compression python-mime python-email"
RDEPENDS_enigma2-plugin-extensions-modem = "dreambox-modem-ppp-scripts ppp"
RDEPENDS_enigma2-plugin-systemplugins-wirelesslan = "wpa-supplicant wireless-tools python-wifi"

RCONFLICTS_enigma2-plugin-systemplugins-softwaremanager = "enigma2-plugin-systemplugins-configurationbackup enigma2-plugin-systemplugins-softwareupdate"
RREPLACES_enigma2-plugin-systemplugins-softwaremanager = "enigma2-plugin-systemplugins-configurationbackup enigma2-plugin-systemplugins-softwareupdate"

PV = "${GITVER}"

inherit srctree autotools gitver pkgconfig

EXTRA_OECONF = " \
        BUILD_SYS=${BUILD_SYS} \
        HOST_SYS=${HOST_SYS} \
        STAGING_INCDIR=${STAGING_INCDIR} \
        STAGING_LIBDIR=${STAGING_LIBDIR} \
"

PACKAGE_ARCH = "${MACHINE_ARCH}"
PACKAGES += "${PN}-meta"

FILES_${PN} += "${datadir}/fonts"
FILES_${PN}-meta = "${datadir}/meta"

python populate_packages_prepend () {
        enigma2_plugindir = bb.data.expand('${libdir}/enigma2/python/Plugins', d)
        do_split_packages(d, enigma2_plugindir, '(.*?/.*?)/.*', 'enigma2-plugin-%s', '%s ', recursive=True, match_path=True, prepend=True)
}
