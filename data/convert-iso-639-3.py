import sys
import cPickle

infilename = "iso-639-3.tab"
outfilename = "iso-639-3.pck"

if len(sys.argv) > 1:
	infilename = sys.argv[1]
if len(sys.argv) > 2:
	outfilename = sys.argv[2]

l = {}

with open(infilename, 'r') as f:
	f.readline() # throw away header line
	for line in f:
		item = line.split('\t')
		name = (item[6],)
		for i in range(4):
			if item[i]:
				l[item[i]] = name

with open(outfilename, 'wb') as f:
	cPickle.dump(l, f, cPickle.HIGHEST_PROTOCOL)
