# nitrogen14 - www.pristavka.de
from xml.etree.cElementTree import fromstring, ElementTree

class iptv_streams:
	
	def __init__(self):
		self.iptv_list = []
		self.groups = []

	def get_list(self):

		tree = ElementTree()
		tree.parse("/usr/lib/enigma2/python/Plugins/Extensions/nStreamPlayer/nstream.xml")
		group_id = 0
		chan_counter = 0
		for group in tree.findall('group'):
			group_id = group_id + 1
			group_name = group.findtext('name')
			cat_channels = []
			chan_id = 0
			for channel in group.findall('channel'):		
				chan_counter = chan_counter + 1 
				name = channel.findtext('name').encode('utf-8')
				piconname = channel.findtext('piconname')
				stream_url = channel.findtext('stream_url')
				ts_stream = channel.findtext('ts_stream')
				buffer_kb = channel.findtext('buffer_kb')

				chan_tulpe = (
					chan_counter,
					name,
					piconname,
					stream_url,
					ts_stream,
					buffer_kb,
					group_id,
					group_name,
				)
				self.iptv_list.append(chan_tulpe)
				cat_channels.append(chan_tulpe)
			counter = len(cat_channels)
			self.groups.append((
				group_id,
				group_name.encode('utf-8'),
				counter,
				cat_channels
				))