# -*- coding: utf-8 -*-
# plnick@vuplus-support.org

from os import path

def getExtendedMovieDescription(ref):
	f = None
	extended_desc = ""
	name = ""
	extensions = (".txt", ".info")
	info_file = path.realpath(ref.getPath())
	name = path.basename(info_file)
	ext_pos = name.rfind('.')
	if ext_pos > 0:
		name = (name[:ext_pos]).replace("_", " ")
	else:
		name = name.replace("_", " ")
	for ext in extensions:
		if path.exists(info_file + ext):
			f = info_file + ext
			break
	if not f:	
		ext_pos = info_file.rfind('.')
		name_len = len(info_file)
		ext_len = name_len - ext_pos
		if ext_len <= 5:
			info_file = info_file[:ext_pos]
			for ext in extensions:
				if path.exists(info_file + ext):
					f = info_file + ext
					break
	if f:
		with open (f, "r") as txtfile:
			extended_desc = txtfile.read()
	
	return (name, extended_desc)
