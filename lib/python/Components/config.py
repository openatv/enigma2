class configFile:
	def __init__(self):
		self.changed = 0
		self.configElements = { }
		try:
			self.file = open("config")
		except IOError:
			print "cannot open config file"
			return 
		
		while 1:
			line = self.file.readline()
			if line == "":
				break
			
			if line.startswith("#"):		#skip comments
				continue	
				
			self.addElement(line)
		self.file.close()

	def addElement(self, line):
		x = line.find("=")
		if x > -1:
			self.configElements[line[:x]] = line[x + 1:]
	
	def getKey(self, key):
		return self.configElements[key]

	def setKey(self, key, value):
		self.changed = 1
		self.configElements[key] = value

	def save(self):
		if self.changed == 0:		#no changes, so no write to disk needed
			return
			
		fileHandle = open("config", "w")
		
		for x in self.configElements:
			wstr = x + "=" + self.configElements[x]
			
			if wstr[len(wstr) - 1] != '\n':
				wstr = wstr + "\n"

			fileHandle.write(wstr)

		fileHandle.close()		

class configSelection:
	def __init__(self, parent):
		self.parent = parent
		
	def checkValues(self):
		if self.parent.value < 0:
			self.parent.value = 0	

		if(self.parent.value >= (len(self.parent.vals) - 1)):
			self.parent.value = len(self.parent.vals) - 1

	def cancel(self):
		self.parent.reload()

	def save(self):
		self.parent.save()

	def handleKey(self, key):
		if key == config.key["prevElement"]:
			self.parent.value = self.parent.value - 1
		if key == config.key["nextElement"]:
			self.parent.value = self.parent.value + 1
		
		self.checkValues()			

		self.parent.change()	

	def __call__(self, selected):			#needed by configlist
		self.checkValues()
		return ("text", self.parent.vals[self.parent.value])

class configSatlist:
	def __init__(self, parent):
		self.parent = parent

	def checkValues(self):
		if self.parent.value < 0:
			self.parent.value = 0	

		if(self.parent.value >= (len(self.parent.vals) - 1)):
			self.parent.value = len(self.parent.vals) - 1
			
		print "value" + str(self.parent.value)
		print "name " + self.parent.vals[self.parent.value][0]

	def cancel(self):
		self.parent.reload()

	def save(self):
		self.parent.save()

	def handleKey(self, key):
		if key == config.key["prevElement"]:
			self.parent.value = self.parent.value - 1
		if key == config.key["nextElement"]:
			self.parent.value = self.parent.value + 1
		
		self.checkValues()			

		self.parent.change()	

	def __call__(self, selected):			#needed by configlist
		self.checkValues()
		#fixme
		return ("text", str(self.parent.vals[self.parent.value][0]))
		
class configSequence:
	def __init__(self, parent):
		self.parent = parent
		self.markedPos = 0
		
	def checkValues(self):
		maxPos = len(self.parent.value) * self.parent.vals[1] 
		print maxPos
			
		if self.markedPos >= maxPos:
			self.markedPos = maxPos - 1
		if self.markedPos < 0:
			self.markedPos = 0
			
	def cancel(self):
		self.parent.reload()

	def save(self):
		self.parent.save()

	def handleKey(self, key):
		#this will no change anything on the value itself
		#so we can handle it here in gui element
		if key == config.key["prevElement"]:
			self.markedPos -= 1
		if key == config.key["nextElement"]:
			self.markedPos += 1
		
		if key >= config.key["0"] and key <= config.key["9"]:
			number = 9 - config.key["9"] + key
			# length of numberblock
			numberLen = len(str(self.parent.vals[1][1]))
			# position in the block
			posinblock = self.markedPos % numberLen
			# blocknumber
			blocknumber = self.markedPos / numberLen
			
			oldvalue = self.parent.value[blocknumber]
			olddec = oldvalue % 10 ** (numberLen - posinblock) - (oldvalue % 10 ** (numberLen - posinblock - 1))
			newvalue = oldvalue - olddec + (10 ** (numberLen - posinblock - 1) * number)
			
			print "You actually pressed a number (" + str(number) + ") which will be added at block number " + str(blocknumber) + " on position " + str(posinblock)
			print "Old value: " + str(oldvalue) + " olddec: " + str(olddec) + " newvalue: " + str(newvalue)
			self.parent.value[blocknumber] = newvalue
			self.markedPos += 1
		
		self.checkValues()			
		
		print "markPos:",
		print self.markedPos

		#FIXME: dont call when press left/right
		self.parent.change()	

	def __call__(self, selected):			#needed by configlist
		value = ""
		mPos = self.markedPos
		print "Positon: " + str(mPos)
		for i in self.parent.value:
			if len(value):	#fixme no heading separator possible
				value += self.parent.vals[0]
				if mPos >= len(value) - 1:
					mPos += 1
				
			#diff = 	self.parent.vals[1] - len(str(i))
			#if diff > 0:
				## if this helps?!
				#value += " " * diff
			print (("%0" + str(len(str(self.parent.vals[1][1]))) + "d") % i)
			value += ("%0" + str(len(str(self.parent.vals[1][1]))) + "d") % i

			# only mark cursor when we are selected
			# (this code is heavily ink optimized!)
		return ("mtext"[1-selected:], value, [mPos])

