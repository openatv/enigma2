# kate: replace-tabs on; indent-width 4; remove-trailing-spaces all; show-tabs on; newline-at-eof on;
# -*- coding:utf-8 -*-

'''
Copyright (C) 2014 Peter Urbanec
All Right Reserved
License: Proprietary / Commercial - contact enigma.licensing (at) urbanec.net
'''

from enigma import eEPGCache
from boxbranding import getMachineBrand, getMachineName
from Components.config import config, ConfigSubsection, ConfigNumber, ConfigText, \
    ConfigPassword, ConfigSelection, NoSave, configfile, ConfigYesNo


config.plugins.icetv = ConfigSubsection()
config.plugins.icetv.member = ConfigSubsection()
config.plugins.icetv.member.email_address = ConfigText(show_help=False, fixed_size=False)
config.plugins.icetv.member.token = ConfigText()
config.plugins.icetv.member.id = ConfigNumber()
config.plugins.icetv.member.region_id = ConfigNumber()

config.plugins.icetv.member.password = NoSave(ConfigPassword(censor="●", show_help=False, fixed_size=False))

config.plugins.icetv.device = ConfigSubsection()
config.plugins.icetv.device.label = ConfigText(default="%s %s" % (getMachineBrand(), getMachineName()), show_help=False)
config.plugins.icetv.device.id = ConfigNumber()
config.plugins.icetv.device.type_id = ConfigNumber(default=22)

config.plugins.icetv.last_update_time = ConfigNumber()
if config.plugins.icetv.last_update_time.value != 0:
    config.plugins.icetv.last_update_time.value = 0
    config.plugins.icetv.last_update_time.save()
    configfile.save()
config.plugins.icetv.last_update_time.disableSave()

config.plugins.icetv.enable_epg = ConfigYesNo(default=False)
config.plugins.icetv.configured = ConfigYesNo(default=False)

minute = 60
hour = minute * 60

checktimes = [
    # ("%d" % int(minute * 2), "2 minutes"),
    ("%d" % int(minute * 5), "5 minutes"),
    ("%d" % int(minute * 10), "10 minutes"),
    ("%d" % int(minute * 15), "15 minutes"),
    ("%d" % int(minute * 30), "30 minutes"),
    ("%d" % int(hour), "1 hour"),
    ("%d" % int(hour * 2), "2 hours"),
    ("%d" % int(hour * 3), "3 hours"),
    ("%d" % int(hour * 4), "4 hours"),
    ("%d" % int(hour * 5), "5 hours"),
    ("%d" % int(hour * 6), "6 hours"),
    ("%d" % int(hour * 7), "7 hours"),
    ("%d" % int(hour * 8), "8 hours"),
    ("%d" % int(hour * 12), "12 hours"),
    ("%d" % int(hour * 24), "24 hours"),
]

config.plugins.icetv.refresh_interval = ConfigSelection(default="%d" % int(minute * 15), choices=checktimes)

def saveConfigFile():
    config.plugins.icetv.save()
    configfile.save()

def enableIceTV():
    setIceTVDefaults()
    epgcache = eEPGCache.getInstance()
    epgcache.setEpgSources(0)
    epgcache.clear()
    epgcache.save()
    saveConfigFile()

def disableIceTV():
    epgcache = eEPGCache.getInstance()
    epgcache.setEpgSources(0)
    epgcache.clear()
    epgcache.save()
    epgcache.setEpgSources(eEPGCache.NOWNEXT | eEPGCache.SCHEDULE | eEPGCache.SCHEDULE_OTHER)
    restoreDefaults()
    saveConfigFile()

def setIceTVDefaults():
    config.plugins.icetv.enable_epg.value = True
    config.plugins.icetv.last_update_time.value = 0
    config.epg.eit.value = False
    config.epg.save()
    config.usage.show_eit_nownext.value = False
    config.usage.show_eit_nownext.save()
    if config.recording.margin_before.value == config.recording.margin_before.default:
        config.recording.margin_before.value = 2
        config.recording.margin_before.save()
    if config.recording.margin_after.value == config.recording.margin_after.default:
        config.recording.margin_after.value = 20
        config.recording.margin_after.save()
    if config.movielist.fontsize.value == config.movielist.fontsize.default:
        config.movielist.fontsize.value = 7
        config.movielist.fontsize.save()
    if config.movielist.itemsperpage.value == config.movielist.itemsperpage.default:
        config.movielist.itemsperpage.value = 15
        config.movielist.itemsperpage.save()

def restoreDefaults():
    if config.recording.margin_before.value == 2:
        config.recording.margin_before.value = config.recording.margin_before.default
        config.recording.margin_before.save()
    if config.recording.margin_after.value == 20:
        config.recording.margin_after.value = config.recording.margin_after.default
        config.recording.margin_after.save()
    if config.movielist.fontsize.value == 7:
        config.movielist.fontsize.value = config.movielist.fontsize.default
        config.movielist.fontsize.save()
    if config.movielist.itemsperpage.value == 15:
        config.movielist.itemsperpage.value = config.movielist.itemsperpage.default
        config.movielist.itemsperpage.save()
    config.usage.show_eit_nownext.value = True
    config.usage.show_eit_nownext.save()
    config.epg.eit.value = True
    config.epg.save()
    config.plugins.icetv.enable_epg.value = False
    config.plugins.icetv.last_update_time.value = 0
