import time
from enigma import getPrevAsciiCode
from Tools.NumericalTextInput import NumericalTextInput
from Tools.Directories import resolveFilename, SCOPE_CONFIG
import copy


# ConfigElement, the base class of all ConfigElements.

# it stores:
#   value    the current value, usefully encoded.
#            usually a property which retrieves _value,
#            and maybe does some reformatting
#   _value   the value as it's going to be saved in the configfile,
#            though still in non-string form.
#            this is the object which is actually worked on.
#   default  the initial value. If _value is equal to default,
#            it will not be stored in the config file
#   saved_value is a text representation of _value, stored in the config file
#
# and has (at least) the following methods:
#   save()   stores _value into saved_value, 
#            (or stores 'None' if it should not be stored)
#   load()   loads _value from saved_value, or loads
#            the default if saved_value is 'None' (default)
#            or invalid.
#
class ConfigElement(object):
	def __init__(self):

		object.__init__(self)
		self.saved_value = None
		self.save_disabled = False
		self.notifiers = []
		self.enabled = True

	# you need to override this to do input validation
	def setValue(self, value):
		self._value = value
		self.changed()

	def getValue(self):
		return self._value
	
	value = property(getValue, setValue)

	# you need to override this if self.value is not a string
	def fromstring(self, value):
		return value

	# you can overide this for fancy default handling
	def load(self):
		if self.saved_value is None:
			self.value = self.default
		else:
			self.value = self.fromstring(self.saved_value)

	def tostring(self, value):
		return str(value)

	# you need to override this if str(self.value) doesn't work
	def save(self):
		if self.save_disabled or self.value == self.default:
			self.saved_value = None
		else:
			self.saved_value = self.tostring(self.value)

	def cancel(self):
		self.load()

	def isChanged(self):
		if self.saved_value is None and self.value == self.default:
			return False
		return self.tostring(self.value) != self.saved_value

	def changed(self):
		for x in self.notifiers:
			x(self)
			
	def addNotifier(self, notifier, initial_call = True):
		assert callable(notifier), "notifiers must be callable"
		self.notifiers.append(notifier)

		# CHECKME:
		# do we want to call the notifier
		#  - at all when adding it? (yes, though optional)
		#  - when the default is active? (yes)
		#  - when no value *yet* has been set,
		#    because no config has ever been read (currently yes)
		#    (though that's not so easy to detect.
		#     the entry could just be new.)
		if initial_call:
			notifier(self)

	def disableSave(self):
		self.save_disabled = True

	def __call__(self, selected):
		return self.getMulti(selected)

	def onSelect(self, session):
		pass

	def onDeselect(self, session):
		pass

KEY_LEFT = 0
KEY_RIGHT = 1
KEY_OK = 2
KEY_DELETE = 3
KEY_BACKSPACE = 4
KEY_HOME = 5
KEY_END = 6
KEY_TOGGLEOW = 7
KEY_ASCII = 8
KEY_TIMEOUT = 9
KEY_NUMBERS = range(12, 12+10)
KEY_0 = 12
KEY_9 = 12+9

def getKeyNumber(key):
	assert key in KEY_NUMBERS
	return key - KEY_0

