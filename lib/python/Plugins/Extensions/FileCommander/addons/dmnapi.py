#!/usr/bin/python -u
# -*- coding: UTF-8 -*-
# napiprojekt.pl API is used with napiproject administration consent

import re
import os
import os.path
import sys
import dmnapim

def get_all(file, supplement):
	rex = re.compile('.*\\.%s$' % file[-3:], re.I)

	(dir, fname) = os.path.split(file)

	for f in os.listdir(dir):
		if os.path.exists(os.path.join(dir, f[:-4] + '.srt')) and supplement:
			pass
		else:
			if rex.match(f):
				try:
					dmnapim.get_sub_from_napi(os.path.join(dir, f))
				except:
					print "  Error: %s" % (sys.exc_info()[1])

try:
	# opt fps videofile [subtitlefile]
	opt = sys.argv[1]
	try:
		fps = float(sys.argv[2]) / 1000
	except:
		fps = 0
	if opt == "get":
		file = os.path.abspath(sys.argv[3])
		dmnapim.get_sub_from_napi(file, fps=fps)
	elif opt == "all" or opt == 'allnew':
		file = os.path.abspath(sys.argv[3])
		get_all(file, opt == "allnew")
	elif opt == "convert":
		file = os.path.abspath(sys.argv[3])
		dmnapim.convert(file, sys.argv[4], fps=fps)
	elif opt == "upgrade":
		file = sys.argv[2]
		x, ipk = os.path.split(file)
		if os.path.exists("/usr/bin/opkg"):
			do = "opkg install " + ipk
		else:
			do = "ipkg install " + ipk
		print "Upgrade to:\n", file, "\n"
		os.system("cd /tmp ; rm -f enigma2-plugin-extensions-dmnapi*.ipk ; opkg update && wget -c %s && ls -al enigma2-plugin-extensions-dmnapi*.ipk && %s" % (file, do))
	elif opt == "n24":
		file = os.path.abspath(sys.argv[3])
		dmnapim.get_sub_from_n24(file, sys.argv[4], fps=fps)
except:
	print "  Error: %s" % (sys.exc_info()[1])
