from twisted.internet import threads
from Components.config import config
from enigma import eTimer, eConsoleAppContainer
from os import system, listdir, path, popen
from datetime import datetime

isBusy = None
CFG = "/usr/keys/CCcam.cfg"

def CamCheck():
    global campoller, POLLTIME
    POLLTIME = int(config.plugins.infopanel_frozencheck.list.value) * 60
    if campoller is None:
        campoller = CamCheckPoller()
    campoller.start()

def CamCheckStop():
    try:
        campoller.stop()
    except:
        print"CamCheck not running, so no need to stop it !! "

def confPath():
	search_dirs = [ "/usr", "/var", "/etc" ]
	sdirs = " ".join(search_dirs)
	cmd = 'find %s -name "CCcam.cfg" | head -n 1' % sdirs
	res = popen(cmd).read()
	if res == "":
		return None
	else:
		return res.replace("\n", "")

def getConfigValue(l):
	list = l.split(":")
	ret = ""

	if len(list) > 1:
		ret = (list[1]).replace("\n", "").replace("\r", "")
		if ret.__contains__("#"):
			idx = ret.index("#")
			ret = ret[:idx]
		while ret.startswith(" "):
			ret = ret[1:]
		while ret.endswith(" "):
			ret = ret[:-1]

	return ret

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
        self.timer.startLongTimer(60)

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


    def FrozenCCcam(self, cam):
        if not cam.upper().startswith('CCCAM'):
            print "[CAMSCHECK] exit Frozen CCcam check, softcam is not CCcam"
            return False
        if path.exists(CFG):
            self.cfg = CFG
        else:
            self.cfg = confPath()
        if not self.cfg:
            print "[CAMSCHECK] exit Frozen CCcam check, CCcam.cfg not found"
            return False
        self.readConfig()
        ff = system('wget -s ' + self.url + ' 2>/dev/null')
        if ff > 0:
            print "[CAMSCHECK] Frozen CCcam detected"
            return True
        else:
            print "[CAMSCHECK] CCcam OK"
            return False

    def readConfig(self):
        self.url = "http://127.0.0.1:16001"
        username = None
        password = None

        try:
            f = open(self.cfg, 'r')
            for l in f:
                if l.startswith('WEBINFO LISTEN PORT :'):
                    port = getConfigValue(l)
                    if port != "":
                        self.url = self.url.replace('16001', port)
                elif l.startswith('WEBINFO USERNAME :'):
                    username = getConfigValue(l)
                elif l.startswith('WEBINFO PASSWORD :'):
                    password = getConfigValue(l)

            f.close()
        except:
            pass

        if (username is not None) and (password is not None) and (username != "") and (password != ""):
            self.url = self.url.replace('http://', ("http://%s:%s@" % (username, password)))

    def doCheck(self):
        emuDir = "/etc/"
        self.emuList = []
        self.mlist = []
        self.emuDirlist = []
        self.emuBin = []
        self.emuStart = []
        self.emuStop = []
        self.emuDirlist = listdir(emuDir)
        cam_name = config.softcam.actCam.value
        cam_name2 = config.softcam.actCam2.value
        if (cam_name == "no CAM 1 active" or cam_name == "") and (cam_name2 == "no CAM 2 active" or cam_name2 == ""):
            print "[CAMSCHECK] No Cam to Check, Exit"
            global isBusy
            isBusy = None
            return


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
                    #// stopcam
                    line = line1
                    if line.find("stopcam") > -1:
                        line = line.split("=")
                        self.emuStop.append(line[1].strip())

                em.close()

        camrunning = 0
        camfound = 0
        camfrozen = 0
        indexcam = -1
        camrunning2 = 0
        camfound2 = 0
        camfrozen2 = 0
        indexcam2 = -1
        tel = 0

        for x in self.mlist:
            #print '[CAMSTARTER] searching active cam: ' + x
            if x == cam_name:
                camfound = 1
                indexcam = tel
                cam_bin = self.emuBin[tel]
                p = system('pidof %s' % cam_bin)
                if p != '':
                    if int(p) == 0:
                        actcam = self.mlist[tel]
                        print datetime.now()
                        print '[CAMSTARTER] CAM 1 is Running, active cam 1: ' + actcam
                        camrunning = 1
                        if self.FrozenCCcam(actcam):
                            camfrozen = 1
                tel +=1
            elif x == cam_name2:
                camfound2 = 1
                indexcam2 = tel
                cam_bin = self.emuBin[tel]
                p = system('pidof %s' % cam_bin)
                if p != '':
                    if int(p) == 0:
                        actcam = self.mlist[tel]
                        print datetime.now()
                        print '[CAMSTARTER] CAM 2 is Running, active cam 2: ' + actcam
                        camrunning2 = 1
                        if self.FrozenCCcam(actcam):
                            camfrozen2 = 1
                tel +=1
            else:
                tel +=1
        try:

            #// CAM IS NOT RUNNING SO START
            if camrunning == 0 or camfrozen == 1 or (camfound2 == 1 and camrunning2 == 0 or camfrozen2 == 1):
                #// AND CAM IN LIST
                if camfound == 1:
                    stop = self.emuStop[indexcam]
                    print "[CAMSTARTER] CAM 1 not running, stop " + stop
                    self.container = eConsoleAppContainer()
                    self.container.execute(stop)

                    start = self.emuStart[indexcam]
                    print "[CAMSTARTER] no CAM 1 active, starting " + start
                    system("echo %s Started cam 1 at: %s >> /tmp/camcheck.txt" % (start, datetime.now()))
                    self.container = eConsoleAppContainer()
                    self.container.execute(start)
                    if camrunning2 == 0 or camfrozen2 == 1:
                        #// AND CAM IN LIST
                        if camfound2 == 1:
                            stop = self.emuStop[indexcam2]
                            print "[CAMSTARTER] CAM 2 not running, stop " + stop
                            self.container = eConsoleAppContainer()
                            self.container.execute(stop)
                            
                            import time
                            time.sleep (int(config.softcam.waittime.value))
                            start = self.emuStart[indexcam2]
                            print "[CAMSTARTER] no CAM 2 active, starting " + start
                            system("echo %s Started cam 2 at: %s >> /tmp/camcheck.txt" % (start, datetime.now()))
                            self.container = eConsoleAppContainer()
                            self.container.execute(start)
            else:
                if camfound == 0:
                    print "[CAMSTARTER] No Cam found to start"

        except:
            print "[CAMSCHECK] Error, can not start Cam"

        global isBusy
        isBusy = None

campoller = None