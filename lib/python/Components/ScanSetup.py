from config import config
from config import ConfigSubsection
from config import configElement
from config import configSelection
from config import configSequence
from Components.NimManager import nimmanager

def InitScanSetup():
    config.scan = ConfigSubsection()
    config.scan.sat = ConfigSubsection()
    config.scan.cab = ConfigSubsection()
    config.scan.ter = ConfigSubsection()
    config.scan.type = configElement("config.scan.type", configSelection, 0, ("Single transponder", "Single satellite", "Multisat"))
    nimList = [ ]
    for nim in nimmanager.nimList():
        nimList.append(nim[0])
    nimList.append("all")
    config.scan.nims = configElement("config.scan.nims", configSelection, 0, nimList)
    
    # sat
    config.scan.sat.frequency = configElement("config.scan.sat.frequency", configSequence, [12187], (("."), (10000,14000)))
    config.scan.sat.inversion = configElement("config.scan.sat.inversion", configSelection, 0, ("off", "on"))
    config.scan.sat.symbolrate = configElement("config.scan.sat.symbolrate", configSequence, [27500], (("."), (1,30000)))
    config.scan.sat.polarzation = configElement("config.scan.sat.polarzation", configSelection, 0, ("horizontal", "vertical"))
    config.scan.sat.fec = configElement("config.scan.sat.fec", configSelection, 0, ("Auto", "1/2", "2/3", "3/4", "4/5", "5/6", "7/8", "8/9"))

    # cable
    config.scan.cab.frequency = configElement("config.scan.cab.frequency", configSequence, [466], (("."), (10000,14000)))
    config.scan.cab.inversion = configElement("config.scan.cab.inversion", configSelection, 0, ("off", "on"))
    config.scan.cab.modulation = configElement("config.scan.cab.modulation", configSelection, 0, ("Auto", "16-QAM", "32-QAM", "64-QAM", "128-QAM", "256-QAM"))
    config.scan.cab.fec = configElement("config.scan.cab.fec", configSelection, 0, ("Auto", "1/2", "2/3", "3/4", "4/5", "5/6", "7/8", "8/9"))
    config.scan.cab.symbolrate = configElement("config.scan.cab.symbolrate", configSequence, [6900], (("."), (1,30000)))
    
    # terrestial
    config.scan.ter.frequency = configElement("config.scan.ter.frequency", configSequence, [466], (("."), (10000,14000)))
    config.scan.ter.inversion = configElement("config.scan.ter.inversion", configSelection, 0, ("off", "on"))
    config.scan.ter.bandwidth = configElement("config.scan.ter.bandwidth", configSelection, 0, ("Auto", "6 MHz", "7MHz", "8MHz"))
    config.scan.ter.fechigh = configElement("config.scan.ter.fechigh", configSelection, 0, ("Auto", "1/2", "2/3", "3/4", "4/5", "5/6", "7/8", "8/9"))
    config.scan.ter.feclow = configElement("config.scan.ter.feclow", configSelection, 0, ("Auto", "1/2", "2/3", "3/4", "4/5", "5/6", "7/8", "8/9"))
    config.scan.ter.modulation = configElement("config.scan.ter.modulation", configSelection, 0, ("Auto", "16-QAM", "32-QAM", "64-QAM", "128-QAM", "256-QAM"))
    config.scan.ter.transmission = configElement("config.scan.ter.transmission", configSelection, 0, ("Auto", "2K", "8K"))
    config.scan.ter.guard = configElement("config.scan.ter.guard", configSelection, 0, ("Auto", "1/4", "1/8", "1/16", "1/32"))
    config.scan.ter.hierarchy = configElement("config.scan.ter.hierarchy", configSelection, 0, ("Auto", "1", "2", "4"))