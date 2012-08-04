#!/usr/bin/python
# don't expect too much.
# this is a really simple&stupid svg parser, which will use rectangles 
# and text fields to produce <widget> snippets for a skin.
# use object "id" fields for source names if you want.
# extracting font information is buggy.
# if you want text fields, please use flow text regions, instead of simple
# text. otherwise, width and height are unknown.
#
# tested only with a single inkscape-generated SVG.

import sys
import os
import string
from xml.sax import make_parser
from xml.sax.handler import ContentHandler

def getattrs(attrs, *a):
	res = []
	for x in a:
		res.append(float(attrs[x]))
	return res

def parsedict(attrs):
	if not attrs:
		return []
	d = attrs.split(';')
	r = { }
	for x in d:
		(key, val) = x.split(':')
		r[key] = val
	return r

def px(x):
	return int(float(x[:-2]) + .5)

def contains(box_o, box_i):
	return box_o[0] <= box_i[0] and box_o[1] <= box_i[1] and box_o[2] >= box_i[2] and box_o[3] >= box_i[3]

class parseXML(ContentHandler):
	def __init__(self):
		self.isPointsElement, self.isReboundsElement = 0, 0
		self.bbox = None
		self.find_bbox = False
		self.flow = None

	def startElement(self, name, attrs):
		if self.find_bbox:
			if name != "rect":
				return
			box = getattrs(attrs, "x", "y", "width", "height")
			if not self.bbox or contains(box, self.bbox):
				self.bbox = box
			return

		if name == "rect":
			(x, y, width, height) = getattrs(attrs, "x", "y", "width", "height")
			x -= self.bbox[0]
			y -= self.bbox[1]
			id = attrs["id"]
			if self.flow:
				id = self.flow
				self.flow = None
			styles = parsedict(attrs.get("style", ""))
		elif name == "text":
			(x, y) = getattrs(attrs, "x", "y")
			x -= self.bbox[0]
			y -= self.bbox[1]
			width, height = 0, 0
			styles = parsedict(attrs["style"])
			id = attrs["id"]
		elif name == "flowRoot":
			self.flow = attrs["id"]
			return
		else:
			return

		if "font-size" in styles:
			font = ' font="Regular;%d"' % px(styles["font-size"])
		else:
			font = ""
		print """\t\t<widget source="%s" render="Label" position="%d,%d" size="%d,%d" %s />""" % (id, x, y, width, height, font)

parser = make_parser()
contentHandler = parseXML()
parser.setContentHandler(contentHandler)
contentHandler.find_bbox = True
parser.parse(sys.argv[1])
bboxi = tuple([int(x) for x in contentHandler.bbox])
contentHandler.find_bbox = False
print '\t<screen name="" position="%d,%d" size="%d,%d" title="">' % bboxi
parser.parse(sys.argv[1])
print '\t</screen>'
