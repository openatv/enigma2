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
translate = _("%d Second")
translate = _("%d Seconds")
