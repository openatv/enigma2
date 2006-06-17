from Tools.CList import CList

# down                       up
# Render Converter Converter Source

# a bidirectional connection
class Element:
	def __init__(self):
		self.downstream_elements = CList()
		self.upstream_elements = CList()
		self.master = None
		self.source = None

	def connectDownstream(self, downstream):
		self.downstream_elements.append(downstream)
		if self.master is None:
			self.master = downstream
	
	def connectUpstream(self, upstream):
		self.upstream_elements.append(upstream)
		self.source = upstream # for single-source elements (i.e., most of them.)
		self.changed()
	
	def connect(self, upstream):
		self.connectUpstream(upstream)
		upstream.connectDownstream(self)

	# default action: push downstream
	def changed(self):
		self.downstream_elements.changed()
