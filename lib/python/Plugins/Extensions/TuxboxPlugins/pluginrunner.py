from enigma import eDBoxLCD, eRCInput, fbClass, eConsoleAppContainer
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox

class PluginRunner(Screen):
	skin = """
		<screen position="1,1" size="1,1" title="Plugin" >
        </screen>"""
	def __init__(self, session, pluginname, args = None):
		self.skin = PluginRunner.skin
		Screen.__init__(self, session)
		self.container = eConsoleAppContainer()
		self.container.appClosed.append(self.finishedExecution)
		self.runPlugin(pluginname)

	def runPlugin(self, pluginname):
		eDBoxLCD.getInstance().lock()
		eRCInput.getInstance().lock()
		fbClass.getInstance().lock()
		print "executing:", ("pluginlauncher -x %s" % pluginname)
		if self.container.execute("pluginlauncher -x %s" % pluginname):
			self.finishedExecution(None)

	def finishedExecution(self, retval = 1):
		print "PluginRunner retval:", retval
		fbClass.getInstance().unlock()
		eRCInput.getInstance().unlock()
		eDBoxLCD.getInstance().unlock()

		if retval is None or retval != 1:
			self.session.openWithCallback(
				self.finishedExecution,
				MessageBox,
				_("Error executing plugin") % param
			)
		else:
			self.close()
