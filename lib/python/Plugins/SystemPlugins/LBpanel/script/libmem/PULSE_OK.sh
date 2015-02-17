#!/bin/sh
# by: ††LUCIFER††
echo ""
MEMORYUSADA=`free | awk '/Mem:/ {print int(100*$3/$2) ;}'`
echo "Memoria usada gigablue: $MEMORYUSADA %"
[ $MEMORYUSADA -ge 80 ];
sync
sleep 2 
echo 3 > /proc/sys/vm/drop_caches
echo ""
MEMORYUSADA=`free | awk '/Mem:/ {print int(100*$3/$2) ;}'`
echo "Memoria usada gigablue tras liberar: $MEMORYUSADA %"


exit 0
