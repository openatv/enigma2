from Components.VariableText import VariableText
from Renderer import Renderer
from Tools.Event import Event

from enigma import eListbox

# the listbox renderer is the listbox, but no listbox content
# the content will be provided by the source (or converter).

# the source should emit the 'changed' signal whenever
# it has a new listbox content.

# the source needs to have the 'content' property for the
# used listbox content

# it should expose exactly the non-content related functions
# of the eListbox class. more or less.

class Listbox(Renderer, object):
	def __init__(self):
		Renderer.__init__(self)
		self.__content = None
		self.__wrap_around = False
		self.__selection_enabled = True

	GUI_WIDGET = eListbox

	def contentChanged(self):
		self.content = self.source.content

	def setContent(self, content):
		self.__content = content
		if self.instance is not None:
			self.instance.setContent(self.__content)

	content = property(lambda self: self.__content, setContent)

	def postWidgetCreate(self, instance):
		if self.__content is not None:
			instance.setContent(self.__content)
		instance.selectionChanged.get().append(self.selectionChanged)
		self.wrap_around = self.wrap_around # trigger
		self.selection_enabled = self.selection_enabled # trigger

	def setWrapAround(self, wrap_around):
		self.__wrap_around = wrap_around
		if self.instance is not None:
			self.instance.setWrapAround(self.__wrap_around)
	
	wrap_around = property(lambda self: self.__wrap_around, setWrapAround)

	def selectionChanged(self):
		self.source.selectionChanged(self.index)

	def getIndex(self):
		if self.instance is None:
			return None
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
		self.__selection_enabled = enabled
		if self.instance is not None:
			self.instance.setSelectionEnable(enabled)

	selection_enabled = property(lambda self: self.__selection_enabled, setSelectionEnabled)

	def changed(self):
		self.content = self.source.content
