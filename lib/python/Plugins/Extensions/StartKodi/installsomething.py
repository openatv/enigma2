from Screens.Screen import Screen
from enigma import quitMainloop
from Screens.MessageBox import MessageBox
from Screens.Ipkg import Ipkg
from Components.Ipkg import IpkgComponent

# 
# for common install invoke with 
# can handle multiple packages
# TODO: 
# - check why the frack ipkg does not report errors 
# - remove debug print
# - caller could check for Net + feeds availability, but more clever to do it here 
#
# How to use:
#    self.KodiInstallation = InstallSomething(self.session, [xbmc-turbo, wetek-good])
#    self.KodiInstallation.__install__()
# for restart question install invoke with:     self.KodiInstallation.__installRST__()

class InstallSomething():
	def __init__(self,session, url_to_download):
		self.session = session
		self.cmdList = []
		for item in url_to_download:
			print "----INSTALL SOMETHING---item ",  item
			self.cmdList.append((IpkgComponent.CMD_INSTALL, { "package": item }))

# plain install, just finish and exit
	def __install__(self):
		self.session.open(Ipkg, cmdList = self.cmdList)

# install with restart
	def __installRST__(self):
		self.session.openWithCallback(self.__restartMessage__, Ipkg, cmdList = self.cmdList)

	def __restartMessage__(self):
		self.session.openWithCallback(self.__restartGUI__, MessageBox,_("Restart Enigma2 to apply the changes?"), MessageBox.TYPE_YESNO, default = True)

	def __restartGUI__(self, callback = None):
		if callback == True:
			quitMainloop(3)
		elif callback == False:
			pass

