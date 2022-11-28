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
translate = ngettext("%d Hour", "%d Hours",1) % 1
translate = ngettext("%d Day", "%d Days",1) % 1
translate = ngettext("%d Week", "%d Weeks",1) % 1
translate = ngettext("%d Month", "%d Months",1) % 1
translate = ngettext("%d Year", "%d Years",1) % 1
translate = ngettext("%d Digit", "%d Digits", 1) % 1
translate = ngettext("%d Event", "%d Events", 1) % 1
translate = ngettext("%d Pixel", "%d Pixels", 1) % 1
translate = ngettext("%d Pixel wide", "%d Pixels wide", 1) % 1
