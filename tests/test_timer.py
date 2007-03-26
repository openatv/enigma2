import enigma

import RecordTimer

t = RecordTimer.RecordTimer()

# generate a timer to test
import xml.dom.minidom

timer = RecordTimer.createTimer(xml.dom.minidom.parseString(
"""
	<timer 
		begin="10" 
		end="200"
		serviceref="1:0:1:6DD2:44D:1:C00000:0:0:0:" 
		repeated="0" 
		name="Test Event Name" 
		description="Test Event Description" 
		afterevent="nothing" 
		eit="56422" 
		disabled="0" 
		justplay="0">
</timer>""").childNodes[0])

t.record(timer)

# run virtual environment
enigma.run()
