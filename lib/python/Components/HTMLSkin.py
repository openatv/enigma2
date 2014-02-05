class HTMLSkin:
	order = ()

	def __init__(self, order):
		self.order = order

	def produceHTML(self):
		res = "<html>\n"
		for name in self.order:
			res += self[name].produceHTML()
		res += "</html>\n"
		return res

