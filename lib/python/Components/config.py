from time import *
from Tools.NumericalTextInput import *
from Tools.Directories import *

class configFile:
	def __init__(self):
		self.changed = 0
		self.configElements = { }
		try:
			self.file = open(resolveFilename(SCOPE_CONFIG, "config"))
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
			self.configElements[line[:x]] = line[x + 1:-1]

	def getKey(self, key):
		return self.configElements[key]

	def setKey(self, key, value, isDefaultKey=False):
		self.changed = 1
		if isDefaultKey and self.configElements.has_key(key):
			del self.configElements[key]
		else:
			self.configElements[key] = value

	def getResolvedKey(self, key):
		str = self.configElements[key]
		if len(str):
			pos = str.find('*')
			if pos != -1:
				str = str[pos+1:]
				pos = str.find('*')
				if pos != -1:
					return str[:pos]
			return str
		return None

	def save(self):
		if self.changed == 0:		#no changes, so no write to disk needed
			return
			
		fileHandle = open(resolveFilename(SCOPE_CONFIG, "config"), "w")
		
		keys = self.configElements.keys()
		keys.sort()
		for x in keys:
			wstr = x + "=" + self.configElements[x] + "\n"

			fileHandle.write(wstr)

		fileHandle.close()
		
def currentConfigSelectionElement(element):
	return element.vals[element.value][0]

def getConfigSelectionElement(element, value):
	count = 0
	for x in element.vals:
		if x[0] == value:
			return count
		count += 1
	return -1

class configSelection:
	def __init__(self, parent):
		self.parent = parent
		
	def checkValues(self):
		if self.parent.value < 0:
			self.parent.value = len(self.parent.vals) - 1	
		elif(self.parent.value > (len(self.parent.vals) - 1)):
			self.parent.value = 0

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

		returnValue = _(self.parent.vals[self.parent.value])
		if not isinstance(returnValue, str):
			returnValue = returnValue[1]

		# FIXME: it's not really nice to translate this here.
		# however, configSelections are persistent.
		
		# WORKAROUND: don't translate ""
		if returnValue:
			returnValue = _(returnValue)
		
		return ("text", returnValue)
		
class configDateTime:
	def __init__(self, parent):
		self.parent = parent
		
	def checkValues(self):
		pass
#		if self.parent.value < 0:
			#self.parent.value = 0	

		#if(self.parent.value >= (len(self.parent.vals) - 1)):
			#self.parent.value = len(self.parent.vals) - 1

	def cancel(self):
		self.parent.reload()

	def save(self):
		self.parent.save()

	def handleKey(self, key):
		if key == config.key["prevElement"]:
			self.parent.value = self.parent.value - self.parent.vals[1]
		if key == config.key["nextElement"]:
			self.parent.value = self.parent.value + self.parent.vals[1]
		
		self.checkValues()

		self.parent.change()	

	def __call__(self, selected):			#needed by configlist
		self.checkValues()
		return ("text", strftime(self.parent.vals[0], localtime(self.parent.value)))
	
class configSatlist:
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
		#fixme
		return ("text", str(self.parent.vals[self.parent.value][0]))

class configSequenceArg:
	def get(self, type, args = ()):
		# configsequencearg.get ("IP")
		if (type == "IP"):
			return (("."), [(0,255),(0,255),(0,255),(0,255)], "")
		# configsequencearg.get ("MAC")
		if (type == "MAC"):
			return ((":"), [(1,255),(1,255),(1,255),(1,255),(1,255),(1,255)], "")
		# configsequencearg.get ("CLOCK")
		if (type == "CLOCK"):
			return ((":"), [(0,23),(0,59)], "")
		# configsequencearg.get("INTEGER", (min, max)) => x with min <= x <= max
		if (type == "INTEGER"):
			return ((":"), [args], "")
		# configsequencearg.get("PINCODE", (number, "*")) => pin with number = length of pincode and "*" as numbers shown as stars
		# configsequencearg.get("PINCODE", (number, "")) => pin with number = length of pincode and numbers shown
		if (type == "PINCODE"):
			return ((":"), [(0, (10**args[0])-1)], args[1])
		# configsequencearg.get("FLOAT", [(min,max),(min1,max1)]) => x.y with min <= x <= max and min1 <= y <= max1
		if (type == "FLOAT"):
			return (("."), args, "")
		
	def getFloat(self, element):
		return float(("%d.%0" + str(len(str(element.vals[1][1][1]))) + "d") % (element.value[0], element.value[1]))

configsequencearg = configSequenceArg()
		
class configSequence:
	def __init__(self, parent):
		self.parent = parent
		self.markedPos = 0
		self.seperator = self.parent.vals[0]
		self.valueBounds = self.parent.vals[1]
		self.censorChar = self.parent.vals[2]

	def checkValues(self):
		maxPos = 0
		num = 0
		for i in self.parent.value:
			maxPos += len(str(self.valueBounds[num][1]))
			while (self.valueBounds[num][0] > self.parent.value[num]):
				self.parent.value[num] += 1

			while (self.valueBounds[num][1] < self.parent.value[num]):
				self.parent.value[num] -= 1
				
