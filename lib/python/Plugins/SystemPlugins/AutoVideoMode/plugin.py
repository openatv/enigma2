from Screens.Screen import Screen
from Plugins.Plugin import PluginDescriptor
from Components.config import config
from Components.ServiceEventTracker import ServiceEventTracker
from enigma import iPlayableService, iServiceInformation, eTimer
from os import path

from Components.AVSwitch import iAVSwitch

class AutoFrameRate(Screen):
	def __init__(self, session, hw):
		Screen.__init__(self, session)
		self.__event_tracker = ServiceEventTracker(screen=self, eventmap=
			{
				iPlayableService.evVideoSizeChanged: self.VideoChanged,
				iPlayableService.evVideoProgressiveChanged: self.VideoChanged,
				iPlayableService.evVideoFramerateChanged: self.VideoChanged,
				iPlayableService.evVideoFramerateChanged: self.VideoChanged,
				iPlayableService.evBuffering: self.BufferInfo,
				# iPlayableService.evUpdatedInfo: self.VideoChanged,
				# iPlayableService.evStart: self.__evStart
			})

		self.delay = False
		self.bufferfull = True
		self.detecttimer = eTimer()
		self.detecttimer.callback.append(self.VideoChangeDetect)
		self.hw = hw

	def BufferInfo(self):
		bufferInfo = self.session.nav.getCurrentService().streamed().getBufferCharge()
		if bufferInfo[0] > 98:
			print '!!!!!!!!!!!!!!!bufferfull'
			self.bufferfull = True
			self.VideoChanged()
		else:
			self.bufferfull = False

	def VideoChanged(self):
		print '!!!!!!!!!!!!!!!!!!!!!!!!VideoChanged'
		print 'REF:',self.session.nav.getCurrentlyPlayingServiceReference().toString()
		print 'REF:',self.session.nav.getCurrentlyPlayingServiceReference().toString().startswith('4097:')
		if self.session.nav.getCurrentlyPlayingServiceReference() and not self.session.nav.getCurrentlyPlayingServiceReference().toString().startswith('4097:'):
			delay = 200
		else:
			delay = 200
		if not self.detecttimer.isActive() and not self.delay:
			print 'TEST 1:',delay
			self.delay = True
			self.detecttimer.start(delay)
		else:
			print 'TEST2:',delay
			self.delay = True
			self.detecttimer.stop()
			self.detecttimer.start(delay)

	def VideoChangeDetect(self):
		print '!!!!!!!!!!!!!!!!!!!!!!!!VideoChangeDetect'

		config_port = config.av.videoport.getValue()
		config_mode = str(config.av.videomode[config_port].getValue())
		print 'config mode:',config_mode
		config_res = str(config.av.videomode[config_port].getValue()[:-1])
		print 'config res:',config_res
		config_rate = str(config.av.videorate[config_mode].getValue())
		print 'config rate:',config_rate
		config_pol = str(config.av.videomode[config_port].getValue()[-1:])
		print 'config pol:',config_pol

		print '\n'

		f = open("/proc/stb/video/videomode")
		current_mode = f.read()[:-1]
		f.close()
		print 'current mode:',current_mode

		if current_mode and current_mode.find('i') != -1:
			current_pol = 'i'
		elif current_mode and current_mode.find('p') != -1:
			current_pol = 'p'
		else:
			current_pol = ''
		print 'current pol:',current_pol

		current_res = current_mode.split(current_pol)[0]
		print 'current res:',current_res

		if len(current_mode.split(current_pol)) > 0:
			current_rate = current_mode.split(current_pol)[1]
		else:
			current_rate = ""
		print 'current rate:',current_rate

		print '\n'

		service = self.session.nav.getCurrentService()
		if service is not None:
			info = service.info()
		else:
			info = None

		if info:
			video_height = int(info.getInfo(iServiceInformation.sVideoHeight))
			print 'video height:',video_height
			video_width = int(info.getInfo(iServiceInformation.sVideoWidth))
			print 'video width:',video_width
			video_pol = ("i", "p")[info.getInfo(iServiceInformation.sProgressive)]
			print 'video pol:',video_pol
			video_rate = int(info.getInfo(iServiceInformation.sFrameRate))
			print 'video rate:',video_rate

			print '\n'

			if video_height != -1:
				if video_height > 720:
					new_res = "1080"
				elif video_height > 576 and video_height <= 720:
					new_res = "720"
				elif video_height > 480 and video_height <= 576:
					new_res = "576"
				else:
					new_res = "480"
			else:
				new_res = config_res
			print 'new res:',new_res

			if video_rate != -1:
				if video_rate in (29970, 30000, 59940, 60000) and video_pol == 'i':
					new_rate = 60000
				elif video_pol == 'i':
					new_rate = 50000
				else:
					new_rate = video_rate
				new_rate = str((new_rate + 500) / 1000)
			else:
				new_rate = config_rate
			print 'new rate:',new_rate

			if video_pol != -1:
				new_pol = str(video_pol)
			else:
				new_pol = config_pol
			print 'new pol:',new_pol
			self.hw.readAvailableModes()
			if new_res+new_pol+new_rate in self.hw.modes_available:
				new_mode = new_res+new_pol+new_rate
			elif new_res+new_pol in self.hw.modes_available:
				new_mode = new_res+new_pol
			else:
				new_mode = config_mode
			print 'new mode:',new_mode

		print 'config.av.autores:',config.av.autores.getValue(
		if config.av.autores.getValue():
			write_mode = new_mode
		else:
			if path.exists('/proc/stb/video/videomode_%shz' % new_rate) and config_rate == 'multi':
				f = open("/proc/stb/video/videomode_%shz" % new_rate, "r")
				multi_videomode = f.read()
				print 'multi_videomode:',multi_videomode
				f.close()
			else:
				multi_videomode = None

			write_mode = config_mode
			if multi_videomode and (write_mode != multi_videomode):
				write_mode = multi_videomode

		print '\n'
		print 'CURRENT MODE:',current_mode
		print 'NEW MODE:',write_mode

		if current_mode != write_mode and self.bufferfull:
			print "[VideoMode] setMode - port: %s, mode: %s" % (config_port, write_mode)
			f = open("/proc/stb/video/videomode", "w")
			f.write(write_mode)
			f.close()

		self.hw.setAspect(config.av.aspect)
		self.hw.setWss(config.av.wss)
		self.hw.setPolicy43(config.av.policy_43)
		self.hw.setPolicy169(config.av.policy_169)

		self.delay = False
		self.detecttimer.stop()

def autostart(reason, **kwargs):
	global session
	if kwargs.has_key("session") and reason == 0:
		session = kwargs["session"]
		AutoFrameRate(session, iAVSwitch)

def Plugins(**kwargs):
	return [PluginDescriptor(where = [PluginDescriptor.WHERE_SESSIONSTART, PluginDescriptor.WHERE_AUTOSTART], fnc = autostart)]