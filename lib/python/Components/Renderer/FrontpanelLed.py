from Components.Element import Element
from os import path
# this is not a GUI renderer.
class FrontpanelLed(Element):
	def __init__(self, which=0, patterns=None, boolean=True):
		if not patterns: patterns = [(20, 0, 0xffffffff), (20, 0x55555555, 0x84fc8c04)]
		self.which = which
		self.boolean = boolean
		self.patterns = patterns
		Element.__init__(self)

	def changed(self, *args, **kwargs):
		if self.boolean:
			val = self.source.boolean and 0 or 1
		else:
			val = self.source.value

		(speed, pattern, pattern_4bit) = self.patterns[val]

		if path.exists("/proc/stb/fp/led%d_pattern" % self.which):
			f = open("/proc/stb/fp/led%d_pattern" % self.which, "w")
			f.write("%08x" % pattern)
			f.close()
		if self.which == 0:
			if path.exists("/proc/stb/fp/led_set_pattern"):
				f = open("/proc/stb/fp/led_set_pattern", "w")
				f.write("%08x" % pattern_4bit)
				f.close()
			if path.exists("/proc/stb/fp/led_set_speed"):
				f = open("/proc/stb/fp/led_set_speed", "w")
				f.write("%d" % speed)
				f.close()
			if path.exists("/proc/stb/fp/led_pattern_speed"):
				f = open("/proc/stb/fp/led_pattern_speed", "w")
				f.write("%d" % speed)
				f.close()
