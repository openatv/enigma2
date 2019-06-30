Beyonwiz enigma2 fork
---------------------

Build enigma2 for Beyonwiz V2 using the SDK:

    source /opt/beyonwiz/beyonwizv2/19.3/environment-setup-cortexa15hf-neon-vfpv4-oe-linux-gnueabi
    autoreconf -i
    mkdir build
    cd build
    ../configure-bw v2
    make

To build for other models, supply a different argument to `configure-bw` (i.e. t2, t3, t4, u4).
