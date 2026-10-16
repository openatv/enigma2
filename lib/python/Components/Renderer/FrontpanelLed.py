from os.path import exists

from Components.Element import Element
# this is not a GUI renderer.


class FrontpanelLed(Element):
	def __init__(self, which=0, patterns=None, boolean=True):
		if not patterns:
			patterns = [(20, 0, 0xffffffff), (20, 0x55555555, 0x84fc8c04)]
		self.which = which
		self.boolean = boolean
		self.patterns = patterns
		Element.__init__(self)

	def changed(self, *args, **kwargs):
		def writeProc(fileName, value):
			if exists(fileName):
				with open(fileName, "w") as fd:
					fd.write(value)

		val = (0 if self.source.boolean else 1) if self.boolean else self.source.value
		speed, pattern, pattern4Bit = self.patterns[val]
		writeProc(f"/proc/stb/fp/led{self.which}_pattern", f"{pattern:08x}")
		if self.which == 0:
			writeProc("/proc/stb/fp/led_set_pattern", f"{pattern4Bit:08x}")
			writeProc("/proc/stb/fp/led_set_speed", str(speed))
			writeProc("/proc/stb/fp/led_pattern_speed", str(speed))
