from Source import Source
from Components.Element import cached
from enigma import eTimer

# a small warning:
# you can use that boolean well to express screen-private
# conditional expressions.
#
# however, if you think that there is ANY interest that another
# screen could use your expression, please put your calculation
# into a seperate Source, providing a "boolean"-property.
class Boolean(Source, object):
	def __init__(self, fixed = False, function = None, poll = 0):
		Source.__init__(self)
		if poll > 0:
			self.poll_timer = eTimer()
			self.poll_timer.timeout.get().append(self.poll)
			self.poll_timer.start(poll)

	@cached
	def getBoolean(self):
		if self.function is not None:
			return self.function()
		else:
			return self.fixed

	boolean = property(getBoolean)

	def poll(self):
		self.changed((self.CHANGED_ALL,))
