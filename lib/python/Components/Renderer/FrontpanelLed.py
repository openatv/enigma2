from Components.Element import Element

# this is not a GUI renderer.
class FrontpanelLed(Element):
	def changed(self, *args, **kwargs):
		if self.source.value:
			pattern = 0x55555555
			pattern_4bit = 0x84fc8c04
			speed = 20
		else:
			pattern = 0
			pattern_4bit = 0xffffffff
			speed = 1

		try:
			open("/proc/stb/fp/led0_pattern", "w").write("%08x" % pattern)
		except IOError:
			pass
		try:
			open("/proc/stb/fp/led_pattern", "w").write("%08x" % pattern_4bit)
		except IOError:
			pass
		try:
			open("/proc/stb/fp/led_pattern_speed", "w").write("%d" % speed)
		except IOError:
			pass
