from enigma import *

def test():
	ref = eServiceReference("4097:47:0:0:0:0:0:0:0:0:/sine_60s_100.mp3");
	
	sc = eServiceCenterPtr()
	print sc
	
	if eServiceCenter.getInstance(sc):
		print "no eServiceCenter instance!"
	else:
		print "now trying to play!"
		i = iPlayableServicePtr();
		if sc.play(ref, i):
			print "play failed! :("
		else:
			print "play ruled!"
			
			p = iPauseableServicePtr()
			if (i.getIPausableService(p)):
				print "no pause available"
			else:
				p.pause()
				p.unpause()
	
	return 0