#
# ConfigSelection is a "one of.."-type.
# it has the "choices", usually a list, which contains
# (id, desc)-tuples (or just only the ids, in case the id
# will be used as description)
#
# all ids MUST be plain strings.
#
class ConfigSelection(ConfigElement):
	def __init__(self, choices, default = None):
		ConfigElement.__init__(self)
		self._value = None
		self.setChoices(choices, default)

	def setChoices(self, choices, default = None):
		self.choices = []
		self.description = {}
		
		if isinstance(choices, list):
			for x in choices:
				if isinstance(x, tuple):
					self.choices.append(x[0])
					self.description[x[0]] = x[1]
				else:
					self.choices.append(x)
					self.description[x] = x
		elif isinstance(choices, dict):
			for (key, val) in choices.items():
				self.choices.append(key)
				self.description[key] = val
		else:
			assert False, "ConfigSelection choices must be dict or list!"
		
		#assert len(self.choices), "you can't have an empty configselection"
		if len(self.choices) == 0:
			self.choices = [""]
			self.description[""] = ""

		if default is None:
			default = self.choices[0]

		assert default in self.choices, "default must be in choice list, but " + repr(default) + " is not!"
		for x in self.choices:
			assert isinstance(x, str), "ConfigSelection choices must be strings"
		
		self.default = default

		if self.value == None or not self.value in self.choices:
			self.value = default

	def setValue(self, value):
		if value in self.choices:
			self._value = value
		else:
			self._value = self.default
		
		self.changed()

	def tostring(self, val):
		return val

	def getValue(self):
		return self._value

	def setCurrentText(self, text):
		i = self.choices.index(self.value)
		del self.description[self.choices[i]]
		self.choices[i] = text
		self.description[text] = text
		self._value = text

	value = property(getValue, setValue)
	
	def getIndex(self):
		return self.choices.index(self.value)
	
	index = property(getIndex)

	# GUI
	def handleKey(self, key):
		nchoices = len(self.choices)
		i = self.choices.index(self.value)
		if key == KEY_LEFT:
			self.value = self.choices[(i + nchoices - 1) % nchoices]
		elif key == KEY_RIGHT:
			self.value = self.choices[(i + 1) % nchoices]
		elif key == KEY_HOME:
			self.value = self.choices[0]
		elif key == KEY_END:
			self.value = self.choices[nchoices - 1]

	def getText(self):
		descr = self.description[self.value]
		if len(descr):
			return _(descr)
		return descr

	def getMulti(self, selected):
		descr = self.description[self.value]
		if len(descr):
			return ("text", _(descr))
		return ("text", descr)

	# HTML
	def getHTML(self, id):
		res = ""
		for v in self.choices:
			if self.value == v:
				checked = 'checked="checked" '
			else:
				checked = ''
			res += '<input type="radio" name="' + id + '" ' + checked + 'value="' + v + '">' + self.description[v] + "</input></br>\n"
		return res;

	def unsafeAssign(self, value):
		# setValue does check if value is in choices. This is safe enough.
		self.value = value

# a binary decision.
#
# several customized versions exist for different
# descriptions.
#
class ConfigBoolean(ConfigElement):
	def __init__(self, default = False, descriptions = {False: "false", True: "true"}):
		ConfigElement.__init__(self)
		self.descriptions = descriptions
		self.value = self.default = default
	def handleKey(self, key):
		if key in [KEY_LEFT, KEY_RIGHT]:
			self.value = not self.value
		elif key == KEY_HOME:
			self.value = False
		elif key == KEY_END:
			self.value = True

	def getText(self):
		descr = self.descriptions[self.value]
		if len(descr):
			return _(descr)
		return descr

	def getMulti(self, selected):
		descr = self.descriptions[self.value]
		if len(descr):
			return ("text", _(descr))
		return ("text", descr)

	def tostring(self, value):
		if not value:
			return "false"
		else:
			return "true"

	def fromstring(self, val):
		if val == "true":
			return True
		else:
			return False

	def getHTML(self, id):
		if self.value:
			checked = ' checked="checked"'
		else:
			checked = ''
		return '<input type="checkbox" name="' + id + '" value="1" ' + checked + " />"

	# this is FLAWED. and must be fixed.
	def unsafeAssign(self, value):
		if value == "1":
			self.value = True
		else:
			self.value = False

class ConfigYesNo(ConfigBoolean):
	def __init__(self, default = False):
		ConfigBoolean.__init__(self, default = default, descriptions = {False: _("no"), True: _("yes")})

class ConfigOnOff(ConfigBoolean):
	def __init__(self, default = False):
		ConfigBoolean.__init__(self, default = default, descriptions = {False: _("off"), True: _("on")})

class ConfigEnableDisable(ConfigBoolean):
	def __init__(self, default = False):
		ConfigBoolean.__init__(self, default = default, descriptions = {False: _("disable"), True: _("enable")})

class ConfigDateTime(ConfigElement):
	def __init__(self, default, formatstring, increment = 86400):
		ConfigElement.__init__(self)
		self.increment = increment
		self.formatstring = formatstring
		self.value = self.default = int(default)

	def handleKey(self, key):
		if key == KEY_LEFT:
			self.value = self.value - self.increment
		elif key == KEY_RIGHT:
			self.value = self.value + self.increment
		elif key == KEY_HOME or key == KEY_END:
			self.value = self.default

	def getText(self):
		return time.strftime(self.formatstring, time.localtime(self.value))

	def getMulti(self, selected):
		return ("text", time.strftime(self.formatstring, time.localtime(self.value)))

	def fromstring(self, val):
		return int(val)

