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

	refstr = "1:0:%d:%X:%X:%X:%X:%d:0:0" % (ref[4], ref[0], ref[2], ref[3], ref[1], ref[5])
	refstr = refstr.replace(':', '_')

	filename = name + ".png"
	linkname = refstr + ".png"

	if os.access(filename, os.F_OK) and not os.access(linkname, os.F_OK):
		os.symlink(filename, linkname)
	else:
		print "could not find PNG for %s" % name
	f =f[3:]
