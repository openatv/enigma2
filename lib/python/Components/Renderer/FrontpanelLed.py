from Components.Element import Element

# this is not a GUI renderer.
class FrontpanelLed(Element):
	def __init__(self):
		Element.__init__(self)

	def changed(self, *args, **kwargs):
		if self.source.value:
			pattern = 0x55555555
			speed = 20
		else:
			pattern = 0
			speed = 1

		try:
			open("/proc/stb/fp/led0_pattern", "w").write("%08x" % pattern)
			open("/proc/stb/fp/led_pattern_speed", "w").write("%d" % speed)
		except IOError:
			pass