# *THE* mighty config element class
#
# allows you to store/edit a sequence of values.
# can be used for IP-addresses, dates, plain integers, ...
# several helper exist to ease this up a bit.
#
class ConfigSequence(ConfigElement):
	def __init__(self, seperator, limits, censor_char = "", default = None):
		ConfigElement.__init__(self)
		assert isinstance(limits, list) and len(limits[0]) == 2, "limits must be [(min, max),...]-tuple-list"
		assert censor_char == "" or len(censor_char) == 1, "censor char must be a single char (or \"\")"
		#assert isinstance(default, list), "default must be a list"
		#assert isinstance(default[0], int), "list must contain numbers"
		#assert len(default) == len(limits), "length must match"

		self.marked_pos = 0
		self.seperator = seperator
		self.limits = limits
		self.censor_char = censor_char
		
		self.default = default
		self.value = copy.copy(default)
		
		self.endNotifier = []

	def validate(self):
		max_pos = 0
		num = 0
		for i in self._value:
			max_pos += len(str(self.limits[num][1]))

			while self._value[num] < self.limits[num][0]:
				self._value[num] += 1

			while self._value[num] > self.limits[num][1]:
				self._value[num] -= 1

			num += 1

		if self.marked_pos >= max_pos:
			for x in self.endNotifier:
				x(self)
			self.marked_pos = max_pos - 1

		if self.marked_pos < 0:
			self.marked_pos = 0

	def validatePos(self):
		if self.marked_pos < 0:
			self.marked_pos = 0
			
		total_len = sum([len(str(x[1])) for x in self.limits])

		if self.marked_pos >= total_len:
			self.marked_pos = total_len - 1
			
	def addEndNotifier(self, notifier):
		self.endNotifier.append(notifier)

	def handleKey(self, key):
		if key == KEY_LEFT:
			self.marked_pos -= 1
			self.validatePos()

		if key == KEY_RIGHT:
			self.marked_pos += 1
			self.validatePos()
		
		if key == KEY_HOME:
			self.marked_pos = 0
			self.validatePos()

		if key == KEY_END:
			max_pos = 0
			num = 0
			for i in self._value:
				max_pos += len(str(self.limits[num][1]))
				num += 1
			self.marked_pos = max_pos - 1
			self.validatePos()
		
		if key in KEY_NUMBERS or key == KEY_ASCII:
			if key == KEY_ASCII:
				code = getPrevAsciiCode()
				if code < 48 or code > 57:
					return
				number = code - 48
			else:
				number = getKeyNumber(key)
			
			block_len = []
			for x in self.limits:
				block_len.append(len(str(x[1])))
			
			total_len = sum(block_len)

			pos = 0
			blocknumber = 0
			block_len_total = [0, ]
			for x in block_len:
				pos += block_len[blocknumber]
				block_len_total.append(pos)
				if pos - 1 >= self.marked_pos:
					pass
				else:
					blocknumber += 1

			# length of numberblock
			number_len = len(str(self.limits[blocknumber][1]))

			# position in the block
			posinblock = self.marked_pos - block_len_total[blocknumber]
			
			oldvalue = self._value[blocknumber]
			olddec = oldvalue % 10 ** (number_len - posinblock) - (oldvalue % 10 ** (number_len - posinblock - 1))
			newvalue = oldvalue - olddec + (10 ** (number_len - posinblock - 1) * number)
			
			self._value[blocknumber] = newvalue
			self.marked_pos += 1
		
			self.validate()
			self.changed()
	
	def genText(self):
		value = ""
		mPos = self.marked_pos
		num = 0;
		for i in self._value:
			if len(value):	#fixme no heading separator possible
				value += self.seperator
				if mPos >= len(value) - 1:
					mPos += 1

			if self.censor_char == "":
				value += ("%0" + str(len(str(self.limits[num][1]))) + "d") % i
			else:
				value += (self.censor_char * len(str(self.limits[num][1])))
			num += 1
		return (value, mPos)
		
	def getText(self):
		(value, mPos) = self.genText()
		return value
	
	def getMulti(self, selected):
		(value, mPos) = self.genText()
			# only mark cursor when we are selected
			# (this code is heavily ink optimized!)
		if self.enabled:
			return ("mtext"[1-selected:], value, [mPos])
		else:
			return ("text", value)

	def tostring(self, val):
		return self.seperator.join([self.saveSingle(x) for x in val])
	
	def saveSingle(self, v):
		return str(v)

	def fromstring(self, value):
		return [int(x) for x in value.split(self.seperator)]