#			if (self.valueBounds[num][0] <= i <= self.valueBounds[num][1]):
				#pass
			#else:
				#self.parent.value[num] = self.valueBounds[num][0]
			num += 1
		
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
			self.blockLen = []
			for x in self.valueBounds:
				self.blockLen.append(len(str(x[1])))
				
			pos = 0
			blocknumber = 0
			self.blockLenTotal = [0,]
			for x in self.blockLen:
				pos += self.blockLen[blocknumber]
				self.blockLenTotal.append(pos)
				if (pos - 1 >= self.markedPos):
					pass
				else:
					blocknumber += 1
					
			number = 9 - config.key["9"] + key
			# length of numberblock
			numberLen = len(str(self.valueBounds[blocknumber][1]))
			# position in the block
			posinblock = self.markedPos - self.blockLenTotal[blocknumber]
			
			oldvalue = self.parent.value[blocknumber]
			olddec = oldvalue % 10 ** (numberLen - posinblock) - (oldvalue % 10 ** (numberLen - posinblock - 1))
			newvalue = oldvalue - olddec + (10 ** (numberLen - posinblock - 1) * number)
			
			self.parent.value[blocknumber] = newvalue
			self.markedPos += 1
		
		self.checkValues()

		#FIXME: dont call when press left/right
		self.parent.change()	

	def __call__(self, selected):			#needed by configlist
		value = ""
		mPos = self.markedPos
		num = 0;
		for i in self.parent.value:
			if len(value):	#fixme no heading separator possible
				value += self.seperator
				if mPos >= len(value) - 1:
					mPos += 1
				
			#diff = 	self.valueBounds - len(str(i))
			#if diff > 0:
				## if this helps?!
				#value += " " * diff
			if (self.censorChar == ""):
				value += ("%0" + str(len(str(self.valueBounds[num][1]))) + "d") % i
			else:
				value += (self.censorChar * len(str(self.valueBounds[num][1])))
			num += 1
			# only mark cursor when we are selected
			# (this code is heavily ink optimized!)
		if (self.parent.enabled == True):
			return ("mtext"[1-selected:], value, [mPos])
		else:
			return ("text", value)

class configNothing:
	def __init__(self, parent):
		self.parent = parent
		self.markedPos = 0

	def cancel(self):
		self.parent.reload()

	def save(self):
		self.parent.save()
		
	def nextEntry(self):
		self.parent.vals[1](self.parent.getConfigPath())

	def handleKey(self, key):
		pass

	def __call__(self, selected):			#needed by configlist
		return ("text", "")

class configText:
	# used as first parameter
	# is the text of a fixed size or is the user able to extend the length of the text
	extendableSize = 1
	fixedSize = 2

	def __init__(self, parent):
		self.parent = parent
		self.markedPos = 0
		self.mode = self.parent.vals[0]
		self.textInput = NumericalTextInput(self.nextEntry)

	def checkValues(self):
		if (self.markedPos < 0):
			self.markedPos = 0
		if (self.markedPos >= len(self.parent.value)):
			self.markedPos = len(self.parent.value) - 1
			
	def cancel(self):
		self.parent.reload()

	def save(self):
		self.parent.save()
		
	def nextEntry(self):
		self.parent.vals[1](self.parent.getConfigPath())

	def handleKey(self, key):
		#this will no change anything on the value itself
		#so we can handle it here in gui element
		if key == config.key["delete"]:
			self.parent.value = self.parent.value[0:self.markedPos] + self.parent.value[self.markedPos + 1:]
		if key == config.key["prevElement"]:
			self.textInput.nextKey()
			self.markedPos -= 1

		if key == config.key["nextElement"]:
			self.textInput.nextKey()
			self.markedPos += 1
			if (self.mode == self.extendableSize):
				if (self.markedPos >= len(self.parent.value)):
					self.parent.value = self.parent.value.ljust(len(self.parent.value) + 1)
			
				
		if key >= config.key["0"] and key <= config.key["9"]:
			number = 9 - config.key["9"] + key

			self.parent.value = self.parent.value[0:self.markedPos] + str(self.textInput.getKey(number)) + self.parent.value[self.markedPos + 1:]
		
		self.checkValues()			
		
		self.parent.change()	

	def __call__(self, selected):			#needed by configlist
		return ("mtext"[1-selected:], str(self.parent.value), [self.markedPos])
		
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
					 "delete": 3,
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

