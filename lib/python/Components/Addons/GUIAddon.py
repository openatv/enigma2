from Components.GUIComponent import GUIComponent


class GUIAddon(GUIComponent):
	def __init__(self):
		GUIComponent.__init__(self)
		self.source = None
		self.sources = {}
		self.relatedScreen = None

	def connectRelatedElement(self, relatedElementName, container):
		relatedElementNames = relatedElementName.split(",")
		if len(relatedElementNames) == 1:
			if relatedElementName == "session":
				self.source = container.session
			else:
				self.source = container[relatedElementName]
				if self.source and hasattr(self.source, "onVisibilityChange"):
					self.source.onVisibilityChange.append(self.onSourceVisibleChanged)
		elif len(relatedElementNames) > 1:
			for x in relatedElementNames:
				if x in container:
					component = container[x]
					self.sources[x] = component
					if isinstance(component, GUIComponent) and x not in container.handledWidgets:
						container.handledWidgets.append(x)
		container.onShow.append(self.onContainerShown)
		self.relatedScreen = container

	def onContainerShown(self):  # This will be overwritten by subclass
		pass

	def onSourceVisibleChanged(self):  # This will be overwritten by subclass
		pass
