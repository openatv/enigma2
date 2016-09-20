from Converter import Converter
from Components.Element import cached

# the protocol works as the following:

# lines starting with '-' are fatal errors (no recovery possible),
# lines starting with '=' are progress notices,
# lines starting with '+' are PIDs to record:
# 	"+d:[p:t[,p:t...]]" with d=demux nr, p: pid, t: type

class Streaming(Converter):
	@cached
	def getText(self):
		service = self.source.service
		if service is None:
			return "-NO SERVICE\n"

		streaming = service.stream()
		s = streaming and streaming.getStreamingData()

		if s is None or not any(s):
			err = hasattr(service, 'getError') and service.getError()
			if err:
				return "-SERVICE ERROR:%d\n" % err
			else:
				return "=NO STREAM\n"

		demux = s["demux"]
		pids = ','.join(["%x:%s" % (x[0], x[1]) for x in s["pids"]])

		return "+%d:%s\n" % (demux, pids)

	text = property(getText)
