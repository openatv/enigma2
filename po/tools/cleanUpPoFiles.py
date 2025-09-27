#!/usr/local/bin/python


"""Cleans up PO translation files

   This script will iterate through all .po files and unset ( "" ) msgstr
   translation entries which match exactly their msgid value.
   The 'fuzzy' flag for each (if it exists) will be removed in such cases.
   Polib will be required, see the docs at
   https://polib.readthedocs.io/en/latest/installation.html#installation

   This script is functional over efficient!

   Known issues / notes:
   - normalised entries (those found in other translation files)
     are currently appended for ease of diffing
   - comments in source code files should probably be ignored
   - FIXED: color hex values (eg. "#25062748") should be ignored
   - printed strings (print "we should never come here!")
     should probably be ignored
   - entries not found in source code aren't marked obsolete/removed
     (these may be from plugin code outside of the enigma2 sources)
   - mismatched fuzzy entries with python variable counts aren't fixed
   - xml item text/descriptions aren't differentiated (via msgctxt etc.)
   - FIXED: msgid " " should be marked DO NOT TRANSLATE
"""

__author__ = "Web Dev Ben"
__credits__ = ["Web Dev Ben"]
__license__ = "GPL & BeeWare (do something to help your local bees!)"
__version__ = "1.0.0"
__maintainer__ = "Web Dev Ben"
__email__ = "9741693+wedebe@users.noreply.github.com"

from datetime import timedelta
from glob import glob
from os import stat, system, walk
from os.path import abspath, basename, dirname, getsize, join, sep
from time import time
import polib
import fnmatch
import re
import mmap
import sys

scriptPath = dirname(abspath(__file__)) + sep

poFiles = scriptPath + "../*.po*"
codeBasePath = scriptPath + "../.."

prefs = {
  'newFileExt': "",  # useful to avoid overwriting original file(s)
  'stripUnchangedMsgstrs': True,
  'removeMatchingObsoletes': False,
  'searchCodebaseForOccurrences': False,  # Makefile will take care of this by default
  'normalisePoFiles': True,
  'outputFinalStats': True,
  'processMaxEntries': 0,  # useful for testing; 0 will process all entries
  'include': ["*.xml", "*.py"],  # for files only
  'exclude': [r"*/\.*", codeBasePath + "/po/*"]  # for dirs and files
}

# transform glob patterns to regular expressions
includes = r'|'.join([fnmatch.translate(x) for x in prefs['include']])
excludes = r'|'.join([fnmatch.translate(x) for x in prefs['exclude']]) or r'$.'

occurrencesCache = {}

poStats = {}
poStats['columnHeadings'] = [
  "Entries",
  "Fuzzy",
  "Unchanged",
  "Translated",
  "Ratio",
  "-",
]  # "Removed #~"]
poStats['data'] = []
poStats['rowTitles'] = []

prgChars = [
 "#   # # # ",
 "# #   # # ",
 "# # #   # ",
 "# # # #   ",
 "# # # # # ",
 "  # # # # ",
]
idx = 0


def stripUnchangedMsgstrs(poEntry):
  if prefs['stripUnchangedMsgstrs']:
    percentCleared = 0
    if len(poEntry.msgid_plural) > 0:
      try:
        # this script version will only handle an entry with one singular
        # (msgstr_plural[0]) and one plural msgstr_plural[1] entry
        if (poEntry.msgid == poEntry.msgstr_plural[0]):
          poEntry.msgstr_plural[0] = ""
          percentCleared = 50
        if (poEntry.msgid_plural == poEntry.msgstr_plural[1]):
          poEntry.msgstr_plural[1] = ""
          percentCleared += 50
      except Exception:
        pass  # let's just pretend that didn't happen >_<
    elif poEntry.msgid == poEntry.msgstr:
      poEntry.msgstr = ""
      percentCleared = 100
    # remove leftover fuzzy flag
    if ("fuzzy" in poEntry.flags) and (percentCleared == 100):
      poEntry.flags = [f for f in poEntry.flags if f != 'fuzzy']
    percentCleared = None


def removeMatchingObsolete(poFile, poEntry):
  if prefs['removeMatchingObsoletes'] and not poEntry.obsolete:
    for obsoleteEntry in [o for o in poFile.obsolete_entries() if poEntry.msgid == o.msgid]:
      poFile.remove(obsoleteEntry)
      # numObsoletesRemoved = numObsoletesRemoved + 1


def getIncludedExcludedPaths(root, dirs, files):
  # exclude dirs
  # dirs[:] = [os.path.join(root, d) for d in dirs]
  # dirs[:] = [d for d in dirs if not re.match(excludes, d)]
  # exclude/include files
  files = [join(root, f) for f in files]
  files = [f for f in files if not re.match(excludes, f)]
  files = [f for f in files if re.match(includes, f)]
  files.sort(key=lambda f: stat(f).st_size, reverse=True)  # sort by file size descending
  return files


def indicateProgress():
  global idx
  print(prgChars[idx], end="\r")
  idx = (idx + 1) % len(prgChars)


def isFoundInFile(msgid, data):
  isFound = False
  regex_msgid = r'["\'](' + re.escape(msgid) + '|' + re.escape(polib.escape(msgid)) + ')["\']'
  if re.search(regex_msgid, data.read(0).decode()):
    isFound = True
  return isFound


def getUncachedEntries(poFile):
  entryIndex = 0
  unCachedEntries = []
  for entry in poFile:
    entryIndex = entryIndex + 1
    if prefs['processMaxEntries'] > 0:
      if entryIndex > prefs['processMaxEntries']:
        break
    if entry.msgid == " ":
      entry.tcomment = "DO NOT TRANSLATE!"
    elif (re.match("^#[a-fA-F0-9]{6,8}", entry.msgid)):
      entry.tcomment = "Remove from translation (hex color value)"
      entry.obsolete = True
    else:
      if (polib.escape(entry.msgid) in [o for o in occurrencesCache]):
        entry.occurrences = occurrencesCache[polib.escape(entry.msgid)]
      else:
        unCachedEntries.append(entry)
  return unCachedEntries


