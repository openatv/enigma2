# logging for XMLTV importer
#
# One can simply use
# import log
# print>>log, "Some text"
# because the log unit looks enough like a file!

import sys
import threading
from io import StringIO

logfile = None
# Need to make our operations thread-safe.
mutex = None

size = None


def open(buffersize=16384):
	global logfile, mutex, size
	if logfile is None:
		logfile = StringIO()
		mutex = threading.Lock()
		size = buffersize


def write(data):
	global logfile, mutex
	mutex.acquire()
	try:
		if logfile.tell() > size:
			# Do a sort of 16k round robin
			logfile.seek(0)
		logfile.write(data)
	finally:
		mutex.release()
	sys.stdout.write(data)


def getvalue():
	global logfile, mutex
	mutex.acquire()
	try:
		pos = logfile.tell()
		head = logfile.read()
		logfile.seek(0)
		tail = logfile.read(pos)
	finally:
		mutex.release()
	return head + tail


def close():
	global logfile
	if logfile:
		logfile.close()
		logfile = None
