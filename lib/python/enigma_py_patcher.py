#read the comment to this file in lib/service/iservice.h !!
import sys
import os

filename = sys.argv[1]
os.rename(filename, filename + ".org")

source=open(filename + ".org", "r")
dest=open(filename, "w")

for line, str in enumerate(source):
	oldstr = str[:]
	str = str.replace('_ENUMS)', ')')

	pos = str.find('_ENUMS')
	if pos != -1:
		spacepos = pos
		while spacepos > 0 and str[spacepos] != ' ':
			spacepos -= 1
		tmpstr = str[spacepos:pos]
		if tmpstr.find('_enigma.') == -1:
			str = str[:pos]+str[pos+6:]

	if oldstr != str:
		print "!!! Patch enigma.py line %d\n%s\n%s" %(line, oldstr[:len(oldstr)-1], str)

	dest.write(str)

del source
del dest
os.remove(filename + ".org")

