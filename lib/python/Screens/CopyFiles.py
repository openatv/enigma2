import os
from twisted.internet import reactor, threads

def copyHandles(handles):
	print "copyHandles: ", len(handles)
	try:
		for src, dst in handles:
			while 1:
				d = src.read(32168)
				if not d:
					# EOF
					src.close()
					dst.close()
					break
				dst.write(d)
	except:
		# On failure, close all handles
		for src, dst in handles:
			src.close()
			dst.close()
		raise
		

def copyFiles(fileList, onComplete):
	# filelist must be list of tuple(source, dest)
	# onDone/onFail will be called with fileList as argument.
	# First open ALL files, so that they cannot be deleted behind our back.
	handles = [(open(fn[0], 'rb'), open(fn[1], 'wb')) for fn in fileList]
	print "open handles: ", len(handles)
	threads.deferToThread(copyHandles, handles).addBoth(onComplete, (fileList,))


# Unit test
if __name__ == '__main__':
	import sys
	fl = [	('CopyFiles.py', '/tmp/CopyFiles.py'),
		('MovieSelection.py', '/tmp/MovieSelection.py'),
	     ]
	
	def copyDone(result, fileList):
		print "Finished copy result:", result, "fileList", fileList
		reactor.stop()
	
	copyFiles(fl, copyDone)
	reactor.run()
