from Components.ActionMap import ActionMap
from Components.Ipkg import IpkgComponent
from Components.Label import Label
from Components.SelectionList import SelectionList
from Plugins.Plugin import PluginDescriptor
from Screens.Ipkg import Ipkg
from Screens.Screen import Screen

class IpkgInstaller(Screen):
	skin = """
		<screen position="100,100" size="550,400" title="..." >
			<widget name="red" halign="center" valign="center" position="0,0" size="140,60" backgroundColor="red" font="Regular;21" />
			<widget name="green" halign="center" valign="center" position="140,0" text="Install selected" size="140,60" backgroundColor="green" font="Regular;21" />
			<widget name="yellow" halign="center" valign="center" position="280,0" size="140,60" backgroundColor="yellow" font="Regular;21" />
			<widget name="blue" halign="center" valign="center" position="420,0" size="140,60" backgroundColor="blue" font="Regular;21" />
			<widget name="list" position="0,60" size="550,360" />
		</screen>
		"""
	
	def __init__(self, session, list):
		self.skin = IpkgInstaller.skin
		Screen.__init__(self, session)
		
		self.list = SelectionList()
		self["list"] = self.list
		for listindex in range(len(list)):
			self.list.addSelection(list[listindex], list[listindex], listindex, True)

		self["red"] = Label()
		self["green"] = Label()
		self["yellow"] = Label()
		self["blue"] = Label()
		
		self["actions"] = ActionMap(["OkCancelActions", "ColorActions"], 
		{
			"ok": self.list.toggleSelection, 
			"cancel": self.close, 
			"green": self.install
		}, -1)
		
	def install(self):
		list = self.list.getSelectionsList()
		cmdList = []
		for item in list:
			cmdList.append((IpkgComponent.CMD_INSTALL, { "package": item[1] }))
		print cmdList
		self.session.open(Ipkg, cmdList = cmdList)

def filescan_open(list, session, **kwargs):
	session.open(IpkgInstaller, list) # list

def filescan():
	# we expect not to be called if the MediaScanner plugin is not available,
	# thus we don't catch an ImportError exception here
	from Plugins.Extensions.MediaScanner.plugin import Scanner, ScanPath
	return \
		Scanner(extensions = ["ipk"], 
			paths_to_scan = 
				[
					ScanPath(path = "ipk", with_subdirs = True), 
					ScanPath(path = "", with_subdirs = False), 
				], 
			name = "Ipkg", 
			description = "Install software updates...", 
			openfnc = filescan_open, 
																																																																)
		
def Plugins(**kwargs):
	return [ PluginDescriptor(name="Ipkg", where = PluginDescriptor.WHERE_FILESCAN, fnc = filescan) ]