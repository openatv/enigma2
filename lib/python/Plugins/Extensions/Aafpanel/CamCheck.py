from twisted.internet import threads
from Components.config import config
from enigma import eTimer, eConsoleAppContainer
from os import system, listdir
from datetime import datetime

isBusy = None

def CamCheck():
        global campoller, POLLTIME
        POLLTIME = int(config.plugins.aafpanel_frozencheck.list.getValue()) * 60
        if campoller is None:
            campoller = CamCheckPoller()
        campoller.start()

def CamCheckStop():
    try:
        campoller.stop()
    except:
        print"CamCheck not running, so no need to stop it !! "

class CamCheckPoller:
    def __init__(self):
        self.timer = eTimer()
        self.onClose = []

    def start(self):
        global isBusy
        if isBusy:
            return
        isBusy = True
        if self.camcheck not in self.timer.callback:
            self.timer.callback.append(self.camcheck)
        self.timer.startLongTimer(0)

    def stop(self):
        global isBusy
        if self.camcheck in self.timer.callback:
            self.timer.callback.remove(self.camcheck)
        self.timer.stop()
        isBusy = None

    def camcheck(self):
        global isBusy
        isBusy = True
        threads.deferToThread(self.JobTask)
        self.timer.startLongTimer(POLLTIME)

    def JobTask(self):
        self.doCheck()
        self.timer.startLongTimer(POLLTIME)

    def doCheck(self):
        emuDir = "/etc/"
        self.emuList = []
        self.mlist = []
        self.emuDirlist = []
        self.emuBin = []
        self.emuStart = []
        self.emuDirlist = listdir(emuDir)
        cam_name = config.softcam.actCam.getValue()
        if cam_name == "no CAM active" or cam_name == "":
            print "[CAMSCHECK] No Cam to Check, Exit"
            global isBusy
            isBusy = None
            return

        #// check emu dir for config files
        for x in self.emuDirlist:
            #// if file contains the string "emu" (then this is a emu config file)
            if x.find("emu") > -1:
                self.emuList.append(emuDir + x)
                em = open(emuDir + x)
                #// read the emu config file
                for line in em.readlines():
                    line1 = line
                    #// emuname
                    if line.find("emuname") > -1:
                        line = line.split("=")
                        self.mlist.append(line[1].strip())
                    #// binname
                    line = line1
                    if line.find("binname") > -1:
                        line = line.split("=")
                        self.emuBin.append(line[1].strip())
                    #// startcam
                    line = line1
                    if line.find("startcam") > -1:
                        line = line.split("=")
                        self.emuStart.append(line[1].strip())

        camrunning = 0
        camfound = 0
        tel = 0
        for x in self.mlist:
            if x == cam_name:
                camfound = 1
                cam_bin = self.emuBin[tel]
                p = system('pidof %s' % cam_bin)
                if p != '':
                    if int(p) == 0:
                        actcam = self.mlist[tel]
                        print '[CAMSCHECK] %s: CAM is Running, active cam: %s' %(datetime.now(), actcam)
                        camrunning = 1
                    break
            else:
                tel +=1
        try:
        #// CAM IS NOT RUNNING SO START
            if camrunning == 0:
                #// AND CAM IN LIST
                if camfound == 1:
                    start = self.emuStart[tel]
                    print "[CAMSCHECK] no CAM active, starting %s" % start
                    system("echo %s Started at: %s >> /tmp/camcheck.txt" % (start, datetime.now()))
                    self.container = eConsoleAppContainer()
                    self.container.execute(start)
        except:
            print "[CAMSCHECK] Error, can not start Cam"

        global isBusy
        isBusy = None

campoller = None