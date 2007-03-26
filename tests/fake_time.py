import time

real_time = time.time

time_offset = real_time()

def my_time():
	return real_time() - time_offset

time.time = my_time
