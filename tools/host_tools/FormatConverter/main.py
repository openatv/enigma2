#!/usr/bin/python
import os

from datasource import genericdatasource
from satxml import satxml
from lamedb import lamedb
from input import *


maindata = genericdatasource()

sources = [satxml, lamedb]

datasources = [maindata]

for source in sources:
	datasources.append(source())

for source in datasources:
	source.setDatasources(datasources)

while True:
	os.system("/usr/bin/clear")
	list = []
	for index in range(len(datasources)):
		list.append(datasources[index].getName() + (" (%d sats)" % len(datasources[index].transponderlist.keys())))
	index = inputChoices(list, "q", "quit")
	if index is None:
		break

	while True:
		print datasources[index].getStatus()
		list = []
		for action in datasources[index].getCapabilities():
			list.append(action[0])
		action = inputChoices(list)
		if action is None:
			break

		datasources[index].getCapabilities()[action][1]()
		#except:
		#	print sys.exc_info()
		#	print "sorry, could not execute that command"

