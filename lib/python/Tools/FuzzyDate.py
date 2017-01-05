from Components.config import config
from time import localtime, time, strftime

def FuzzyTime(t, inPast=False):
	d = localtime(t)
	nt = time()
	n = localtime(nt)

	if d[:3] == n[:3]:
		# same day
		date = _("Today")
	elif d[0] == n[0] and d[7] == n[7] - 1 and inPast:
		# won't work on New Year's day
		date = _("Yesterday")
	elif ((t - nt) < 7 * 86400) and (nt < t) and not inPast:
		# same week (must be future)
		date = strftime("%a", d)
	elif d[0] == n[0]:
		# same year
		if inPast:
			# I want the day in the movielist
			date = strftime(config.usage.date.dayshort.value, d)
		else:
			date = strftime(config.usage.date.short.value, d)
	else:
		date = strftime(config.usage.date.long.value, d)

	timeres = strftime(config.usage.time.short.value, d)

	return date, timeres

if __name__ == "__main__":
	def _(x): return x
	print "now: %s %s" % FuzzyTime(time())
	for i in range(1, 14):
		print "+%2s day(s):  %s " % (i, FuzzyTime(time() + 86400 * i))
	for i in range(1, 14):
		print "-%2s day(s):  %s " % (i, FuzzyTime(time() - 86400 * i, True))
