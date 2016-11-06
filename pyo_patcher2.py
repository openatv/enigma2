import os

filename = "/usr/lib/enigma2/python/Plugins/Extensions/CoolTVGuide/plugin.pyo"
os.rename(filename, filename + ".org")

source=open(filename + ".org", "r")
dest=open(filename, "w")

for line, str in enumerate(source):
	oldstr = str[:]
	str = str.replace('2017', '2025')

	if oldstr != str:
		print "!!! Patch pyo line %d" %(line)

	dest.write(str)

del source
del dest
os.remove(filename + ".org")

