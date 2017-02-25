from Components.ActionMap import ActionMap
from Components.Sources.StaticText import StaticText
from Components.Button import Button
from Components.ScrollLabel import ScrollLabel
from Components.Label import Label
from Components.config import config
from Screens.Screen import Screen

from enigma import eTimer
from boxbranding import getImageVersion, getImageBuild, getImageDevBuild, getImageType
from sys import modules

from datetime import datetime
from json import loads
import urllib2

if getImageType() == 'release':
	ImageVer = getImageBuild()
else:
	ImageVer = "%s.%s" % (getImageBuild(),getImageDevBuild())
	ImageVer = float(ImageVer)

E2Branches = {
	'developer' : 'Dev',
	'release' : 'Master'
	}

project = 0
projects = [
	("https://api.github.com/repos/OpenViX/enigma2/commits?sha=%s" % E2Branches[getImageType()], "Enigma2"),
	("https://api.github.com/repos/OpenViX/vix-core/commits", "ViX Core"),
	("https://api.github.com/repos/OpenViX/skins/commits", "ViX Skins"),
	("https://api.github.com/repos/oe-alliance/oe-alliance-core/commits?sha=4.0", "OE-A Core"),
	("https://api.github.com/repos/oe-alliance/oe-alliance-plugins/commits?sha=2.3", "OE-A Plugins"),
	("https://api.github.com/repos/oe-alliance/AutoBouquetsMaker/commits", "AutoBouquetsMaker"),
	("https://api.github.com/repos/oe-alliance/branding-module/commits", "Branding Module"),
]
cachedProjects = {}

def readGithubCommitLogsSoftwareUpdate():
	global ImageVer
	gitstart = True
	url = projects[project][0]
	commitlog = ""
	try:
		try:
			from ssl import _create_unverified_context
			log = loads(urllib2.urlopen(url, timeout=5, context=_create_unverified_context()).read())
		except:
			log = loads(urllib2.urlopen(url, timeout=5).read())
		for c in log:
			if gitstart and not c['commit']['message'].startswith('openvix:') and getScreenTitle() in ("Enigma2", "OE-A Core"):
					continue
			if c['commit']['message'].startswith('openvix:'):
				gitstart = False
				if getImageType() == 'release' and c['commit']['message'].startswith('openvix: developer'):
					print '[GitCommitLog] Skipping developer line'
					continue
				elif getImageType() == 'developer' and c['commit']['message'].startswith('openvix: release'):
					print '[GitCommitLog] Skipping release line'
					continue
				tmp = c['commit']['message'].split(' ')[2].split('.')
				if len(tmp) > 2:
					if getImageType() == 'release':
						releasever = tmp[2]
					else:
						releasever = '%s.%s' % (tmp[2], tmp[3])
				releasever = float(releasever)
				if ImageVer >= releasever:
					blockstart = True
					break

			creator = c['commit']['author']['name']
			title = c['commit']['message']
			date = datetime.strptime(c['commit']['committer']['date'], '%Y-%m-%dT%H:%M:%SZ').strftime('%x %X')
			commitlog += date + ' ' + creator + '\n' + title + 2 * '\n'
		commitlog = commitlog.encode('utf-8')
		cachedProjects[getScreenTitle()] = commitlog
	except urllib2.HTTPError, err:
		if err.code == 403:
			print '[GitCommitLog] It seems you have hit your API limit - please try later again'
			commitlog += _("It seems you have hit your API limit - please try later again")
		else:
			print '[GitCommitLog] Currently the commit log cannot be retrieved - please try later again\n%s' % err
			commitlog += _("Currently the commit log cannot be retrieved - please try later again\n%s" % err)
	except urllib2.URLError, err:
		print '[GitCommitLog] Currently the commit log cannot be retrieved - please try later again\n%s' % err.reason[0]
		commitlog += _("Currently the commit log cannot be retrieved - please try later again\n%s" % err.reason[0])
	except urllib2, err:
		print '[GitCommitLog] Currently the commit log cannot be retrieved - please try later again\n%s' % err
		commitlog += _("Currently the commit log cannot be retrieved - please try later again\n%s" % err)
	except:
		print '[GitCommitLog] Currently the commit log cannot be retrieved - please try later again'
		commitlog += _("Currently the commit log cannot be retrieved - please try later again")
	return commitlog

