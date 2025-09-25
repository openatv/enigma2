#!/usr/bin/python
from os import system

from datasource import genericdatasource
from satxml import satxml
from lamedb import lamedb
from input import inputChoices


maindata = genericdatasource()

sources = [satxml, lamedb]

datasources = [maindata]

for source in sources:
	datasources.append(source())

for source in datasources:
	source.setDatasources(datasources)

while True:
	system("/usr/bin/clear")
	items = []
	for index in range(len(datasources)):
		items.append(datasources[index].getName() + f" ({len(datasources[index].transponderlist.keys())} sats)")
	index = inputChoices(items, "q", "quit")
	if index is None:
		break

	while True:
		print(datasources[index].getStatus())
		items = []
		for action in datasources[index].getCapabilities():
			items.append(action[0])
		action = inputChoices(items)
		if action is None:
			break

		datasources[index].getCapabilities()[action][1]()
		#except:
		#	print sys.exc_info()
		#	print "sorry, could not execute that command"
