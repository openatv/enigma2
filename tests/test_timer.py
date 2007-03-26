import enigma
import sys
import time

#enigma.reset()
def test_timer(repeat = 0, timer_start = 10, timer_length = 100):
	import RecordTimer
	
	at = time.time()
	
	t = RecordTimer.RecordTimer()

	# generate a timer to test
	import xml.dom.minidom

	timer = RecordTimer.createTimer(xml.dom.minidom.parseString(
	"""
		<timer 
			begin="%d" 
			end="%d"
			serviceref="1:0:1:6DD2:44D:1:C00000:0:0:0:" 
			repeated="%d" 
			name="Test Event Name" 
			description="Test Event Description" 
			afterevent="nothing" 
			eit="56422" 
			disabled="0" 
			justplay="0">
	</timer>""" % (at + timer_start, at + timer_start + timer_length, repeat)
	).childNodes[0])

	t.record(timer)

	# run virtual environment
	enigma.run(4 * 86400)
	
	print "done."
	
	timers = t.processed_timers  + t.timer_list
	
	print "start: %s" % (time.ctime(at + 10))
	
	assert len(timers) == 1
	
	for t in timers:
		print "begin=%d, end=%d, repeated=%d, state=%d" % (t.begin - at, t.end - at, t.repeated, t.state)
		print "begin: %s" % (time.ctime(t.begin))
		print "end: %s" % (time.ctime(t.end))

	# if repeat, check if the calculated repeated time of day matches the initial time of day
	if repeat:
		t_initial = time.localtime(at + timer_start)
		t_repeated = time.localtime(timers[0].begin)
		print t_initial
		print t_repeated
		
#		assert t_initial[3:6] == t_repeated[3:6], "repeated timer time of day does not match"

# required stuff for timer (we try to keep this minimal)
enigma.init_nav()
enigma.init_record_config()
enigma.init_parental_control()


import FakeNotifications
sys.modules["Notifications"] = FakeNotifications

from events import log

import calendar


import os
# we are operating in CET/CEST
os.environ['TZ'] = 'CET'
time.tzset()

log(test_timer, base_time = calendar.timegm((2007, 3, 24, 12, 0, 0)), repeat=0x7f)
#log(test_timer, base_time = calendar.timegm((2007, 03, 20, 0, 0, 0)), repeat=0x7f)
