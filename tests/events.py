import time
import tests

recorded_events = [ ]

def event(self, name, args, kwargs):
	global recorded_events
	print "*EVENT*", time.time(), self, name, args, kwargs
	recorded_events.append((time.time(), self, name, args, kwargs))

def eventfnc(f):
	name = f.__name__
	def wrapper(self, *args, **kwargs):
		event(self, name, args, kwargs)
		return f(self, *args, **kwargs)
	return wrapper

def get_events():
	global recorded_events
	r = recorded_events
	recorded_events = [ ]
	return r

def start_log():
	global base_time
	base_time = time.time()

def end_log(test_name):
	global base_time

	results = ""

	for (t, self, method, args, kwargs) in get_events():
		results += "%s T+%f: %s::%s(%s, *%s, *%s)\n"  % (time.ctime(t), t - base_time, str(self.__class__), method, self, args, kwargs)

	expected = None

	try:
		f = open(test_name + ".results", "rb")
		expected = f.read()
		f.close()
	except:
		print "NO TEST RESULT FOUND, creating new"
		f = open(test_name + ".new_results", "wb")
		f.write(results)
		f.close()

	print results

	if expected is not None:
		print "expected:"
		if expected != results:
			f = open(test_name + ".bogus_results", "wb")
			f.write(results)
			f.close()
			raise tests.TestError("test data does not match")
		else:
			print "test compared ok"
	else:
		print "no test data to compare with."

def log(fnc, base_time = 0, test_name = "test", *args, **kwargs):
	import fake_time
	fake_time.setTime(base_time)

	start_log()
	try:
		fnc(*args, **kwargs)
		event(None, "test_completed", [], {"test_name": test_name})
	except tests.TestError,c:
		event(None, "test_failed", [], {"test_name": test_name, "reason": str(c)})
	end_log(test_name)
