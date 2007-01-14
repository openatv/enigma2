#read the comment to this file in lib/service/iservice.h !!

import os

os.rename("enigma.py", "enigma.py.org")

source=open("enigma.py.org", "r")
dest=open("enigma.py", "w")

line=1
for str in source.readlines():
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
	line += 1

del source
del dest
os.remove("enigma.py.org")