class ConfigIP(ConfigSequence):
	def __init__(self, default):
		ConfigSequence.__init__(self, seperator = ".", limits = [(0,255),(0,255),(0,255),(0,255)], default = default)
	
	def getHTML(self, id):
		# we definitely don't want leading zeros
		return '.'.join(["%d" % d for d in self.value])

class ConfigMAC(ConfigSequence):
	def __init__(self, default):
		ConfigSequence.__init__(self, seperator = ":", limits = [(1,255),(1,255),(1,255),(1,255),(1,255),(1,255)], default = default)

class ConfigPosition(ConfigSequence):
	def __init__(self, default, args):
		ConfigSequence.__init__(self, seperator = ",", limits = [(0,args[0]),(0,args[1]),(0,args[2]),(0,args[3])], default = default)

class ConfigClock(ConfigSequence):
	def __init__(self, default):
		import time
		t = time.localtime(default)
		ConfigSequence.__init__(self, seperator = ":", limits = [(0,23),(0,59)], default = [t.tm_hour, t.tm_min])

class ConfigInteger(ConfigSequence):
	def __init__(self, default, limits = (0, 10000000000)):
		ConfigSequence.__init__(self, seperator = ":", limits = [limits], default = default)
	
	# you need to override this to do input validation
	def setValue(self, value):
		self._value = [value]
		self.changed()

	def getValue(self):
		return self._value[0]
	
	value = property(getValue, setValue)

	def fromstring(self, value):
		return int(value)

	def tostring(self, value):
		return str(value)

class ConfigPIN(ConfigInteger):
	def __init__(self, default, len = 4, censor = ""):
		assert isinstance(default, int), "ConfigPIN default must be an integer"
		if default == -1:
			default = "aaaa"
		ConfigSequence.__init__(self, seperator = ":", limits = [(0, (10**len)-1)], censor_char = censor, default = default)
		self.len = len

	def getLength(self):
		return self.len

class ConfigFloat(ConfigSequence):
	def __init__(self, default, limits):
		ConfigSequence.__init__(self, seperator = ".", limits = limits, default = default)

	def getFloat(self):
		return float(self.value[1] / float(self.limits[1][1] + 1) + self.value[0])

	float = property(getFloat)