class configSlider:
	def __init__(self, parent):
		self.parent = parent

	def cancel(self):
		self.parent.reload()

	def save(self):
		self.parent.save()

	def checkValues(self):
		if self.parent.value < 0:
			self.parent.value = 0	

		if self.parent.value > self.parent.vals[1]:
			self.parent.value = self.parent.vals[1]

	def handleKey(self, key):
		if key == config.key["prevElement"]:
			self.parent.value = self.parent.value - self.parent.vals[0]
		if key == config.key["nextElement"]:
			self.parent.value = self.parent.value + self.parent.vals[0]
					
		self.checkValues()	
		self.parent.change()	

	def __call__(self, selected):			#needed by configlist
		self.checkValues()
		return ("slider", self.parent.value, self.parent.vals[1])

class ConfigSubsection:
	def __init__(self):
		pass

class configElement:

	def getIndexbyEntry(self, data):
		cnt = 0;
		tcnt = -1; #for defaultval
		for x in self.vals:
			if int(x[1]) == int(data):
					return cnt
			if int(x[1]) == int(self.defaultValue):
					tcnt = cnt
			cnt += 1
		if tcnt != -1:
			return tcnt
		return 0	#prevent bigger then array

	def datafromFile(self, control, data):
		if control == configSlider:
			return int(data)
		elif control == configSelection:
			try:
				return int(data)
			except:
				for x in data.split(":"):
					if x[0] == "*":
						count = 0
						for y in self.vals:
							if y[0] == x[1:-1]:
								return count
							count += 1
				return self.defaultValue
		elif control == configDateTime:
			return int(data)
		elif control == configText:
			return str(data)
		elif control == configSequence:
			list = [ ]
			part = data.split(self.vals[0])
			for x in part:
				list.append(int(x))
			return list
		elif control == configSatlist:
			return self.getIndexbyEntry(data)
		else: 
			return ""	

	def datatoFile(self, control, data):
		if control == configSlider:
			return str(data)
		elif control == configSelection:
			if len(self.vals) < data + 1:
				return "0"
			if isinstance(self.vals[data], str):
				return str(data)
			else:
				confList = []
				count = 0
				for x in self.vals:
					if count == data:
						confList.append("*" + str(x[0] + "*"))
					else:
						confList.append(x[0])
					count += 1
				return ":".join(confList)
			return str(data)
		elif control == configDateTime:
			return str(data)
		elif control == configText:
			return str(data.strip())
		elif control == configSequence:
#			print self.vals
#			print self.value
			try:
				value = ""
				count = 0
				for i in data:
					if value !="":
						value += self.vals[0]
					value += (("%0" + str(len(str(self.vals[1][count][1]))) + "d") % i)
					count += 1
					#value = ((len(data) * ("%d" + self.vals[0]))[0:-1]) % tuple(data)
			except:	
				value = str(data)	
			return value
		elif control == configSatlist:
			return str(self.vals[self.value][1]);
		else: 
			return ""	

	def loadData(self):
		#print "load:" + self.configPath
		try:
			value = self.datafromFile(self.controlType, configfile.getKey(self.configPath))
		except:		
			value = ""

		if value == "":
			#print "value not found - using default"
			if self.controlType == configSatlist:
				self.value = self.getIndexbyEntry(self.defaultValue)
			elif self.controlType == configSequence:
				self.value = self.defaultValue[:]
			else:
				self.value = self.defaultValue

			self.save()		#add missing value to dict
		else:
			#print "set val:" + str(value)
			self.value = value

		#is this right? activate settings after load/cancel and use default	
		self.change()

	def __init__(self, configPath, control, defaultValue, vals, saveDefaults = True):
		self.configPath = configPath
		self.defaultValue = defaultValue
		self.controlType = control
		self.vals = vals
		self.notifierList = [ ]
		self.enabled = True
		self.saveDefaults = saveDefaults
		self.loadData()		
		
	def getConfigPath(self):
		return self.configPath
	
	def addNotifier(self, notifier):
		self.notifierList.append(notifier);
		notifier(self);

	def change(self):
		for notifier in self.notifierList:
			notifier(self)

	def reload(self):
		self.loadData()

	def save(self):
		if self.controlType == configSatlist:
			defaultValue = self.getIndexbyEntry(self.defaultValue)
		else:
			defaultValue = self.defaultValue
		if self.value != defaultValue or self.saveDefaults:
			configfile.setKey(self.configPath, self.datatoFile(self.controlType, self.value))
		else:
			try:
				oldValue = configfile.getKey(self.configPath)
			except:
				oldValue = None
			if oldValue is not None and oldValue != defaultValue:
				configfile.setKey(self.configPath, self.datatoFile(self.controlType, self.value), True)

class configElement_nonSave(configElement):
	def __init__(self, configPath, control, defaultValue, vals):
		configElement.__init__(self, configPath, control, defaultValue, vals)

	def save(self):
		pass

def getConfigListEntry(description, element):
	b = element
	item = b.controlType(b)
	return ((description, item))

def configElementBoolean(name, default, texts=(_("Enable"), _("Disable"))):
	return configElement(name, configSelection, default, texts)

config.misc = ConfigSubsection()
