#read the comment to this file in lib/service/iservice.h !!
from os import remove, rename
import sys

filename = sys.argv[1]
rename(filename, filename + ".org")

source = open(filename + ".org")
dest = open(filename, "w")

for line, str in enumerate(source):
	oldstr = str[:]
	str = str.replace('_ENUMS)', ')')

	pos = str.find('_ENUMS')
	if pos != -1:
		spacepos = pos
		while spacepos > 0 and str[spacepos] != ' ':
			spacepos -= 1
		tmpstr = str[spacepos:pos]
		if '_enigma.' not in tmpstr:
			str = str[:pos] + str[pos + 6:]

	if oldstr != str:
		print("!!! Patch enigma.py line %d\n%s\n%s" % (line, oldstr[:len(oldstr) - 1], str))

	dest.write(str)

del source
del dest
remove(filename + ".org")
