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
# config.plugins.icetv.member.email_address = ConfigText(visible_width=50, fixed_size=False)
config.plugins.icetv.member.email_address = ConfigText(show_help=False)
config.plugins.icetv.member.token = ConfigText()
config.plugins.icetv.member.id = ConfigNumber()
config.plugins.icetv.member.region_id = ConfigNumber()

# config.plugins.icetv.meber.password = ConfigPassword(visible_width=50, fixed_size=False, censor="●")
config.plugins.icetv.member.password = NoSave(ConfigPassword(censor="●", show_help=False))

config.plugins.icetv.device = ConfigSubsection()
config.plugins.icetv.device.label = ConfigText(default="%s %s" % (getMachineBrand(), getMachineName()), show_help=False)
config.plugins.icetv.device.id = ConfigNumber()
config.plugins.icetv.device.type_id = ConfigNumber(default=22)

config.plugins.icetv.last_update_time = ConfigNumber()
config.plugins.icetv.enable_epg = ConfigYesNo(default=False)
config.plugins.icetv.configured = ConfigYesNo(default=False)

checktimes = [
    ("%d" % int(2 * 60      ), "2 minutes" ),
    ("%d" % int(5 * 60      ), "5 minutes" ),
    ("%d" % int(10 * 60     ), "10 minutes"),
    ("%d" % int(15 * 60     ), "15 minutes"),
    ("%d" % int(30 * 60     ), "30 minutes"),
    ("%d" % int(60 * 60     ), "1 hour"    ),
    ("%d" % int(2 * 60 * 60 ), "2 hours"   ),
    ("%d" % int(3 * 60 * 60 ), "3 hours"   ),
    ("%d" % int(4 * 60 * 60 ), "4 hours"   ),
    ("%d" % int(5 * 60 * 60 ), "5 hours"   ),
    ("%d" % int(6 * 60 * 60 ), "6 hours"   ),
    ("%d" % int(7 * 60 * 60 ), "7 hours"   ),
    ("%d" % int(8 * 60 * 60 ), "8 hours"   ),
    ("%d" % int(12 * 60 * 60), "12 hours"  ),
    ("%d" % int(24 * 60 * 60), "24 hours"  ),
]

config.plugins.icetv.refresh_interval = ConfigSelection(default=checktimes[3][0], choices=checktimes)

def saveConfigFile():
    config.plugins.icetv.save()
    configfile.save()

def enableIceTV():
    config.epg.eit.value = False
    config.epg.save()
    config.usage.show_eit_nownext.value = False
    config.usage.show_eit_nownext.save()
    config.plugins.icetv.enable_epg.value = True
    config.plugins.icetv.last_update_time.value = 0
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
    config.epg.eit.value = True
    config.epg.save()
    config.usage.show_eit_nownext.value = True
    config.usage.show_eit_nownext.save()
    config.plugins.icetv.enable_epg.value = False
    config.plugins.icetv.last_update_time.value = 0
    saveConfigFile()
