class PluginDescriptor:
	"""An object to describe a plugin."""
	
	# where to list the plugin. Note that there are different call arguments,
	# so you might not be able to combine them.
	
	# supported arguments are:
	#   session
	#   servicereference
	#   reason
	
	# argument: session
	WHERE_BLUEMENU = 0
	WHERE_MAINMENU = 1
	WHERE_PLUGINMENU  = 2
	# argument: session, serviceref (currently selected)
	WHERE_MOVIELIST = 3
	# ...
	WHERE_SETUP    = 4
	
	# reason (0: start, 1: end)
	WHERE_AUTOSTART = 5
	
	# start as wizard. In that case, fnc must be a screen class!
	WHERE_WIZARD = 6
	
	def __init__(self, name = "Plugin", where = [ ], description = "", icon = None, fnc = None):
		self.name = name
		if type(where) is list:
			self.where = where
		else:
			self.where = [ where ]
		self.description = description
		if type(fnc) is str:
			self.icon = loadPNG("..")
		else:
			self.icon = icon
		self.__call__ = fnc