# an editable text...
class ConfigText(ConfigElement, NumericalTextInput):
	def __init__(self, default = "", fixed_size = True, visible_width = False):
		ConfigElement.__init__(self)
		NumericalTextInput.__init__(self, nextFunc = self.nextFunc, handleTimeout = False)
		
		self.marked_pos = 0
		self.allmarked = (default != "")
		self.fixed_size = fixed_size
		self.visible_width = visible_width
		self.offset = 0
		self.overwrite = fixed_size
		self.help_window = None
		self.value = self.default = default

	def validateMarker(self):
		if self.fixed_size:
			if self.marked_pos > len(self.text)-1:
				self.marked_pos = len(self.text)-1
		else:
			if self.marked_pos > len(self.text):
				self.marked_pos = len(self.text)
		if self.marked_pos < 0:
			self.marked_pos = 0
		if self.visible_width:
			if self.marked_pos < self.offset:
				self.offset = self.marked_pos
			if self.marked_pos >= self.offset + self.visible_width:
				if self.marked_pos == len(self.text):
					self.offset = self.marked_pos - self.visible_width
				else:
					self.offset = self.marked_pos - self.visible_width + 1
			if self.offset > 0 and self.offset + self.visible_width > len(self.text):
				self.offset = max(0, len(self.text) - self.visible_width)

	def insertChar(self, ch, pos, owr):
		if owr or self.overwrite:
			self.text = self.text[0:pos] + ch + self.text[pos + 1:]
		elif self.fixed_size:
			self.text = self.text[0:pos] + ch + self.text[pos:-1]
		else:
			self.text = self.text[0:pos] + ch + self.text[pos:]

	def deleteChar(self, pos):
		if not self.fixed_size:
			self.text = self.text[0:pos] + self.text[pos + 1:]
		elif self.overwrite:
			self.text = self.text[0:pos] + " " + self.text[pos + 1:]
		else:
			self.text = self.text[0:pos] + self.text[pos + 1:] + " "

	def deleteAllChars(self):
		if self.fixed_size:
			self.text = " " * len(self.text)
		else:
			self.text = ""
		self.marked_pos = 0

	def handleKey(self, key):
		# this will no change anything on the value itself
		# so we can handle it here in gui element
		if key == KEY_DELETE:
			self.timeout()
			if self.allmarked:
				self.deleteAllChars()
				self.allmarked = False
			else:
				self.deleteChar(self.marked_pos)
				if self.fixed_size and self.overwrite:
					self.marked_pos += 1
		elif key == KEY_BACKSPACE:
			self.timeout()
			if self.allmarked:
				self.deleteAllChars()
				self.allmarked = False
			elif self.marked_pos > 0:
				self.deleteChar(self.marked_pos-1)
				if not self.fixed_size and self.offset > 0:
					self.offset -= 1
				self.marked_pos -= 1
		elif key == KEY_LEFT:
			self.timeout()
			if self.allmarked:
				self.marked_pos = len(self.text)
				self.allmarked = False
			else:
				self.marked_pos -= 1
		elif key == KEY_RIGHT:
			self.timeout()
			if self.allmarked:
				self.marked_pos = 0
				self.allmarked = False
			else:
				self.marked_pos += 1
		elif key == KEY_HOME:
			self.timeout()
			self.allmarked = False
			self.marked_pos = 0
		elif key == KEY_END:
			self.timeout()
			self.allmarked = False
			self.marked_pos = len(self.text)
		elif key == KEY_TOGGLEOW:
			self.timeout()
			self.overwrite = not self.overwrite
		elif key == KEY_ASCII:
  			self.timeout()
  			newChar = unichr(getPrevAsciiCode())
			if self.allmarked:
				self.deleteAllChars()
				self.allmarked = False
			self.insertChar(newChar, self.marked_pos, False)
			self.marked_pos += 1
		elif key in KEY_NUMBERS:
			owr = self.lastKey == getKeyNumber(key)
			newChar = self.getKey(getKeyNumber(key))
			if self.allmarked:
				self.deleteAllChars()
				self.allmarked = False
			self.insertChar(newChar, self.marked_pos, owr)
		elif key == KEY_TIMEOUT:
			self.timeout()
			if self.help_window:
				self.help_window.update(self)
			return

		if self.help_window:
			self.help_window.update(self)
		self.validateMarker()
		self.changed()

	def nextFunc(self):
		self.marked_pos += 1
		self.validateMarker()
		self.changed()

	def getValue(self):
		return self.text.encode("utf-8")
		
	def setValue(self, val):
		try:
			self.text = val.decode("utf-8")
		except UnicodeDecodeError:
			self.text = val
			print "Broken UTF8!"

	value = property(getValue, setValue)
	_value = property(getValue, setValue)

	def getText(self):
		return self.text.encode("utf-8")

	def getMulti(self, selected):
		if self.visible_width:
			if self.allmarked:
				mark = range(0, min(self.visible_width, len(self.text)))
			else:
				mark = [self.marked_pos-self.offset]
			return ("mtext"[1-selected:], self.text[self.offset:self.offset+self.visible_width].encode("utf-8")+" ", mark)
		else:
			if self.allmarked:
				mark = range(0, len(self.text))
			else:
				mark = [self.marked_pos]
			return ("mtext"[1-selected:], self.text.encode("utf-8")+" ", mark)

	def onSelect(self, session):
		self.allmarked = (self.value != "")
		if session is not None:
			from Screens.NumericalTextInputHelpDialog import NumericalTextInputHelpDialog
			self.help_window = session.instantiateDialog(NumericalTextInputHelpDialog, self)
			self.help_window.show()

	def onDeselect(self, session):
		self.marked_pos = 0
		self.offset = 0
		if self.help_window:
			session.deleteDialog(self.help_window)
			self.help_window = None

	def getHTML(self, id):
		return '<input type="text" name="' + id + '" value="' + self.value + '" /><br>\n'

	def unsafeAssign(self, value):
		self.value = str(value)

