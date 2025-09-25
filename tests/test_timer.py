import time

import enigma
import tests


#enigma.reset()
def test_timer(repeat=0, timer_start=3600, timer_length=1000, sim_length=86400 * 7):

	import NavigationInstance

	at = time.time()

	t = NavigationInstance.instance.RecordTimer
	print(t)
	print("old mwt:", t.MaxWaitTime)
	t.MaxWaitTime = 86400 * 1000

	t.processed_timers = []
	t.timer_list = []

	# generate a timer to test
	import xml.etree.cElementTree
	import RecordTimer

	timer = RecordTimer.createTimer(xml.etree.cElementTree.fromstring(
	f"""
\t\t<timer
\t\t\tbegin="{at + timer_start}"
\t\t\tend="{at + timer_start + timer_length}"
\t\t\tserviceref="1:0:1:6DD2:44D:1:C00000:0:0:0:"
\t\t\trepeated="{repeat}"
\t\t\tname="Test Event Name"
\t\t\tdescription="Test Event Description"
\t\t\tafterevent="nothing"
\t\t\teit="56422"
\t\t\tdisabled="0"
\t\t\tjustplay="0">
\t</timer>"""
	))

	t.record(timer)

	# run virtual environment
	enigma.run(sim_length)

	print("done.")

	timers = t.processed_timers + t.timer_list

	print(f"start: {time.ctime(at + 10)}")

	assert len(timers) == 1

	for t in timers:
		print(f"begin={t.begin - at}, end={t.end - at}, repeated={t.repeated}, state={t.state}")
		print(f"begin: {time.ctime(t.begin)}")
		print(f"end: {time.ctime(t.end)}")

	# if repeat, check if the calculated repeated time of day matches the initial time of day
	if repeat:
		t_initial = time.localtime(at + timer_start)
		t_repeated = time.localtime(timers[0].begin)
		print(t_initial)
		print(t_repeated)

	if t_initial[3:6] != t_repeated[3:6]:
		raise tests.TestError("repeated timer time of day does not match")

#sys.modules["Tools.Notifications"] = FakeNotifications
#sys.modules["Tools.NumericalTextInput.NumericalTextInput"] = FakeNotifications


# required stuff for timer (we try to keep this minimal)
enigma.init_nav()
enigma.init_record_config()
enigma.init_parental_control()


from events import log  # noqa: E402

import calendar  # noqa: E402


import os  # noqa: E402
# we are operating in CET/CEST
os.environ['TZ'] = 'CET'
time.tzset()

#log(test_timer, test_name = "test_timer_repeating", base_time = calendar.timegm((2007, 3, 1, 12, 0, 0)), repeat=0x7f, sim_length = 86400 * 7)
log(test_timer, test_name="test_timer_repeating_dst_skip", base_time=calendar.timegm((2007, 0o3, 20, 0, 0, 0)), timer_start=3600, repeat=0x7f, sim_length=86400 * 7)
#log(test_timer, test_name = "test_timer_repeating_dst_start", base_time = calendar.timegm((2007, 03, 20, 0, 0, 0)), timer_start = 10000, repeat=0x7f, sim_length = 86400 * 7)