class configValue:
	def __init__(self, obj):
		self.obj = obj
		
	def __str__(self):
		return self.obj

class Config:
	def __init__(self):
		self.key = { "choseElement": 0,
					 "prevElement": 1,
					 "nextElement": 2,
					 "0": 10,
					 "1": 11,
					 "2": 12,
					 "3": 13,
					 "4": 14,
					 "5": 15,
					 "6": 16,
					 "7": 17,
					 "8": 18,
					 "9": 19 }
		
config = Config();
configfile = configFile()

class ConfigSlider:
	def __init__(self, parent):
		self.parent = parent

	def cancel(self):
		self.parent.reload()

	def save(self):
		self.parent.save()

	def checkValues(self):
		if self.parent.value < 0:
			self.parent.value = 0	

		if self.parent.value > 10:
			self.parent.value = 10	

	def handleKey(self, key):
		if key == config.key["prevElement"]:
			self.parent.value = self.parent.value - 1
		if key == config.key["nextElement"]:
			self.parent.value = self.parent.value + 1
					
		self.checkValues()	
		self.parent.change()	

	def __call__(self, selected):			#needed by configlist
		self.checkValues()
		return ("slider", self.parent.value * 10)

class ConfigSubsection:
	def __init__(self):
		pass

class configElement:
	def datafromFile(self, control, data):
		if control == ConfigSlider:
			return int(data);
		elif control == configSelection:
			return int(data);
		elif control == configSequence:
			list = [ ]
			part = data.split(self.vals[0])
			for x in part:
				list.append(int(x))
			return list
		else: 
			return ""	

	def datatoFile(self, control, data):
		if control == ConfigSlider:
			return str(data);
		elif control == configSelection:
			return str(data);
		elif control == configSequence:
			value = ((len(data) * ("%d" + self.vals[0]))[0:-1]) % tuple(data)
#			just in case you don't understand the above, here an equivalent:
#			value = ""
#			for i in data:
#				if value !="":
#					value += self.vals[0]
#				value += str(i)
			return value
		else: 
			return ""	

	def loadData(self):
		try:
			value = self.datafromFile(self.controlType, configfile.getKey(self.configPath))
		except:		
			value = ""

		if value == "":
			print "value not found - using default"
			self.value = self.defaultValue
			self.save()		#add missing value to dict
		else:
			self.value = value

	def __init__(self, configPath, control, defaultValue, vals):
		self.configPath = configPath
		self.defaultValue = defaultValue
		self.controlType = control
		self.vals = vals
		self.notifierList = [ ]
		self.enabled = True
		self.loadData()		
	def addNotifier(self, notifier):
		self.notifierList.append(notifier);
		notifier(self);
	def change(self):
		for notifier in self.notifierList:
			notifier(self)
	def reload(self):
		self.loadData()
	def save(self):
		configfile.setKey(self.configPath, self.datatoFile(self.controlType,self.value))