class ConfigNumber(ConfigText):
	def __init__(self, default = 0):
		ConfigText.__init__(self, str(default), fixed_size = False)

	def getValue(self):
		return int(self.text)
		
	def setValue(self, val):
		self.text = str(val)

	value = property(getValue, setValue)
	_value = property(getValue, setValue)

	def conform(self):
		pos = len(self.text) - self.marked_pos
		self.text = self.text.lstrip("0")
		if self.text == "":
			self.text = "0"
		if pos > len(self.text):
			self.marked_pos = 0
		else:
			self.marked_pos = len(self.text) - pos

	def handleKey(self, key):
		if key in KEY_NUMBERS or key == KEY_ASCII:
			if key == KEY_ASCII:
				ascii = getPrevAsciiCode()
				if not (48 <= ascii <= 57):
					return
			else:
				ascii = getKeyNumber(key) + 48
  			newChar = unichr(ascii)
			if self.allmarked:
				self.deleteAllChars()
				self.allmarked = False
			self.insertChar(newChar, self.marked_pos, False)
			self.marked_pos += 1
		else:
			ConfigText.handleKey(self, key)
		self.conform()

	def onSelect(self, session):
		self.allmarked = (self.value != "")

	def onDeselect(self, session):
		self.marked_pos = 0
		self.offset = 0

# a slider.
class ConfigSlider(ConfigElement):
	def __init__(self, default = 0, increment = 1, limits = (0, 100)):
		ConfigElement.__init__(self)
		self.value = self.default = default
		self.min = limits[0]
		self.max = limits[1]
		self.increment = increment

	def checkValues(self):
		if self.value < self.min:
			self.value = self.min

		if self.value > self.max:
			self.value = self.max

	def handleKey(self, key):
		if key == KEY_LEFT:
			self.value -= self.increment
		elif key == KEY_RIGHT:
			self.value += self.increment
		elif key == KEY_HOME:
			self.value = self.min
		elif key == KEY_END:
			self.value = self.max
		else:
			return

		self.checkValues()
		self.changed()

	def getText(self):
		return "%d / %d" % (self.value, self.max)

	def getMulti(self, selected):
		self.checkValues()
		return ("slider", self.value, self.max)

	def fromstring(self, value):
		return int(value)

# a satlist. in fact, it's a ConfigSelection.
class ConfigSatlist(ConfigSelection):
	def __init__(self, list, default = None):
		if default is not None:
			default = str(default)
		ConfigSelection.__init__(self, choices = [(str(orbpos), desc) for (orbpos, desc, flags) in list], default = default)

	def getOrbitalPosition(self):
		if self.value == "":
			return None
		return int(self.value)
	
	orbital_position = property(getOrbitalPosition)

# nothing.
class ConfigNothing(ConfigSelection):
	def __init__(self):
		ConfigSelection.__init__(self, choices = [""])

# until here, 'saved_value' always had to be a *string*.
# now, in ConfigSubsection, and only there, saved_value
# is a dict, essentially forming a tree.
#
# config.foo.bar=True
# config.foobar=False
#
# turns into:
# config.saved_value == {"foo": {"bar": "True"}, "foobar": "False"}
#


class ConfigSubsectionContent(object):
	pass

# we store a backup of the loaded configuration
# data in self.stored_values, to be able to deploy
# them when a new config element will be added,
# so non-default values are instantly available

# A list, for example:
# config.dipswitches = ConfigSubList()
# config.dipswitches.append(ConfigYesNo())
# config.dipswitches.append(ConfigYesNo())
# config.dipswitches.append(ConfigYesNo())
class ConfigSubList(list, object):
	def __init__(self):
		object.__init__(self)
		list.__init__(self)
		self.stored_values = {}

	def save(self):
		for x in self:
			x.save()
	
	def load(self):
		for x in self:
			x.load()

	def getSavedValue(self):
		res = {}
		for i in range(len(self)):
			sv = self[i].saved_value
			if sv is not None:
				res[str(i)] = sv
		return res

	def setSavedValue(self, values):
		self.stored_values = dict(values)
		for (key, val) in self.stored_values.items():
			if int(key) < len(self):
				self[int(key)].saved_value = val

	saved_value = property(getSavedValue, setSavedValue)
	
	def append(self, item):
		i = str(len(self))
		list.append(self, item)
		if i in self.stored_values:
			item.saved_value = self.stored_values[i]
			item.load()

	def dict(self):
		res = dict()
		for index in range(len(self)):
			res[str(index)] = self[index]
		return res

