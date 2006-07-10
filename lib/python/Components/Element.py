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

	# we disconnect from down to up
	def disconnectAll(self):
		# we should not disconnect from upstream if
		# there are still elements depending on us.
		assert len(self.downstream_elements) == 0, "there are still downstream elements left"
		
		# disconnect all upstream elements from us
		for upstream in self.upstream_elements:
			upstream.disconnectDownstream(self)
	
	def disconnectDownstream(self, downstream):
		self.downstream_elements.remove(downstream)
		if self.master == downstream:
			self.master = None
		
		if len(self.downstream_elements) == 0:
			self.disconnectAll()

	# default action: push downstream
	def changed(self, *args, **kwargs):
		self.downstream_elements.changed(*args, **kwargs)
