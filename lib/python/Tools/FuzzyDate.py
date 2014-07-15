from time import localtime, time

def FuzzyTime(t, inPast = False):
	d = localtime(t)
	nt = time()
	n = localtime()
	dayOfWeek = (_("Mon"), _("Tue"), _("Wed"), _("Thu"), _("Fri"), _("Sat"), _("Sun"))

	if d[:3] == n[:3]:
		# same day
		date = _("Today")
	elif d[0] == n[0] and d[7] == n[7] - 1 and inPast:
		# won't work on New Year's day
		date = _("Yesterday")
	elif ((t - nt) < 7*86400) and (nt < t) and not inPast:
		# same week (must be future)
		date = dayOfWeek[d[6]]
	elif d[0] == n[0]:
		# same year
		if inPast:
			# I want the day in the movielist
			date = "%s %02d.%02d." % (dayOfWeek[d[6]], d[2], d[1])
		else:
			date = "%02d.%02d." % (d[2], d[1])
	else:
		date = "%02d.%02d.%d" % (d[2], d[1], d[0])

	timeres = "%02d:%02d" % (d[3], d[4])

	return date, timeres

if __name__ == "__main__":
	def _(x): return x
	print "now: %s %s" % FuzzyTime(time())
	for i in range(1, 14):
		print "+%2s day(s):  %s " % (i, FuzzyTime(time() + 86400 * i))
	for i in range(1, 14):
		print "-%2s day(s):  %s " % (i, FuzzyTime(time() - 86400 * i, True))
