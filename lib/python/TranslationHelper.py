# This file is used to define strings that must be translated but, due
# to the nature of the code, can't be translated where the text is
# defined. A particular example of this issue is when code needs to
# pass variables into the ngettext() function. Strings used in the
# ngettext() function *MUST NOT* be translated as ngettext() will do
# the translation itself. If the string is fed in via a translated
# variable then the translation will be done *TWICE* and this can
# lead to unexpected results.
#
# The solution to this issue is to define any strings that will
# ultimately require translation here where the language scanner
# will see and harvest the strings and submit them for translation
# but this code itself will NEVER be used by, or included in, any
# Enigma2 image.
#
# This file will allow code like this to work and the strings be
# correctly translated:
#
# delay = 32
# displayAnswer(delay, ("%d Second", "%d Seconds"))
#
# def displayAnswer(value, units):
# 	print(ngettext(units[0], units[1], value) % value)
#
translate = ngettext("%d Second", "%d Seconds", 1) % 1
translate = ngettext("%d Minute", "%d Minutes", 1) % 1
translate = ngettext("%d Min", "%d Mins", 1) % 1
translate = ngettext("%d Hour", "%d Hours", 1) % 1
translate = ngettext("%d Day", "%d Days", 1) % 1
translate = ngettext("%d Week", "%d Weeks", 1) % 1
translate = ngettext("%d Month", "%d Months", 1) % 1
translate = ngettext("%d Year", "%d Years", 1) % 1
translate = ngettext("%d Digit", "%d Digits", 1) % 1
translate = ngettext("%d Event", "%d Events", 1) % 1
translate = ngettext("%d Pixel", "%d Pixels", 1) % 1
translate = ngettext("%d Pixel wide", "%d Pixels wide", 1) % 1

# f-string harvester workaround
# version 0.23 of xgetext should fix this issue
translate = _("Do you want to replace:")
translate = _("Please wait while the feeds are reset (cleared and reloaded)...")
translate = _("Current Status:")
translate = _("PPanel")
translate = _("Shellscript")
translate = _("Hotkey Settings")
translate = _("Panic to")
translate = _("Zap to")
translate = _("ButtonSetup")
translate = _("Hotkey")
translate = _("Are you sure to remove this entry?")
translate = _("N/A")
translate = _("Unknown")
translate = _("Network storage on")
translate = _("Client")
translate = _("Reception Settings")

translate = _("Do you want to remove:")
translate = _("Do you want to install:")
translate = _("Do you want to update:")
translate = _("Do you want to replace:")
translate = _("Reception Settings")

translate = _("Configuring")
translate = _("Downloading")
translate = _("Installing")
translate = _("User defined")
translate = _("ClientIP")
translate = _("Transcode")
translate = _("Channel")
translate = _("(TV)")
translate = _("(Radio)")
translate = _("(PiP)")
translate = _("Tuner")
translate = _("Current")

translate = _("No log files found so debug logs are unavailable!")

translate = _("Locale")
translate = _("Language")

translate = _("Preferred tuner DVB-S")
translate = _("Preferred tuner DVB-S for recordings")
translate = _("Preferred tuner DVB-T")
translate = _("Preferred tuner DVB-T for recordings")
translate = _("Preferred tuner DVB-C")
translate = _("Preferred tuner DVB-C for recordings")
translate = _("When enabled, this setting has more weight than 'Preferred tuner'.")
translate = _("When enabled, this setting has more weight than 'Preferred tuner for recordings'.")
translate = _("Preferred tuner ATSC")
translate = _("Preferred tuner ATSC for recordings")

translate = _("Miscellaneous languages")
translate = _("Enable new GStreamer playback")
translate = _("If enabled, the new GStreamer playback engine will be used.")


translate = _("Back USB 3.0")
translate = _("Back USB")
translate = _("Back USB-C")
translate = _("Back, inner USB")
translate = _("Back, left USB")
translate = _("Back, lower USB")
translate = _("Back, outer USB")
translate = _("Back, right USB")
translate = _("Back, upper USB")
translate = _("Front USB 3.0")
translate = _("Front USB")
translate = _("Internal USB")
translate = _("Left USB")
translate = _("Left, back USB")
translate = _("Left, front USB")
translate = _("Lower USB")
translate = _("Micro SD")
translate = _("Right USB")
translate = _("Right, back USB")
translate = _("Right, front USB")
translate = _("SATA BACK")
translate = _("SATA FRONT")
translate = _("SATA")
translate = _("SD")
translate = _("USB 2.0 (Back, inner)")
translate = _("USB 3.0 (Back, outer)")
translate = _("Upper USB")
translate = _("eMMC")
translate = _("eSATA")
