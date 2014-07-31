# kate: replace-tabs on; indent-width 4; remove-trailing-spaces all; show-tabs on; newline-at-eof on;
# -*- coding:utf-8 -*-

'''
Copyright (C) 2014 Peter Urbanec
All Right Reserved
License: Proprietary / Commercial - contact enigma.licensing (at) urbanec.net
'''

from boxbranding import getMachineBrand, getMachineName
from Components.config import config, ConfigSubsection, ConfigNumber, ConfigText, \
    ConfigPassword, ConfigSelection, NoSave, configfile


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

checktimes = {
    "2 minutes": 2 * 60,
    "5 minutes": 5 * 60,
    "10 minutes": 10 * 60,
    "15 minutes": 15 * 60,
    "30 minutes": 30 * 60,
    "1 hour": 60 * 60,
    "2 hours": 2 * 60 * 60,
    "3 hours": 3 * 60 * 60,
    "4 hours": 4 * 60 * 60,
    "5 hours": 5 * 60 * 60,
    "6 hours": 6 * 60 * 60,
    "7 hours": 7 * 60 * 60,
    "8 hours": 8 * 60 * 60,
    "12 hours": 12 * 60 * 60,
    "24 hours": 24 * 60 * 60,
}

config.plugins.icetv.refresh_interval = ConfigSelection(default="15 minutes", choices=checktimes)

def saveConfigFile():
    config.plugins.icetv.save()
    configfile.save()
