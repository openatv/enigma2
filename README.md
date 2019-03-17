Beyonwiz enigma2 fork
---------------------

Build enigma2 for Beyonwiz V2 using the SDK:

    source /opt/beyonwiz/beyonwizv2/19.3/environment-setup-cortexa15hf-neon-vfpv4-oe-linux-gnueabi
    autoreconf -i
    mkdir build
    cd build
    ../configure $CONFIGURE_FLAGS \
      BUILD_SYS=x86_64-linux \
      HOST_SYS=${TARGET_PREFIX%-} \
      STAGING_INCDIR=${SDKTARGETSYSROOT}/usr/include \
      STAGING_LIBDIR=${SDKTARGETSYSROOT}/usr/lib \
      PYTHON_VERSION=2.7 \
      PYTHON_CPPFLAGS=-I${SDKTARGETSYSROOT}/usr/include/python2.7 \
      PYTHON_LDFLAGS="-L${SDKTARGETSYSROOT}/usr/lib -lpython2.7" \
      PYTHON_SITE_PKG=${SDKTARGETSYSROOT}/usr/lib/python2.7/site-packages \
      --prefix=/usr \
      --libexecdir=/usr/lib/enigma2 \
      --sysconfdir=/etc \
      --localstatedir=/var \
      --enable-silent-rules \
      --enable-dependency-tracking \
      --with-gstversion=1.0 \
      --with-textlcd   \
      --with-7segment \
      --with-lcddev=/dev/null \
      --with-libsdl=no \
      --with-alphablendingacceleration=always \
      --with-blitaccelerationthreshold=250 \
      --with-fillaccelerationthreshold=190000 \
      --with-machinebuild=beyonwizv2 \
      --with-boxtype=beyonwizv2
    make

To build for other models, adjust the --with arguments.
For example, T4 needs:
      --with-gstversion=1.0 \
      --with-bwlcd255 \
      --with-boxtype=inihdp \
