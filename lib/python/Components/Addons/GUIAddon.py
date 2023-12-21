from Components.GUIComponent import GUIComponent


class GUIAddon(GUIComponent):
	def __init__(self):
		GUIComponent.__init__(self)
		self.sources = {}
		self.relatedScreen = None

	def connectRelatedElement(self, relatedElementName, container):
		relatedElementNames = relatedElementName.split(",")
		if len(relatedElementNames) == 1:
			self.source = container[relatedElementName]
		elif len(relatedElementNames) > 1:
			for x in relatedElementNames:
				if x in container:
					component = container[x]
					self.sources[x] = component
					if isinstance(component, GUIComponent) and x not in container.handledWidgets:
						container.handledWidgets.append(x)
		container.onShow.append(self.onContainerShown)
		self.relatedScreen = container

	def onContainerShown(self):  # This function needs to be overwritten
		pass
