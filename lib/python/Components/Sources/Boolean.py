from enigma import eTimer

from Components.Element import cached
from Components.Sources.Source import Source


# A small warning:
# You can use Boolean to express screen-private conditional expressions.
# However, if you think that there is ANY interest that another screen
# could use your expression, please put your calculation into a separate
# Source, providing a "boolean"-property.
#
class Boolean(Source):
	def __init__(self, fixed=False, function=None, destroy=None, poll=0):
		Source.__init__(self)
		self.fixed = fixed
		self.function = function
		self.postDestroy = destroy
		if poll > 0:
			self.pollTimer = eTimer()
			self.pollTimer.callback.append(self.poll)
			self.pollTimer.start(poll)
		else:
			self.pollTimer = None

	@cached
	def getBoolean(self):
		if self.function is not None:
			return self.function()
		else:
			return self.fixed

	def setBoolean(self, value):
		assert self.function is None
		self.fixed = value
		self.poll()

	boolean = property(getBoolean, setBoolean)

	def poll(self):
		self.changed((self.CHANGED_ALL,))

	def destroy(self):
		if self.pollTimer:
			self.pollTimer.callback.remove(self.poll)
		if self.postDestroy is not None:
			self.fixed = self.postDestroy
			self.poll()
		Source.destroy(self)
