from Screens.Screen import Screen
from Plugins.Plugin import PluginDescriptor
from Components.PluginComponent import plugins
from Components.config import config
from CleanupWizard import checkFreeSpaceAvailable

freeSpace = checkFreeSpaceAvailable()
print "[CleanupWizard] freeSpaceAvailable-->",freeSpace


if freeSpace is None:
	internalMemoryExceeded = 0
elif int(freeSpace) <= 12048:
	internalMemoryExceeded = 1
else:
	internalMemoryExceeded = 0


def CleanupWizard(*args, **kwargs):
	from CleanupWizard import CleanupWizard
	return CleanupWizard(*args, **kwargs)

def Plugins(**kwargs):
	list = []
	if not config.misc.firstrun.value:
		if internalMemoryExceeded:
			list.append(PluginDescriptor(name=_("Cleanup Wizard"), where = PluginDescriptor.WHERE_WIZARD, fnc=(1, CleanupWizard)))
	return list

