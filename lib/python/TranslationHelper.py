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

# fallback timer
translate = _("Unexpected error while retrieving fallback tuner's timer information")
translate = _("Fallback API did not return a valid result.")
translate = _("Error while retrieving fallback timer information\n%s")
translate = _("Fallback tuner setup")
translate = _("Same as stream")
translate = _("Enter IP address")
translate = _("Import from remote receiver URL")
translate = _("Import channels and/or EPG from remote receiver URL when receiver is booted")
translate = _("Enable import timer from fallback tuner")
translate = _("When enabled the timer from the fallback tuner is imported")
translate = _("Select the timer from the fallback tuner by default")
translate = _("When enabled the timer from the fallback tuner is the default timer")
translate = _("Fallback remote receiver")
translate = _("Destination of fallback remote receiver")
translate = _("Fallback remote receiver IP")
translate = _("IP of fallback remote receiver")
translate = _("Fallback remote receiver Port")
translate = _("Port of fallback remote receiver")
translate = _("URL of fallback remote receiver")
translate = _("Import remote receiver URL")
translate = _("Also import at reboot/restart enigma2")
translate = _("Import channels and/or EPG from remote receiver URL when receiver or enigma2 is restarted")
translate = _("Also import when box is leaving standby")
translate = _("Import channels and/or EPG from remote receiver URL also when the receiver is getting out of standby")
translate = _("Also import from the extension menu")
translate = _("Make it possible to manually initiate the channels import and/or EPG via the extension menu")
translate = _("Show notification when import channels was successful")
translate = _("Show notification when import channels and/or EPG from remote receiver URL is completed")
translate = _("Show notification when import channels was not successful")
translate = _("Show notification when import channels and/or EPG from remote receiver URL did not complete")
translate = _("Customize OpenWebIF settings for fallback tuner")
translate = _("When enabled you can customize the OpenWebIf settings for the fallback tuner")
translate = _("User ID")
translate = _("Set the User ID of the OpenWebif from your fallback tuner")
translate = _("Set the password of the OpenWebif from your fallback tuner")
translate = _("Set the port of the OpenWebif from your fallback tuner")
translate = _("Alternative URLs for DVB-T/C or ATSC")
translate = _("Set alternative fallback tuners for DVB-T/C or ATSC")
translate = _("Fallback remote receiver for DVB-T")
translate = _("Destination of fallback remote receiver for DVB-T")
translate = _("Fallback remote receiver for DVB-C")
translate = _("Destination of fallback remote receiver for DVB-C")
translate = _("Fallback remote receiver for ATSC")
translate = _("Destination of fallback remote receiver for ATSC")
