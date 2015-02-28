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
		date = strftime("%a %d %b", d)
	else:
		date = strftime("%d %b %Y", d)

	timeres = strftime("%R", d)

	return date, timeres

if __name__ == "__main__":
	def _(x):
		return x

	for i in [365] + range(14, 0, -1):
		print "%+4.0d day(s): %s" % (i, FuzzyTime(time() + 86400 * i))
	print "        now: %s" % str(FuzzyTime(time()))
	for i in range(1, 14) + [365]:
		print "%+4.0d day(s): %s" % (-i, FuzzyTime(time() - 86400 * i, True))
