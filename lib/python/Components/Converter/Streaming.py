from Converter import Converter
from Components.Element import cached

class Streaming(Converter):
	def __init__(self, type):
		Converter.__init__(self, type)

	@cached
	def getText(self):
		service = self.source.service
		if service is None:
			return "-NO SERVICE"

		streaming = service.stream()
		s = streaming and streaming.getStreamingData()

		if streaming is None:
			err = service.getError()
			return "-1SERVICE ERROR:%d" % err

		r = streaming.getStreamingData()
		if r is None:
			return "-NO STREAM"

		demux = r["demux"]
		pids = ','.join(["%x:%s" % (x[0], x[1]) for x in r["pids"]])

		return "+%d:%s\n" % (demux, pids)

	text = property(getText)
