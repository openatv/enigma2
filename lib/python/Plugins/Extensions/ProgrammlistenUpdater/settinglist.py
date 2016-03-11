from enigma import eTimer
import re, glob, shutil, os, urllib2, urllib, time, sys
from Screens.Screen import Screen
from Components.config import ConfigSubsection, ConfigYesNo, ConfigText, config, configfile
from Screens.MessageBox import MessageBox
from downloader import DownloadSetting, ConverDate, ConverDateBack
from enigma import *

try:
    import zipfile
except:
    pass

Directory = os.path.dirname(sys.modules[__name__].__file__)

def InstallSettings(name, link, date):

    def DownloadSetting(link):
        req = urllib2.Request(link)
        req.add_header('User-Agent', 'VAS')
        response = urllib2.urlopen(req)
        newlink = response.read()
        response.close()
        Setting = open(Directory + '/Settings/tmp/listE2.zip', 'w')
        Setting.write(newlink)
        Setting.close()
        if os.path.exists(Directory + '/Settings/tmp/listE2.zip'):
            os.system('mkdir ' + Directory + '/Settings/tmp/listE2_unzip')
            try:
                os.system('unzip ' + Directory + '/Settings/tmp/listE2.zip -d  ' + Directory + '/Settings/tmp/listE2_unzip')
            except:
                print "ERROR unzip listE2.zip"
            if not os.path.exists(Directory + '/Settings/tmp/setting'):
                os.system('mkdir ' + Directory + '/Settings/tmp/setting')
                try:
                    os.system('unzip ' + Directory + '/Settings/tmp/listE2_unzip/*.zip -d  ' + Directory + '/Settings/tmp/setting')
                except:
                    print "ERROR unzip %s.zip", name
        return False

    Status = True
    
    # remove old download if exists
    if os.path.exists(Directory + '/Settings/tmp'):
        os.system('rm -rf ' + Directory + '/Settings/tmp')

    # create a new empty tmp folder
    if not os.path.exists(Directory + '/Settings/tmp'):
        os.system('mkdir -p ' + Directory + '/Settings/tmp')

    # copy current settings
    if not os.path.exists(Directory + '/Settings/enigma2'):
        os.system('mkdir -p ' + Directory + '/Settings/enigma2')

    now = time.time()
    ttime = time.localtime(now)
    tt = str(ttime[0])[2:] + str('{0:02d}'.format(ttime[1])) + str('{0:02d}'.format(ttime[2])) + '_' + str('{0:02d}'.format(ttime[3])) + str('{0:02d}'.format(ttime[4])) + str('{0:02d}'.format(ttime[5]))
    os.system("tar -czvf " + Directory + "/Settings/enigma2/" + tt + "_enigma2settingsbackup.tar.gz" + " -C / /etc/enigma2/*.tv /etc/enigma2/*.radio /etc/enigma2/lamedb")

    def getRemoveList():
        RemoveList = []
        inhaltfile = Directory + '/Settings/tmp/setting/inhalt.lst'
        if os.path.isfile(inhaltfile):
            with open(inhaltfile, 'r') as f:
                data = f.read().decode("utf-8-sig").encode("utf-8")
            RemoveList = data.splitlines()

        return RemoveList

    if not DownloadSetting(link):
        RemoveList = getRemoveList()
        if RemoveList:
            for file in RemoveList:
               nFile = '/etc/enigma2/'+ file
               if os.path.isfile(nFile) and not nFile == '/etc/enigma2/lamedb':
                    os.system('rm -rf %s' %nFile)

        os.system('rm -rf /etc/enigma2/*.del')
        os.system('rm -rf /etc/enigma2/lamedb')

        # copy new settings
        os.system('cp -rf ' + Directory + '/Settings/tmp/setting/*.tv  /etc/enigma2/')
        os.system('cp -rf ' + Directory + '/Settings/tmp/setting/*.radio  /etc/enigma2/')
        os.system('cp -rf ' + Directory + '/Settings/tmp/setting/lamedb  /etc/enigma2/')

        # remove /tmp folder
        if os.path.exists(Directory + '/Settings/tmp'):
            os.system('rm -rf ' + Directory + '/Settings/tmp')
        
    else:
        Status = False

    return Status


class CheckTimer:

    def __init__(self, session = None):
        self.session = session
        self.UpdateTimer = eTimer()
        self.UpdateTimer.callback.append(self.startTimerSetting)

    def gotSession(self, session, url):
        self.session = session
        self.url = url
        if config.pud.autocheck.value:
            self.TimerSetting(True)

    def startDownload(self, name, link, date):
        if InstallSettings(name, link, date):
            # save new name/date
            config.pud.autocheck.value = True
            config.pud.lastdate.value = date
            config.pud.satname.value = name
            config.pud.save()
            configfile.save()
            eDVBDB.getInstance().reloadServicelist()
            eDVBDB.getInstance().reloadBouquets()
            self.session.open(MessageBox, _('New Setting DXAndy ') + name + _(' of ') + date + _(' updated'), MessageBox.TYPE_INFO, timeout=15)
        else:
            self.session.open(MessageBox, _('Error Download Setting'), MessageBox.TYPE_ERROR, timeout=15)

    def StopTimer(self):
        try:
            self.UpdateTimer.stop()
        except:
            pass

    def TimerSetting(self, Auto=False):
  
        try:
            self.StopTimer()
        except:
            pass

        now = time.time()
        ttime = now + 28800 # Check each 8 hours for new version
        delta1 = int(ttime - now)
        
        if Auto:
            #Do Check at bootup after 2 min
            self.UpdateTimer.start(120000, True)
        else:
            self.UpdateTimer.start(1000 * delta1, True)

    def CBupdate(self, req):
        if req:
            config.pud.update_question.value = True
            self.startDownload(self.name, self.link, ConverDate(self.date))
        else:
            config.pud.update_question.value = False
        config.pud.save()
        
    def startTimerSetting(self):

        def OnDsl():
            try:
                urllib2.urlopen('http://www.google.de', None, 3)
                return (True and config.pud.showmessage.value)
            except:
                return False

            return

        if OnDsl():
            print "Programmlisten-Updater: CHECK FOR UPDATE"
            sList = DownloadSetting(self.url)
            for date, name, link in sList:
                if name == config.pud.satname.value:
                    lastdate = config.pud.lastdate.value
                    if date > ConverDateBack(lastdate):
                        self.date = date
                        self.name = name
                        self.link = link
                        yesno_default = config.pud.update_question.value
                        print "Programmlisten-Updater: NEW SETTINGS DXANDY"
                        if config.pud.just_update.value:
                            # Update without information
                            self.startDownload(self.name, self.link, ConverDate(self.date))
                        else:
                            # Auto update with confrimation
                            self.session.openWithCallback(self.CBupdate, MessageBox, _('New Setting DXAndy ') + name + _(' of ') + ConverDate(date) + _(' available !!' + "\n\n" + "Do you want to install the new settingslist?"), MessageBox.TYPE_YESNO, default=yesno_default, timeout=60)
                    else:
                        print "Programmlisten-Updater: NO NEW UPDATE AVAILBLE"
                    break
 
        self.TimerSetting()