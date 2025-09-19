#
# create links for picon
#   usage: create_picon_providers lamedb
# run in picon directory.
# It will read the servicenames from the lamedb and create symlinks
# for the servicereference names.

from os import makedirs, symlink
import sys

f = open(sys.argv[1]).readlines()

f = f[f.index("services\n") + 1:-3]

while len(f) > 2:
	ref = [int(x, 0x10) for x in f[0][:-1].split(':')]
	name = f[1][:-1]
	name = name.replace('\xc2\x87', '').replace('\xc2\x86', '')

	fields = f[2].split(',')
	if len(fields) and fields[0][0] == 'p':
		provider = fields[0].split(':')[1]
	else:
		provider = 'unknown'

	if ref[4] == 1:
		servicetype = 'tv'
	elif ref[4] == 2:
		servicetype = 'radio'
	else:
		servicetype = 'unknown'

	sat = str(ref[1] / 16 / 16 / 16 / 16)

#	SID:NS:TSID:ONID:STYPE:UNUSED(channelnumber in enigma1)
#	X   X  X    X    D     D

#	REFTYPE:FLAGS:STYPE:SID:TSID:ONID:NS:PARENT_SID:PARENT_TSID:UNUSED
#   D       D     X     X   X    X    X  X          X           X

	refstr = f"1:0:{ref[4]:X}:{ref[0]:X}:{ref[2]:X}:{ref[3]:X}:{ref[1]:X}:0:0:0"
	refstr = refstr.replace(':', '_')

	filename = f"{name}.png"
	linkname = f"{refstr}.png"

	filename = filename.replace('/', '_').replace('\\', '_').replace('&', '_').replace('\'', '').replace('"', '').replace('`', '').replace('*', '_').replace('?', '_').replace(' ', '_').replace('(', '_').replace(')', '_')
	provider = provider.replace('/', '_').replace('\\', '_').replace('&', '_').replace('\'', '').replace('"', '').replace('`', '').replace('*', '_').replace('?', '_').replace(' ', '_').replace('(', '_').replace(')', '_')
	filename = filename.replace('\n', '')
	provider = provider.replace('\n', '')

	for i in list(range(len(filename))):
		if ord(filename[i]) > 127:
			filename = f"{filename[0:i]}_{filename[i + 1:]}"

	for i in list(range(len(provider))):
		if ord(provider[i]) > 127:
			provider = f"{provider[0:i]}_{provider[i + 1:]}"

	filename = f"{sat}_{provider}_{servicetype}_{filename}"

	try:
		makedirs(f"{sat}/{servicetype}/{provider}")
	except OSError:
		pass

	try:
		symlink(filename, f"{sat}/{servicetype}/{provider}/{linkname}")
	except OSError:
		pass

	f = f[3:]
