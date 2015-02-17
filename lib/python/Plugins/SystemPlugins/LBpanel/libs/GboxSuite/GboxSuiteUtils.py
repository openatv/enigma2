# 2014.10.12 15:52:04 CEST
import os
from Imports import *
import Imports

def fillProviderTable():
    if os.path.isfile(config.plugins.gs.configDir.value + '/ident.info') == True:
        fp = open(config.plugins.gs.configDir.value + '/ident.info', 'r')
        while 1:
            currentLine = fp.readline()
            if currentLine == '':
                break
            Imports.providerTable[currentLine[:8]] = currentLine[9:(len(currentLine) - 1)]

        fp.close()



def getProviderName(provId):
    if Imports.providerTable.has_key(provId):
        return Imports.providerTable[provId]
    else:
        return provId



def readTextFile(args):
    try:
        fp = file(args[0], 'r')
        lines = fp.readlines()
        fp.close()
        output = ''
        for x in lines:
            output += x

    except IOError:
        output = args[1]
    return output

