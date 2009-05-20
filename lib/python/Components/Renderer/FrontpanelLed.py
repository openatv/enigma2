from Components.Element import Element

# this is not a GUI renderer.
class FrontpanelLed(Element):
	def __init__(self, which = 0, pattern_on = (20, 0x55555555, 0x84fc8c04), pattern_off = (20, 0, 0xffffffff)):
		self.which = which
		self.pattern_on = pattern_on
		self.pattern_off = pattern_off
		Element.__init__(self)

	def changed(self, *args, **kwargs):
		if self.source.boolean:
			(speed, pattern, pattern_4bit) = self.pattern_on
		else:
			(speed, pattern, pattern_4bit) = self.pattern_off

		try:
			open("/proc/stb/fp/led%d_pattern" % self.which, "w").write("%08x" % pattern)
		except IOError:
			pass
		if self.which == 0:
			try:
				open("/proc/stb/fp/led_pattern", "w").write("%08x" % pattern_4bit)
			except IOError:
				pass
			try:
				open("/proc/stb/fp/led_pattern_speed", "w").write("%d" % speed)
			except IOError:
				pass