def readGithubCommitLogs():
	global ImageVer
	global cachedProjects
	cachedProjects = {}
	blockstart = False
	gitstart = True
	url = projects[project][0]
	commitlog = ""
	try:
		try:
			from ssl import _create_unverified_context
			log = loads(urllib2.urlopen(url, timeout=5, context=_create_unverified_context()).read())
		except:
			log = loads(urllib2.urlopen(url, timeout=5).read())
		for c in log:
			if gitstart and not c['commit']['message'].startswith('openvix:') and getScreenTitle() in ("Enigma2", "OE-A Core"):
				continue
			if c['commit']['message'].startswith('openvix:'):
				blockstart = False
				gitstart = False
				if getImageType() == 'release' and c['commit']['message'].startswith('openvix: developer'):
					print '[GitCommitLog] Skipping developer line'
					continue
				elif getImageType() == 'developer' and c['commit']['message'].startswith('openvix: release'):
					print '[GitCommitLog] Skipping release line'
					continue
				tmp = c['commit']['message'].split(' ')[2].split('.')
				if len(tmp) > 2:
					if getImageType() == 'release':
						releasever = tmp[2]
					else:
						releasever = '%s.%s' % (tmp[2], tmp[3])
				releasever = float(releasever)
				if releasever > ImageVer:
					blockstart = True
					continue
			elif blockstart and getScreenTitle() in ("Enigma2", "OE-A Core"):
				blockstart = True
				continue

			creator = c['commit']['author']['name']
			title = c['commit']['message']
			date = datetime.strptime(c['commit']['committer']['date'], '%Y-%m-%dT%H:%M:%SZ').strftime('%x %X')
			commitlog += date + ' ' + creator + '\n' + title + 2 * '\n'
		commitlog = commitlog.encode('utf-8')
		cachedProjects[getScreenTitle()] = commitlog
	except urllib2.HTTPError, err:
		if err.code == 403:
			print '[GitCommitLog] It seems you have hit your API limit - please try later again'
			commitlog += _("It seems you have hit your API limit - please try later again")
		else:
			print '[GitCommitLog] Currently the commit log cannot be retrieved - please try later again\n%s' % err
			commitlog += _("Currently the commit log cannot be retrieved - please try later again\n%s" % err)
	except urllib2.URLError, err:
		print '[GitCommitLog] Currently the commit log cannot be retrieved - please try later again\n%s' % err.reason[0]
		commitlog += _("Currently the commit log cannot be retrieved - please try later again\n%s" % err.reason[0])
	except urllib2, err:
		print '[GitCommitLog] Currently the commit log cannot be retrieved - please try later again\n%s' % err
		commitlog += _("Currently the commit log cannot be retrieved - please try later again\n%s" % err)
	except:
		print '[GitCommitLog] Currently the commit log cannot be retrieved - please try later again'
		commitlog += _("Currently the commit log cannot be retrieved - please try later again")
	return commitlog

def getScreenTitle():
	return projects[project][1]

def left():
	global project
	project = project == 0 and len(projects) - 1 or project - 1

def right():
	global project
	project = project != len(projects) - 1 and project + 1 or 0

gitcommitinfo = modules[__name__]

class CommitInfo(Screen):
	def __init__(self, session, menu_path = ""):
		Screen.__init__(self, session)
		self.menu_path = menu_path
		self.skinName = ["CommitInfo", "AboutOE"]
		self["menu_path_compressed"] = StaticText("")
		self["AboutScrollLabel"] = ScrollLabel(_("Please wait"))
		self["HintText"] = Label(_("Press left/right to scroll through logs"))

		self["actions"] = ActionMap(["SetupActions", "DirectionActions"],
			{
				"cancel": self.close,
				"ok": self.close,
				"up": self["AboutScrollLabel"].pageUp,
				"down": self["AboutScrollLabel"].pageDown,
				"left": self.left,
				"right": self.right
			})

		self["key_red"] = Button(_("Cancel"))

		self.Timer = eTimer()
		self.Timer.callback.append(self.readGithubCommitLogs)
		self.Timer.start(50, True)

	def updateScreenTitle(self, screentitle):
		if config.usage.show_menupath.value == 'large':
			title = self.menu_path + screentitle
			self["menu_path_compressed"].setText("")
		elif config.usage.show_menupath.value == 'small':
			title = screentitle
			self["menu_path_compressed"].setText(self.menu_path + " >" if not self.menu_path.endswith(' / ') else self.menu_path[:-3] + " >" or "")
		else:
			title = screentitle
			self["menu_path_compressed"].setText("")
		self.setTitle(title)

	def readGithubCommitLogs(self):
		self.updateScreenTitle(gitcommitinfo.getScreenTitle())
		self["AboutScrollLabel"].setText(gitcommitinfo.readGithubCommitLogs())

	def updateCommitLogs(self):
		if gitcommitinfo.cachedProjects.has_key(gitcommitinfo.getScreenTitle()):
			self.updateScreenTitle(gitcommitinfo.getScreenTitle())
			self["AboutScrollLabel"].setText(gitcommitinfo.cachedProjects[gitcommitinfo.getScreenTitle()])
		else:
			self["AboutScrollLabel"].setText(_("Please wait"))
			self.Timer.start(50, True)

	def left(self):
		gitcommitinfo.left()
		self.updateCommitLogs()

	def right(self):
		gitcommitinfo.right()
		self.updateCommitLogs()

	def closeRecursive(self):
		self.close(("menu", "menu"))
