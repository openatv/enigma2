# LBPanel -- Linux-Box Panel.   
# Copyright (C) www.linux-box.es
# 
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,  
# but WITHOUT ANY WARRANTY; without even the implied warranty of   
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with GNU gv; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.
# 
# Author: lucifer
#         iqas
#
# Internet: www.linux-box.es
# Based on original source by openpli - About.py

from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.Sources.StaticText import StaticText
from Components.Harddisk import harddiskmanager
from Components.NimManager import nimmanager
from Components.About import about
from Components.ScrollLabel import ScrollLabel
from Components.Button import Button
from Tools.StbHardware import getFPVersion
from enigma import eTimer

class About(Screen):

    def __init__(self, session):
        Screen.__init__(self, session)
        AboutText = _('Hardware: ') + about.getHardwareTypeString() + '\n'
        AboutText += _('Image: ') + about.getImageTypeString() + '\n'
        AboutText += _('Kernel version: ') + about.getKernelVersionString() + '\n'
        EnigmaVersion = 'Enigma: ' + about.getEnigmaVersionString()
        self['EnigmaVersion'] = StaticText(EnigmaVersion)
        AboutText += EnigmaVersion + '\n'
        ImageVersion = _('Last upgrade: ') + about.getImageVersionString()
        self['ImageVersion'] = StaticText(ImageVersion)
        AboutText += ImageVersion + '\n'
        fp_version = getFPVersion()
        if fp_version is None:
            fp_version = ''
        else:
            fp_version = _('Frontprocessor version: %d') % fp_version
            AboutText += fp_version + '\n'
        self['FPVersion'] = StaticText(fp_version)
        self['TunerHeader'] = StaticText(_('Detected NIMs:'))
        AboutText += '\n' + _('Detected NIMs:') + '\n'
        nims = nimmanager.nimList()
        for count in range(len(nims)):
            if count < 4:
                self['Tuner' + str(count)] = StaticText(nims[count])
            else:
                self['Tuner' + str(count)] = StaticText('')
            AboutText += nims[count] + '\n'

        self['HDDHeader'] = StaticText(_('Detected HDD:'))
        AboutText += '\n' + _('Detected HDD:') + '\n'
        hddlist = harddiskmanager.HDDList()
        hddinfo = ''
        if hddlist:
            for count in range(len(hddlist)):
                if hddinfo:
                    hddinfo += '\n'
                hdd = hddlist[count][1]
                if int(hdd.free()) > 1024:
                    hddinfo += '%s\n(%s, %d GB %s)' % (hdd.model(),
                     hdd.capacity(),
                     hdd.free() / 1024,
                     _('free'))
                else:
                    hddinfo += '%s\n(%s, %d MB %s)' % (hdd.model(),
                     hdd.capacity(),
                     hdd.free(),
                     _('free'))

        else:
            hddinfo = _('none')
        self['hddA'] = StaticText(hddinfo)
        AboutText += hddinfo
        self['AboutScrollLabel'] = ScrollLabel(AboutText)
        self['key_green'] = Button(_('Translations'))
        self['key_red'] = Button(_('Latest Commits'))
        self['actions'] = ActionMap(['ColorActions', 'SetupActions', 'DirectionActions'], {'cancel': self.close,
         'ok': self.close,
         #'red': self.showCommits,
         'green': self.showTranslationInfo,
         'up': self['AboutScrollLabel'].pageUp,
         'down': self['AboutScrollLabel'].pageDown})
        return

    def showTranslationInfo(self):
        self.session.open(TranslationInfo)

    def showCommits(self):
        self.session.open(CommitInfo)


class TranslationInfo(Screen):

    def __init__(self, session):
        Screen.__init__(self, session)
        info = _('TRANSLATOR_INFO')
        if info == 'TRANSLATOR_INFO':
            info = '(N/A)'
        infolines = _('').split('\n')
        infomap = {}
        for x in infolines:
            l = x.split(': ')
            if len(l) != 2:
                continue
            type, value = l
            infomap[type] = value

        print infomap
        self['TranslationInfo'] = StaticText(info)
        translator_name = infomap.get('Language-Team', 'none')
        if translator_name == 'none':
            translator_name = infomap.get('Last-Translator', '')
        self['TranslatorName'] = StaticText(translator_name)
        self['actions'] = ActionMap(['SetupActions'], {'cancel': self.close,
         'ok': self.close})