def searchCodebaseForOccurrences(poFile):
  if prefs['searchCodebaseForOccurrences']:
    unCachedEntries = getUncachedEntries(poFile)
    if len(unCachedEntries) > 0:
      print(f"Searching for {len(unCachedEntries)} occurrences...")
      for root, dirs, files in walk(codeBasePath, topdown=True, onerror=None):
        for fName in getIncludedExcludedPaths(root, dirs, files):
          indicateProgress()
          sys.stdout.flush()
          try:
            baseDirectory = fName.replace(codeBasePath, "")
            size = stat(fName).st_size
            f2 = open(fName)
            data = mmap.mmap(f2.fileno(), size, access=mmap.ACCESS_READ)
            entryIndex = 0

            for poEntry in unCachedEntries:
              entryIndex = entryIndex + 1
              if prefs['processMaxEntries'] > 0:
                if entryIndex > prefs['processMaxEntries']:
                  break
              encodedMsgid = polib.escape(poEntry.msgid)
              try:
                poEntry.occurrences = occurrencesCache[encodedMsgid]
              except KeyError:
                occurrencesCache[encodedMsgid] = []
              if isFoundInFile(poEntry.msgid, data):
                occurrencesCache[encodedMsgid] = occurrencesCache[encodedMsgid] + [(baseDirectory, '0')]
                poEntry.occurrences = occurrencesCache[encodedMsgid]
          except UnicodeDecodeError:
            # found non-text data
            pass
          except ValueError:
            # possibly an empty file
            pass
          finally:
            data = None


def processPoFile(fileName):
  poFile = polib.pofile(fileName)
  poFile.wrapwidth = 1024  # avoid re-wrapping
  # numObsoletesRemoved = 0
  entryIndex = 0
  for poEntry in poFile:
    entryIndex = entryIndex + 1
    if prefs['processMaxEntries'] > 0:
      if entryIndex > prefs['processMaxEntries']:
        break
    stripUnchangedMsgstrs(poEntry)
    removeMatchingObsolete(poFile, poEntry)
  searchCodebaseForOccurrences(poFile)
  return poFile


def addToPoStats(baseFileName, poFile):
  if prefs['outputFinalStats']:
    poStats['rowTitles'].append(baseFileName)
    poStats['data'].append([
                    len(poFile.translated_entries()) + len(poFile.untranslated_entries()),
                    len(poFile.fuzzy_entries()),
                    len(poFile.untranslated_entries()),
                    str(len(poFile.translated_entries())),
                    str(poFile.percent_translated()) + "%",
                    '-',  # numObsoletesRemoved
                  ])

# all entries that were found in the codebase will be added to
# or un-obsoleted from all .po files for consistency


def normaliseAllPoFiles(filesGlob):
  if prefs['normalisePoFiles']:
    fileIndex = 0
    for fileName in sorted(filesGlob):
      fileIndex = fileIndex + 1
      poFile = polib.pofile(fileName)
      poFile.wrapwidth = 1024  # avoid re-wrapping
      poFile.check_for_duplicates = True
      print("\rNormalising translation files..." + f" {float(fileIndex) / len(sorted(filesGlob)):.0%}", end=" ")
      sys.stdout.flush()

      for cacheEntry in sorted(occurrencesCache, key=lambda r: r[0]):
        matchedEntries = [e for e in poFile if e.msgid == polib.unescape(cacheEntry)]
        if len(matchedEntries) == 0 and len(occurrencesCache[cacheEntry]) > 0:
          try:
            newEntry = polib.POEntry(
              msgid=polib.unescape(cacheEntry),
              msgstr="",
              occurrences=occurrencesCache[cacheEntry],
              tcomment="normalised"
            )
            poFile.append(newEntry)
          except Exception:
            print("error adding")
            pass
        elif len(matchedEntries) == 1 and matchedEntries[0].obsolete:
          # matchedEntries[0].obsolete = False
          pass
      poFile.save(fileName + prefs['newFileExt'])


def main():
  startTime = time()
  try:
    filesGlob = glob(poFiles)
    fileCountStr = str(len(filesGlob))
    poFilesGlob = sorted(filesGlob, key=getsize, reverse=True)
    fileIndex = 0
    system('clear')
    print("Running... (first file will take substantially longer as there's no cache)")

    for fileName in poFilesGlob:
      fileIndex = fileIndex + 1
      baseFileName = basename(fileName)
      print(("Processing file %3d" % fileIndex) + "/" + str(fileCountStr) + " (" + baseFileName + ")")
      poFile = processPoFile(fileName)
      poFile.save(fileName + prefs['newFileExt'])
      addToPoStats(baseFileName, poFile)
    if prefs['outputFinalStats']:
      print("")
      rowFormat = "{:>12} " * (len(poStats['columnHeadings']) + 1)
      print(rowFormat.format("File", *poStats['columnHeadings']))
      rowsByName = sorted([line for line in zip(poStats['rowTitles'], poStats['data'])], key=lambda r: r[0])
      for pfs, row in rowsByName:
        print(rowFormat.format(pfs, *row))
    print("")
    normaliseAllPoFiles(poFilesGlob)
    hours, remainder = divmod(timedelta(seconds=time() - startTime).seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    print("\nComplete in " + f'{int(hours):02}:{int(minutes):02}:{int(seconds):02}' + "!\n")
  except KeyboardInterrupt:
    print("\nBye!")


if __name__ == "__main__":
  main()
