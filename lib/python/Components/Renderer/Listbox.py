from Components.Renderer.Renderer import Renderer
from enigma import eListbox

# the listbox renderer is the listbox, but no listbox content.
# the content will be provided by the source (or converter).

# the source should emit the 'changed' signal whenever
# it has a new listbox content.

# the source needs to have the 'content' property for the
# used listbox content

# it should expose exactly the non-content related functions
# of the eListbox class. more or less.


class Listbox(Renderer):
	def __init__(self):
		Renderer.__init__(self)
		self.__content = None
		self.__selectionEnabled = True  # FIXME: The default is true already.
		self.scale = None

	GUI_WIDGET = eListbox

	def contentChanged(self):
		self.content = self.source.content

	def setContent(self, content):
		self.__content = content
		if self.instance is not None:
			self.instance.setContent(self.__content)

	content = property(lambda self: self.__content, setContent)

	def applySkin(self, desktop, parent):
		self.scale = parent.scale
		return Renderer.applySkin(self, desktop, parent)

	def postWidgetCreate(self, instance):
		if self.__content is not None:
			instance.setContent(self.__content)
		instance.selectionChanged.get().append(self.selectionChanged)
		# Trigger property changes
		self.setWrapAround(self.wrapAround)
		self.setSelectionEnabled(self.selectionEnabled)
		self.setScrollbarMode(self.scrollbarMode)

	def preWidgetRemove(self, instance):
		instance.setContent(None)
		instance.selectionChanged.get().remove(self.selectionChanged)

	def setWrapAround(self, wrapAround):
		if self.instance is not None:
			self.instance.setWrapAround(wrapAround)

	def getWrapAround(self):
		return self.instance and self.instance.getWrapAround()

	wrapAround = property(getWrapAround, setWrapAround)

	def selectionChanged(self):
		self.source.selectionChanged(self.index)

	def getIndex(self):
		if self.instance is None:
			return 0
		return self.instance.getCurrentIndex()

	def moveToIndex(self, index):
		if self.instance is None:
			return
		self.instance.moveSelectionTo(index)

	index = property(getIndex, moveToIndex)

	def move(self, direction):
		if self.instance is not None:
			self.instance.moveSelection(direction)

	def setSelectionEnabled(self, enabled):
		self.__selectionEnabled = enabled
		if self.instance is not None:
			self.instance.setSelectionEnable(enabled)

	selectionEnabled = property(lambda self: self.__selectionEnabled, setSelectionEnabled)

	def setScrollbarMode(self, mode):
		if self.instance is not None:
			self.instance.setScrollbarMode(
				{
					"showOnDemand": eListbox.showOnDemand,
					"showAlways": eListbox.showAlways,
					"showNever": eListbox.showNever,
					"showLeft": eListbox.showLeftOnDemand,
					"showLeftOnDemand": eListbox.showLeftOnDemand,
					"showLeftAlways": eListbox.showLeftAlways,
				}.get(mode, eListbox.showNever))

	def getScrollbarMode(self):
		mode = self.instance and self.instance.getScrollbarMode()
		mode = {
				eListbox.showOnDemand: "showOnDemand",
				eListbox.showAlways: "showAlways",
				eListbox.showNever: "showNever",
				eListbox.showLeftOnDemand: "showLeftOnDemand",
				eListbox.showLeftAlways: "showLeftAlways",
			}.get(mode, "showNever")
		return mode

	scrollbarMode = property(getScrollbarMode, setScrollbarMode)

	def changed(self, what):
		if hasattr(self.source, "selectionEnabled"):
			self.selectionEnabled = self.source.selectionEnabled
		if hasattr(self.source, "scrollbarMode"):
			self.scrollbarMode = self.source.scrollbarMode
		if len(what) > 1 and isinstance(what[1], str) and what[1] == "style":
			return
		if self.content:
			return
		self.content = self.source.content

	def entry_changed(self, index):
		if self.instance is not None:
			self.instance.entryChanged(index)