# same as ConfigSubList, just as a dictionary.
# care must be taken that the 'key' has a proper
# str() method, because it will be used in the config
# file.
class ConfigSubDict(dict, object):
	def __init__(self):
		object.__init__(self)
		dict.__init__(self)
		self.stored_values = {}

	def save(self):
		for x in self.values():
			x.save()
	
	def load(self):
		for x in self.values():
			x.load()

	def getSavedValue(self):
		res = {}
		for (key, val) in self.items():
			if val.saved_value is not None:
				res[str(key)] = val.saved_value
		return res

	def setSavedValue(self, values):
		self.stored_values = dict(values)
		for (key, val) in self.items():
			if str(key) in self.stored_values:
				val = self.stored_values[str(key)]

	saved_value = property(getSavedValue, setSavedValue)

	def __setitem__(self, key, item):
		dict.__setitem__(self, key, item)
		if str(key) in self.stored_values:
			item.saved_value = self.stored_values[str(key)]
			item.load()

	def dict(self):
		return self

# Like the classes above, just with a more "native"
# syntax.
#
# some evil stuff must be done to allow instant
# loading of added elements. this is why this class
# is so complex.
#
# we need the 'content' because we overwrite 
# __setattr__.
# If you don't understand this, try adding
# __setattr__ to a usual exisiting class and you will.
class ConfigSubsection(object):
	def __init__(self):
		object.__init__(self)
		self.__dict__["content"] = ConfigSubsectionContent()
		self.content.items = { }
		self.content.stored_values = { }
	
	def __setattr__(self, name, value):
		if name == "saved_value":
			return self.setSavedValue(value)
		assert isinstance(value, ConfigSubsection) or isinstance(value, ConfigElement) or isinstance(value, ConfigSubList) or isinstance(value, ConfigSubDict), "ConfigSubsections can only store ConfigSubsections, ConfigSubLists, ConfigSubDicts or ConfigElements"
		self.content.items[name] = value
		if name in self.content.stored_values:
			#print "ok, now we have a new item,", name, "and have the following value for it:", self.content.stored_values[name]
			value.saved_value = self.content.stored_values[name]
			value.load()

	def __getattr__(self, name):
		return self.content.items[name]

	def getSavedValue(self):
		res = self.content.stored_values
		for (key, val) in self.content.items.items():
			if val.saved_value is not None:
				res[key] = val.saved_value
			elif key in res:
				del res[key]
				
		return res

	def setSavedValue(self, values):
		values = dict(values)
		
		self.content.stored_values = values

		for (key, val) in self.content.items.items():
			if key in values:
				val.saved_value = values[key]

	saved_value = property(getSavedValue, setSavedValue)

	def save(self):
		for x in self.content.items.values():
			x.save()

	def load(self):
		for x in self.content.items.values():
			x.load()

	def dict(self):
		return self.content.items

class ConfigSet(ConfigElement):
	def __init__(self, choices, default = []):
		ConfigElement.__init__(self)
		choices.sort()
		self.choices = choices
		self.pos = -1
		default.sort()
		self.default = default
		self.value = default+[]

	def toggleChoice(self, choice):
		if choice in self.value:
			self.value.remove(choice)
		else:
			self.value.append(choice)
			self.value.sort()

	def handleKey(self, key):
		if key in KEY_NUMBERS + [KEY_DELETE, KEY_BACKSPACE]:
			if self.pos != -1:
				self.toggleChoice(self.choices[self.pos])
		elif key == KEY_LEFT:
			self.pos -= 1
			if self.pos < -1:
			    self.pos = len(self.choices)-1
		elif key == KEY_RIGHT:
			self.pos += 1
			if self.pos >= len(self.choices):
			    self.pos = -1
		elif key in [KEY_HOME, KEY_END]:
			self.pos = -1

	def genString(self, lst):
		res = ""
		for x in lst:
			res += str(x)+" "
		return res

	def getText(self):
		self.genString(self.value)

	def getMulti(self, selected):
		if not selected or self.pos == -1:
			return ("text", self.genString(self.value))
		else:
			tmp = self.value+[]
			ch = self.choices[self.pos]
			mem = ch in self.value
			if not mem:
				tmp.append(ch)
				tmp.sort()
			ind = tmp.index(ch)
			val1 = self.genString(tmp[:ind])
			val2 = " "+self.genString(tmp[ind+1:])
			if mem:
				chstr = " "+str(ch)+" "
			else:
				chstr = "("+str(ch)+")"
			return ("mtext", val1+chstr+val2, range(len(val1),len(val1)+len(chstr)))

	def onDeselect(self, session):
		self.pos = -1
		self.changed()
		
	def tostring(self, value):
		return str(value)

	def fromstring(self, val):
		return eval(val)


