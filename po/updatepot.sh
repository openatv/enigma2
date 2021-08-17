#!/bin/bash
# Script to generate pot file outside of the normal build process
#  
# Pre-requisite:
# The following tools must be installed on your system and accessible from path
# gawk, find, xgettext, gsed, python, msguniq, msgmerge, msgattrib, msgfmt, msginit
#
# Run this script from within the po folder.
#
# Author: Pr2
# Version: 1.2

printf "Creating temporary file enigma2-py.pot\n"
find -s -X .. -name "*.py" -exec xgettext --no-wrap -L Python --from-code=UTF-8 -kpgettext:1c,2 --add-comments="TRANSLATORS:" -d enigma2 -s -o enigma2-py.pot {} \+
gsed --in-place enigma2-py.pot --expression=s/CHARSET/UTF-8/
printf "Creating temporary file enigma2-xml.pot\n"
find -s -X .. -name "*.xml" -exec python xml2po.py {} \+ > enigma2-xml.pot
printf "Merging pot files to create: enigma2.pot\n"
cat enigma2-py.pot enigma2-xml.pot | msguniq --no-wrap --no-location -o enigma2.pot -
rm enigma2-py.pot enigma2-xml.pot
printf "pot update from script finished!\n"

