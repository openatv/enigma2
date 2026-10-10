from Components.Converter.Converter import Converter
from Components.Element import cached

# The protocol works as follows:
# Lines starting with '-' are fatal errors (no recovery possible).
# Lines starting with '=' are progress notices.
# Lines starting with '+' are PIDs to record:
# 	"+d:[p:t[,p:t...]]" with d=demux nr, p: pid, t: type


class Streaming(Converter):
	@cached
	def getText(self):
		service = self.source.service
		if service is None:
			text = "-NO SERVICE\n"
		else:
			streaming = service.stream()
			streamData = streaming and streaming.getStreamingData()
			if streamData is None or not any(streamData):
				error = service.getError()
				text = f"-SERVICE ERROR:{int(error)}\n" if error else "=NO STREAM\n"
			else:
				pids = ",".join(f"{x[0]:x}:{x[1]}" for x in streamData["pids"])
				text = f"+{int(streamData['demux'])}:{pids}\n"
		return text

	text = property(getText)