# the root config object, which also can "pickle" (=serialize)
# down the whole config tree.
#
# we try to keep non-existing config entries, to apply them whenever
# a new config entry is added to a subsection
# also, non-existing config entries will be saved, so they won't be
# lost when a config entry disappears.
class Config(ConfigSubsection):
	def __init__(self):
		ConfigSubsection.__init__(self)

	def pickle_this(self, prefix, topickle, result):
		for (key, val) in topickle.items():
			name = prefix + "." + key
			
			if isinstance(val, dict):
				self.pickle_this(name, val, result)
			elif isinstance(val, tuple):
				result.append(name + "=" + val[0]) # + " ; " + val[1])
			else:
				result.append(name + "=" + val)

	def pickle(self):
		result = [ ]
		self.pickle_this("config", self.saved_value, result)
		return '\n'.join(result) + "\n"

	def unpickle(self, lines):
		tree = { }
		for l in lines:
			if not len(l) or l[0] == '#':
				continue
			
			n = l.find('=')
			val = l[n+1:].strip()

			names = l[:n].split('.')
#			if val.find(' ') != -1:
#				val = val[:val.find(' ')]

			base = tree
			
			for n in names[:-1]:
				base = base.setdefault(n, {})
			
			base[names[-1]] = val

		# we inherit from ConfigSubsection, so ...
		#object.__setattr__(self, "saved_value", tree["config"])
		if "config" in tree:
			self.setSavedValue(tree["config"])

	def saveToFile(self, filename):
		f = open(filename, "w")
		f.write(self.pickle())
		f.close()

	def loadFromFile(self, filename):
		f = open(filename, "r")
		self.unpickle(f.readlines())
		f.close()

config = Config()
config.misc = ConfigSubsection()

class ConfigFile:
	CONFIG_FILE = resolveFilename(SCOPE_CONFIG, "settings")

	def load(self):
		try:
			config.loadFromFile(self.CONFIG_FILE)
		except IOError, e:
			print "unable to load config (%s), assuming defaults..." % str(e)
	
	def save(self):
#		config.save()
		config.saveToFile(self.CONFIG_FILE)
	
	def __resolveValue(self, pickles, cmap):
		if cmap.has_key(pickles[0]):
			if len(pickles) > 1:
				return self.__resolveValue(pickles[1:], cmap[pickles[0]].dict())
			else:
				return str(cmap[pickles[0]].value)
		return None
	
	def getResolvedKey(self, key):
		names = key.split('.')
		if len(names) > 1:
			if names[0] == "config":
				ret=self.__resolveValue(names[1:], config.content.items)
				if ret and len(ret):
					return ret
		print "getResolvedKey", key, "failed !! (Typo??)"
		return ""

def NoSave(element):
	element.disableSave()
	return element

configfile = ConfigFile()

configfile.load()

def getConfigListEntry(*args):
	assert len(args) > 1, "getConfigListEntry needs a minimum of two arguments (descr, configElement)"
	return args

#def _(x):
#	return x
#
#config.bla = ConfigSubsection()
#config.bla.test = ConfigYesNo()
#config.nim = ConfigSubList()
#config.nim.append(ConfigSubsection())
#config.nim[0].bla = ConfigYesNo()
#config.nim.append(ConfigSubsection())
#config.nim[1].bla = ConfigYesNo()
#config.nim[1].blub = ConfigYesNo()
#config.arg = ConfigSubDict()
#config.arg["Hello"] = ConfigYesNo()
#
#config.arg["Hello"].handleKey(KEY_RIGHT)
#config.arg["Hello"].handleKey(KEY_RIGHT)
#
##config.saved_value
#
##configfile.save()
#config.save()
#print config.pickle()
