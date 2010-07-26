#
# create links for picon
#   usage: create_picon_links lamedb
# run in picon directory.
# It will read the servicenames from the lamedb and create symlinks
# for the servicereference names.

import os, sys

f = open(sys.argv[1]).readlines()

f = f[f.index("services\n")+1:-3]

while len(f):
	ref = [int(x, 0x10) for x in f[0][:-1].split(':')]
	name = f[1][:-1]

	name = name.replace('\xc2\x87', '').replace('\xc2\x86', '')

#	SID:NS:TSID:ONID:STYPE:UNUSED(channelnumber in enigma1)
#	X   X  X    X    D     D

#	REFTYPE:FLAGS:STYPE:SID:TSID:ONID:NS:PARENT_SID:PARENT_TSID:UNUSED
#	D       D     X     X   X    X    X  X          X           X

	refstr = "1:0:%X:%X:%X:%X:%X:0:0:0" % (ref[4], ref[0], ref[2], ref[3], ref[1])
	refstr = refstr.replace(':', '_')

	filename = name + ".png"
	linkname = refstr + ".png"

	if os.access(filename, os.F_OK) and not os.access(linkname, os.F_OK):
		os.symlink(filename, linkname)
	else:
		print "could not find PNG for %s" % name
	f =f[3:]
