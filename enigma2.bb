DESCRIPTION = "Enigma2 is an experimental, but useful framebuffer-based frontend for DVB functions"
MAINTAINER = "OpenATV"
LICENSE = "GPLv2"
LIC_FILES_CHKSUM = "file://LICENSE;md5=b234ee4d69f5fce4486a80fdaf4a4263"

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

do_unpack[noexec] = "1"
do_patch[no_exec] = "1"
do_populate_sysroot[noexec] = "1"
do_populate_lic[noexec] = "1"
do_packagedata[noexec] = "1"
do_package_write_ipk[noexec] = "1"
do_rm_work[noexec] = "1"
do_rm_work_all[noexec] = "1"

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
    ${@bb.utils.contains("GST_VERSION", "1.0", "--with-gstversion=1.0", "", d)} \
    ${@bb.utils.contains("MACHINE_FEATURES", "textlcd", "--with-textlcd" , "", d)} \
    ${@bb.utils.contains("MACHINE_FEATURES", "colorlcd", "--with-colorlcd" , "", d)} \
    ${@bb.utils.contains("MACHINE_FEATURES", "colorlcd128", "--with-colorlcd128" , "", d)} \
    ${@bb.utils.contains("MACHINE_FEATURES", "colorlcd220", "--with-colorlcd220" , "", d)} \
    ${@bb.utils.contains("MACHINE_FEATURES", "colorlcd400", "--with-colorlcd400" , "", d)} \
    ${@bb.utils.contains("MACHINE_FEATURES", "colorlcd480", "--with-colorlcd480" , "", d)} \
    ${@bb.utils.contains("MACHINE_FEATURES", "colorlcd720", "--with-colorlcd720" , "", d)} \
    ${@bb.utils.contains("MACHINE_FEATURES", "colorlcd800", "--with-colorlcd800" , "", d)} \
    ${@bb.utils.contains("MACHINE_FEATURES", "bwlcd128", "--with-bwlcd128" , "", d)} \
    ${@bb.utils.contains("MACHINE_FEATURES", "bwlcd140", "--with-bwlcd140" , "", d)} \
    ${@bb.utils.contains("MACHINE_FEATURES", "bwlcd255", "--with-bwlcd255" , "", d)} \
    ${@bb.utils.contains("MACHINE_FEATURES", "fullgraphiclcd", "--with-fullgraphiclcd" , "", d)} \
    ${@bb.utils.contains("MACHINE_FEATURES", "gigabluelcd", "--with-gigabluelcd" , "", d)} \
    ${@bb.utils.contains("MACHINE_FEATURES", "nolcd", "--with-nolcd" , "", d)} \
    ${@bb.utils.contains("TARGET_ARCH", "sh4", "--enable-sh=yes " , "", d)} \
    ${@bb.utils.contains("MACHINE_FEATURES", "uianimation", "--with-libvugles2" , "", d)} \
    ${@bb.utils.contains("MACHINE_FEATURES", "osdanimation", "--with-osdanimation" , "", d)} \
    "

LDFLAGS_prepend = "${@bb.utils.contains('GST_VERSION', '1.0', ' -lxml2 ', '', d)}"

do_install_append() {
    install -d ${D}/usr/share/keymaps
}

python populate_packages_prepend () {
    enigma2_plugindir = bb.data.expand('${libdir}/enigma2/python/Plugins', d)
    do_split_packages(d, enigma2_plugindir, '(.*?/.*?)/.*', 'enigma2-plugin-%s', '%s ', recursive=True, match_path=True, prepend=True, extra_depends="enigma2")
}
