# fake-enigma

import fake_time

class slot:
	def __init__(self):
		self.list = [ ]

	def get(self):
		return self.list

	def __call__(self):
		for x in self.list:
			x()

timers = set()

import time

##################### ENIGMA BASE

class eTimer:
	def __init__(self):
		self.timeout = slot()
		self.next_activation = None
	
	def start(self, msec, singleshot = False):
		self.next_activation = time.time() + msec / 1000.0
		self.msec = msec
		self.singleshot = singleshot
		timers.add(self)
	
	def stop():
		timers.remove(self)

	def __repr__(self):
		return "<eTimer timeout=%s next_activation=%s singleshot=%s>" % (repr(self.timeout), repr(self.next_activation), repr(self.singleshot))

	def do(self):
		if self.singleshot:
			self.stop()
		self.next_activation += self.msec / 1000.0
		print "next activation now %d " % self.next_activation
		self.timeout()

def runIteration():
	running_timers = list(timers)
	assert len(running_timers), "no running timers, so nothing will ever happen!"
	running_timers.sort(key=lambda x: x.next_activation)
	print running_timers
	
	next_timer = running_timers[0]

	now = time.time()
	delay = next_timer.next_activation - now 
	
	if delay > 0:
		time.sleep(delay)
		now += delay

	while len(running_timers) and running_timers[0].next_activation <= now:
		running_timers[0].do()
		running_timers = running_timers[1:]

stopped = False

def stop():
	global stopped
#	print "STOP NOW"
#	stopped = True

def run():
	stoptimer = eTimer()
	stoptimer.start(10000)
	stoptimer.timeout.get().append(stop)
	while not stopped:
		runIteration()


##################### ENIGMA GUI

eSize = None
ePoint = None
gFont = None
eWindow = None
eLabel = None
ePixmap = None
eWindowStyleManager = None
loadPNG = None
addFont = None
gRGB = None
eWindowStyleSkinned = None

##################### ENIGMA CONFIG

import Components.config

my_config = [
"config.skin.primary_skin=None\n"
]

Components.config.config.unpickle(my_config)

