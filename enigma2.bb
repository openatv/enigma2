DESCRIPTION = "Enigma2 is an experimental, but useful framebuffer-based frontend for DVB functions"
MAINTAINER = "OpenATV"
LICENSE = "GPLv2"
LIC_FILES_CHKSUM = "file://LICENSE;md5=751419260aa954499f7abaabaa882bbe"

inherit gitpkgv externalsrc

S = "${FILE_DIRNAME}"
WORKDIR = "${S}/build"

PV = "2.7+git"
PKGV = "2.7+git${GITPKGV}"
PR = "r26"

FILES_${PN} += "${datadir}/keymaps"
FILES_${PN}-meta = "${datadir}/meta"
PACKAGES =+ "${PN}-src"
PACKAGES += "${PN}-meta"
PACKAGE_ARCH = "${MACHINE_ARCH}"

inherit autotools-brokensep pkgconfig pythonnative

ACLOCALDIR = "${B}/aclocal-copy"
e2_copy_aclocal () {
        rm -rf ${ACLOCALDIR}/
        mkdir -p ${ACLOCALDIR}/
        if [ -d ${STAGING_DATADIR_NATIVE}/aclocal ]; then
                cp-noerror ${STAGING_DATADIR_NATIVE}/aclocal/ ${ACLOCALDIR}/
        fi
        if [ -d ${STAGING_DATADIR}/aclocal -a "${STAGING_DATADIR_NATIVE}/aclocal" != "${STAGING_DATADIR}/aclocal" ]; then
                cp-noerror ${STAGING_DATADIR}/aclocal/ ${ACLOCALDIR}/
        fi
}

EXTRACONFFUNCS += "e2_copy_aclocal"

ACLOCALDIR = "${B}/aclocal-copy"
e2_copy_aclocal () {
	rm -rf ${ACLOCALDIR}/
	mkdir -p ${ACLOCALDIR}/
	if [ -d ${STAGING_DATADIR_NATIVE}/aclocal ]; then
		cp-noerror ${STAGING_DATADIR_NATIVE}/aclocal/ ${ACLOCALDIR}/
	fi
	if [ -d ${STAGING_DATADIR}/aclocal -a "${STAGING_DATADIR_NATIVE}/aclocal" != "${STAGING_DATADIR}/aclocal" ]; then
		cp-noerror ${STAGING_DATADIR}/aclocal/ ${ACLOCALDIR}/
	fi
}

EXTRACONFFUNCS += "e2_copy_aclocal"

bindir = "/usr/bin"
sbindir = "/usr/sbin"

EXTRA_OECONF = " \
    BUILD_SYS=${BUILD_SYS} \
    HOST_SYS=${HOST_SYS} \
    STAGING_INCDIR=${STAGING_INCDIR} \
    STAGING_LIBDIR=${STAGING_LIBDIR} \
    --with-boxtype=${MACHINE} \
    --with-machinebuild="${MACHINEBUILD}" \
    --with-libsdl=no \
    --enable-dependency-tracking \
    ${@base_contains("GST_VERSION", "1.0", "--with-gstversion=1.0", "", d)} \
    ${@base_contains("MACHINE_FEATURES", "textlcd", "--with-textlcd" , "", d)} \
    ${@base_contains("MACHINE_FEATURES", "colorlcd", "--with-colorlcd" , "", d)} \
    ${@base_contains("MACHINE_FEATURES", "colorlcd128", "--with-colorlcd128" , "", d)} \
    ${@base_contains("MACHINE_FEATURES", "colorlcd220", "--with-colorlcd220" , "", d)} \
    ${@base_contains("MACHINE_FEATURES", "colorlcd400", "--with-colorlcd400" , "", d)} \
    ${@base_contains("MACHINE_FEATURES", "colorlcd480", "--with-colorlcd480" , "", d)} \
    ${@base_contains("MACHINE_FEATURES", "colorlcd720", "--with-colorlcd720" , "", d)} \
    ${@base_contains("MACHINE_FEATURES", "bwlcd128", "--with-bwlcd128" , "", d)} \
    ${@base_contains("MACHINE_FEATURES", "bwlcd140", "--with-bwlcd140" , "", d)} \
    ${@base_contains("MACHINE_FEATURES", "bwlcd255", "--with-bwlcd255" , "", d)} \
    ${@base_contains("MACHINE_FEATURES", "fullgraphiclcd", "--with-fullgraphiclcd" , "", d)} \
    ${@base_contains("MACHINE_FEATURES", "gigabluelcd", "--with-gigabluelcd" , "", d)} \
    ${@base_contains("MACHINE_FEATURES", "nolcd", "--with-nolcd" , "", d)} \
    ${@base_contains("TARGET_ARCH", "sh4", "--enable-sh=yes " , "", d)} \
    ${@base_contains("MACHINE_FEATURES", "uianimation", "--with-libvugles2" , "", d)} \
    ${@base_contains("MACHINE_FEATURES", "osdanimation", "--with-osdanimation" , "", d)} \
    "

LDFLAGS_prepend = "${@base_contains('GST_VERSION', '1.0', ' -lxml2 ', '', d)}"

do_install_append() {
    install -d ${D}/usr/share/keymaps
}

python populate_packages_prepend () {
    enigma2_plugindir = bb.data.expand('${libdir}/enigma2/python/Plugins', d)
    do_split_packages(d, enigma2_plugindir, '(.*?/.*?)/.*', 'enigma2-plugin-%s', '%s ', recursive=True, match_path=True, prepend=True, extra_depends="enigma2")
}
