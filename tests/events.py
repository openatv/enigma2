import time

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

def end_log():
	global base_time
	for (t, self, method, args, kwargs) in get_events():
		print "%s T+%f: %s::%s(%s, *%s, *%s)"  % (time.ctime(t), t - base_time, str(self.__class__), method, self, args, kwargs)

def log(fnc, base_time = 0, *args, **kwargs):
	import fake_time
	fake_time.setTime(base_time)

	start_log()
	fnc(*args, **kwargs)
	end_log()
