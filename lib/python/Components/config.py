from enigma import getPrevAsciiCode
from Tools.NumericalTextInput import NumericalTextInput
from Tools.Directories import resolveFilename, SCOPE_CONFIG, fileExists
from Components.Harddisk import harddiskmanager
from Tools.LoadPixmap import LoadPixmap
from copy import copy as copy_copy
from os import path as os_path
from time import localtime, strftime

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
		self.extra_args = {}
		self.saved_value = None
		self.save_forced = False
		self.last_value = None
		self.save_disabled = False
		self.__notifiers = { }
		self.__notifiers_final = { }
		self.enabled = True
		self.callNotifiersOnSaveAndCancel = False

	def getNotifiers(self):
		return [func for (func, val, call_on_save_and_cancel) in self.__notifiers.itervalues()]

	def setNotifiers(self, val):
		print "just readonly access to notifiers is allowed! append/remove doesnt work anymore! please use addNotifier, removeNotifier, clearNotifiers"

	notifiers = property(getNotifiers, setNotifiers)

	def getNotifiersFinal(self):
		return [func for (func, val, call_on_save_and_cancel) in self.__notifiers_final.itervalues()]

	def setNotifiersFinal(self, val):
		print "just readonly access to notifiers_final is allowed! append/remove doesnt work anymore! please use addNotifier, removeNotifier, clearNotifiers"

	notifiers_final = property(getNotifiersFinal, setNotifiersFinal)

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
		sv = self.saved_value
		if sv is None:
			self.value = self.default
		else:
			self.value = self.fromstring(sv)

	def tostring(self, value):
		return str(value)

	# you need to override this if str(self.value) doesn't work
	def save(self):
		if self.save_disabled or (self.value == self.default and not self.save_forced):
			self.saved_value = None
		else:
			self.saved_value = self.tostring(self.value)
		if self.callNotifiersOnSaveAndCancel:
			self.changed()

	def cancel(self):
		self.load()
		if self.callNotifiersOnSaveAndCancel:
			self.changed()

	def isChanged(self):
		sv = self.saved_value
		if sv is None and self.value == self.default:
			return False
		return self.tostring(self.value) != sv

	def changed(self):
		if self.__notifiers:
			for x in self.notifiers:
				try:
					if self.extra_args and self.extra_args[x]:
						x(self, self.extra_args[x])
					else:
						x(self)
				except:
					x(self)

	def changedFinal(self):
		if self.__notifiers_final:
			for x in self.notifiers_final:
				try:
					if self.extra_args and self.extra_args[x]:
						x(self, self.extra_args[x])
					else:
						x(self)
				except:
					x(self)

	# immediate_feedback = True means call notifier on every value CHANGE
	# immediate_feedback = False means call notifier on leave the config element (up/down) when value have CHANGED
	# call_on_save_or_cancel = True means call notifier always on save/cancel.. even when value have not changed
	def addNotifier(self, notifier, initial_call = True, immediate_feedback = True, call_on_save_or_cancel = False, extra_args=None):
		if not extra_args: extra_args = []
		assert callable(notifier), "notifiers must be callable"
		try:
			self.extra_args[notifier] = extra_args
		except: pass	
		if immediate_feedback:
			self.__notifiers[str(notifier)] = (notifier, self.value, call_on_save_or_cancel)
		else:
			self.__notifiers_final[str(notifier)] = (notifier, self.value, call_on_save_or_cancel)
		# CHECKME:
		# do we want to call the notifier
		#  - at all when adding it? (yes, though optional)
		#  - when the default is active? (yes)
		#  - when no value *yet* has been set,
		#    because no config has ever been read (currently yes)
		#    (though that's not so easy to detect.
		#     the entry could just be new.)
		if initial_call:
			if extra_args:
				notifier(self,extra_args)
			else:
				notifier(self)

	def removeNotifier(self, notifier):
		try:
			del self.__notifiers[str(notifier)]
		except:
			try:
				del self.__notifiers_final[str(notifier)]
			except:
				pass

	def clearNotifiers(self):
		self.__notifiers = { }
		self.__notifiers_final = { }

	def disableSave(self):
		self.save_disabled = True

	def __call__(self, selected):
		return self.getMulti(selected)

	def onSelect(self, session):
		pass

	def onDeselect(self, session):
		if not self.last_value == self.value:
			self.changedFinal()
			self.last_value = self.value

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

class choicesList(object): # XXX: we might want a better name for this
	LIST_TYPE_LIST = 1
	LIST_TYPE_DICT = 2

	def __init__(self, choices, type = None):
		self.choices = choices
		if type is None:
			if isinstance(choices, list):
				self.type = choicesList.LIST_TYPE_LIST
			elif isinstance(choices, dict):
				self.type = choicesList.LIST_TYPE_DICT
			else:
				assert False, "choices must be dict or list!"
		else:
			self.type = type

	def __list__(self):
		if self.type == choicesList.LIST_TYPE_LIST:
			ret = [not isinstance(x, tuple) and x or x[0] for x in self.choices]
		else:
			ret = self.choices.keys()
		return ret or [""]

	def __iter__(self):
		if self.type == choicesList.LIST_TYPE_LIST:
			ret = [not isinstance(x, tuple) and x or x[0] for x in self.choices]
		else:
			ret = self.choices
		return iter(ret or [""])

	def __len__(self):
		return len(self.choices) or 1

	def updateItemDescription(self, index, descr):
		if self.type == choicesList.LIST_TYPE_LIST:
			orig = self.choices[index]
			assert isinstance(orig, tuple)
			self.choices[index] = (orig[0], descr)
		else:
			key = self.choices.keys()[index]
			self.choices[key] = descr

	def __getitem__(self, index):
		if self.type == choicesList.LIST_TYPE_LIST:
			ret = self.choices[index]
			if isinstance(ret, tuple):
				ret = ret[0]
			return ret
		return self.choices.keys()[index]

	def index(self, value):
		try:
			return self.__list__().index(value)
		except (ValueError, IndexError):
			# occurs e.g. when default is not in list
			return 0

	def __setitem__(self, index, value):
		if self.type == choicesList.LIST_TYPE_LIST:
			orig = self.choices[index]
			if isinstance(orig, tuple):
				self.choices[index] = (value, orig[1])
			else:
				self.choices[index] = value
		else:
			key = self.choices.keys()[index]
			orig = self.choices[key]
			del self.choices[key]
			self.choices[value] = orig

	def default(self):
		choices = self.choices
		if not choices:
			return ""
		if self.type is choicesList.LIST_TYPE_LIST:
			default = choices[0]
			if isinstance(default, tuple):
				default = default[0]
		else:
			default = choices.keys()[0]
		return default

class descriptionList(choicesList): # XXX: we might want a better name for this
	def __list__(self):
		if self.type == choicesList.LIST_TYPE_LIST:
			ret = [not isinstance(x, tuple) and x or x[1] for x in self.choices]
		else:
			ret = self.choices.values()
		return ret or [""]

	def __iter__(self):
		return iter(self.__list__())

	def __getitem__(self, index):
		if self.type == choicesList.LIST_TYPE_LIST:
			for x in self.choices:
				if isinstance(x, tuple):
					if x[0] == index:
						return str(x[1])
				elif x == index:
					return str(x)
			return str(index) # Fallback!
		else:
			return str(self.choices.get(index, ""))

	def __setitem__(self, index, value):
		if self.type == choicesList.LIST_TYPE_LIST:
			i = self.index(index)
			orig = self.choices[i]
			if isinstance(orig, tuple):
				self.choices[i] = (orig[0], value)
			else:
				self.choices[i] = value
		else:
			self.choices[index] = value

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
		self.choices = choicesList(choices)

		if default is None:
			default = self.choices.default()

		self._descr = None
		self.default = self._value = self.last_value = default

	def setChoices(self, choices, default = None):
		self.choices = choicesList(choices)

		if default is None:
			default = self.choices.default()
		self.default = default

		if self.value not in self.choices:
			self.value = default

	def setValue(self, value):
		if value in self.choices:
			self._value = value
		else:
			self._value = self.default
		self._descr = None
		self.changed()

	def tostring(self, val):
		return val

	def getValue(self):
		return self._value

	def setCurrentText(self, text):
		i = self.choices.index(self.value)
		self.choices[i] = text
		self._descr = self.description[text] = text
		self._value = text

	value = property(getValue, setValue)

	def getIndex(self):
		return self.choices.index(self.value)

	index = property(getIndex)

	# GUI
	def handleKey(self, key):
		nchoices = len(self.choices)
		if nchoices > 1:
			i = self.choices.index(self.value)
			if key == KEY_LEFT:
				self.value = self.choices[(i + nchoices - 1) % nchoices]
			elif key == KEY_RIGHT:
				self.value = self.choices[(i + 1) % nchoices]
			elif key == KEY_HOME:
				self.value = self.choices[0]
			elif key == KEY_END:
				self.value = self.choices[nchoices - 1]

	def selectNext(self):
		nchoices = len(self.choices)
		i = self.choices.index(self.value)
		self.value = self.choices[(i + 1) % nchoices]

	def getText(self):
		if self._descr is None:
			self._descr = self.description[self.value]
		return self._descr

	def getMulti(self, selected):
		if self._descr is None:
			self._descr = self.description[self.value]
		return ("text", self._descr)

	# HTML
	def getHTML(self, id):
		res = ""
		for v in self.choices:
			descr = self.description[v]
			if self.value == v:
				checked = 'checked="checked" '
			else:
				checked = ''
			res += '<input type="radio" name="' + id + '" ' + checked + 'value="' + v + '">' + descr + "</input></br>\n"
		return res

	def unsafeAssign(self, value):
		# setValue does check if value is in choices. This is safe enough.
		self.value = value

	description = property(lambda self: descriptionList(self.choices.choices, self.choices.type))

# a binary decision.
#
# several customized versions exist for different
# descriptions.
#
class ConfigBoolean(ConfigElement):
	def __init__(self, default = False, descriptions = {False: _("false"), True: _("true")}, graphic=True):
		ConfigElement.__init__(self)
		self.descriptions = descriptions
		self.value = self.last_value = self.default = default
		self.graphic = graphic

	def handleKey(self, key):
		if key in (KEY_LEFT, KEY_RIGHT):
			self.value = not self.value
		elif key == KEY_HOME:
			self.value = False
		elif key == KEY_END:
			self.value = True

	def getText(self):
		return self.descriptions[self.value]

	def getMulti(self, selected):
		from config import config
		from skin import switchPixmap
		if self.graphic and config.usage.boolean_graphic.value and switchPixmap.get("menu_on", False) and switchPixmap.get("menu_off", False):
			return ('pixmap', self.value and switchPixmap["menu_on"] or switchPixmap["menu_off"])
		else:
			return ("text", self.descriptions[self.value])

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

	def onDeselect(self, session):
		if not self.last_value == self.value:
			self.changedFinal()
			self.last_value = self.value

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
		self.value = self.last_value = self.default = int(default)

	def handleKey(self, key):
		if key == KEY_LEFT:
			self.value -= self.increment
		elif key == KEY_RIGHT:
			self.value += self.increment
		elif key == KEY_HOME or key == KEY_END:
			self.value = self.default

	def getText(self):
		return strftime(self.formatstring, localtime(self.value))

	def getMulti(self, selected):
		return "text", strftime(self.formatstring, localtime(self.value))

	def fromstring(self, val):
		return int(val)

# *THE* mighty config element class
#
# allows you to store/edit a sequence of values.
# can be used for IP-addresses, dates, plain integers, ...
# several helper exist to ease this up a bit.
#
class ConfigSequence(ConfigElement):
	def __init__(self, seperator, limits, default, censor_char = ""):
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

		self.last_value = self.default = default
		self.value = copy_copy(default)
		self.endNotifier = None

	def validate(self):
		max_pos = 0
		num = 0
		for i in self._value:
			max_pos += len(str(self.limits[num][1]))

			if self._value[num] < self.limits[num][0]:
				self._value[num] = self.limits[num][0]

			if self._value[num] > self.limits[num][1]:
				self._value[num] = self.limits[num][1]

			num += 1

		if self.marked_pos >= max_pos:
			if self.endNotifier:
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
		if self.endNotifier is None:
			self.endNotifier = []
		self.endNotifier.append(notifier)

	def handleKey(self, key):
		if key == KEY_LEFT:
			self.marked_pos -= 1
			self.validatePos()

		elif key == KEY_RIGHT:
			self.marked_pos += 1
			self.validatePos()

		elif key == KEY_HOME:
			self.marked_pos = 0
			self.validatePos()

		elif key == KEY_END:
			max_pos = 0
			num = 0
			for i in self._value:
				max_pos += len(str(self.limits[num][1]))
				num += 1
			self.marked_pos = max_pos - 1
			self.validatePos()

		elif key in KEY_NUMBERS or key == KEY_ASCII:
			if key == KEY_ASCII:
				code = getPrevAsciiCode()
				if code < 48 or code > 57:
					return
				number = code - 48
			else:
				number = getKeyNumber(key)

			block_len = [len(str(x[1])) for x in self.limits]
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

			oldvalue = abs(self._value[blocknumber]) # we are using abs in order to allow change negative values like default -1 on mis
			olddec = oldvalue % 10 ** (number_len - posinblock) - (oldvalue % 10 ** (number_len - posinblock - 1))
			newvalue = oldvalue - olddec + (10 ** (number_len - posinblock - 1) * number)

			self._value[blocknumber] = newvalue
			self.marked_pos += 1

			self.validate()
			self.changed()

	def genText(self):
		value = ""
		mPos = self.marked_pos
		num = 0
		for i in self._value:
			if value:	#fixme no heading separator possible
				value += self.seperator
				if mPos >= len(value) - 1:
					mPos += 1
			if self.censor_char == "":
				value += ("%0" + str(len(str(self.limits[num][1]))) + "d") % i
			else:
				value += (self.censor_char * len(str(self.limits[num][1])))
			num += 1
		return value, mPos

	def getText(self):
		(value, mPos) = self.genText()
		return value

	def getMulti(self, selected):
		(value, mPos) = self.genText()
			# only mark cursor when we are selected
			# (this code is heavily ink optimized!)
		if self.enabled:
			return "mtext"[1-selected:], value, [mPos]
		else:
			return "text", value

	def tostring(self, val):
		return self.seperator.join([self.saveSingle(x) for x in val])

	def saveSingle(self, v):
		return str(v)

	def fromstring(self, value):
		try:
			return [int(x) for x in value.split(self.seperator)]
		except:
			return self.default

	def onDeselect(self, session):
		if self.last_value != self._value:
			self.changedFinal()
			self.last_value = copy_copy(self._value)

ip_limits = [(0,255),(0,255),(0,255),(0,255)]
class ConfigIP(ConfigSequence):
	def __init__(self, default, auto_jump = False):
		ConfigSequence.__init__(self, seperator = ".", limits = ip_limits, default = default)
		self.block_len = [len(str(x[1])) for x in self.limits]
		self.marked_block = 0
		self.overwrite = True
		self.auto_jump = auto_jump

	def handleKey(self, key):
		if key == KEY_LEFT:
			if self.marked_block > 0:
				self.marked_block -= 1
			self.overwrite = True

		elif key == KEY_RIGHT:
			if self.marked_block < len(self.limits)-1:
				self.marked_block += 1
			self.overwrite = True

		elif key == KEY_HOME:
			self.marked_block = 0
			self.overwrite = True

		elif key == KEY_END:
			self.marked_block = len(self.limits)-1
			self.overwrite = True

		elif key in KEY_NUMBERS or key == KEY_ASCII:
			if key == KEY_ASCII:
				code = getPrevAsciiCode()
				if code < 48 or code > 57:
					return
				number = code - 48
			else:
				number = getKeyNumber(key)
			oldvalue = self._value[self.marked_block]

			if self.overwrite:
				self._value[self.marked_block] = number
				self.overwrite = False
			else:
				oldvalue *= 10
				newvalue = oldvalue + number
				if self.auto_jump and newvalue > self.limits[self.marked_block][1] and self.marked_block < len(self.limits)-1:
					self.handleKey(KEY_RIGHT)
					self.handleKey(key)
					return
				else:
					self._value[self.marked_block] = newvalue

			if len(str(self._value[self.marked_block])) >= self.block_len[self.marked_block]:
				self.handleKey(KEY_RIGHT)

			self.validate()
			self.changed()

	def genText(self):
		value = ""
		block_strlen = []
		for i in self._value:
			block_strlen.append(len(str(i)))
			if value:
				value += self.seperator
			value += str(i)
		leftPos = sum(block_strlen[:self.marked_block])+self.marked_block
		rightPos = sum(block_strlen[:(self.marked_block+1)])+self.marked_block
		mBlock = range(leftPos, rightPos)
		return value, mBlock

	def getMulti(self, selected):
		(value, mBlock) = self.genText()
		if self.enabled:
			return "mtext"[1-selected:], value, mBlock
		else:
			return "text", value

	def getHTML(self, id):
		# we definitely don't want leading zeros
		return '.'.join(["%d" % d for d in self.value])

mac_limits = [(1,255),(1,255),(1,255),(1,255),(1,255),(1,255)]
class ConfigMAC(ConfigSequence):
	def __init__(self, default):
		ConfigSequence.__init__(self, seperator = ":", limits = mac_limits, default = default)

class ConfigMacText(ConfigElement, NumericalTextInput):
	def __init__(self, default = "", visible_width = False):
		ConfigElement.__init__(self)
		NumericalTextInput.__init__(self, nextFunc = self.nextFunc, handleTimeout = False)

		self.marked_pos = 0
		self.allmarked = (default != "")
		self.fixed_size = 17
		self.visible_width = visible_width
		self.offset = 0
		self.overwrite = 17
		self.help_window = None
		self.value = self.last_value = self.default = default
		self.useableChars = '0123456789ABCDEF'

	def validateMarker(self):
		textlen = len(self.text)
		if self.marked_pos > textlen-1:
			self.marked_pos = textlen-1
		elif self.marked_pos < 0:
			self.marked_pos = 0

	def insertChar(self, ch, pos, owr):
		if self.text[pos] == ':':
			pos += 1
		if owr or self.overwrite:
			self.text = self.text[0:pos] + ch + self.text[pos + 1:]
		elif self.fixed_size:
			self.text = self.text[0:pos] + ch + self.text[pos:-1]
		else:
			self.text = self.text[0:pos] + ch + self.text[pos:]

	def handleKey(self, key):
		if key == KEY_LEFT:
			self.timeout()
			if self.allmarked:
				self.marked_pos = len(self.text)
				self.allmarked = False
			else:
				if self.text[self.marked_pos-1] == ':':
					self.marked_pos -= 2
				else:
					self.marked_pos -= 1
		elif key == KEY_RIGHT:
			self.timeout()
			if self.allmarked:
				self.marked_pos = 0
				self.allmarked = False
			else:
				if self.marked_pos < (len(self.text)-1):
					if self.text[self.marked_pos+1] == ':':
						self.marked_pos += 2
					else:
						self.marked_pos += 1
		elif key in KEY_NUMBERS:
			owr = self.lastKey == getKeyNumber(key)
			newChar = self.getKey(getKeyNumber(key))
			self.insertChar(newChar, self.marked_pos, owr)
		elif key == KEY_TIMEOUT:
			self.timeout()
			if self.help_window:
				self.help_window.update(self)
			if self.text[self.marked_pos] == ':':
				self.marked_pos += 1
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
		try:
			return self.text.encode("utf-8")
		except UnicodeDecodeError:
			print "Broken UTF8!"
			return self.text

	def setValue(self, val):
		try:
			self.text = val.decode("utf-8")
		except UnicodeDecodeError:
			self.text = val.decode("utf-8", "ignore")
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
			return "mtext"[1-selected:], self.text[self.offset:self.offset+self.visible_width].encode("utf-8")+" ", mark
		else:
			if self.allmarked:
				mark = range(0, len(self.text))
			else:
				mark = [self.marked_pos]
			return "mtext"[1-selected:], self.text.encode("utf-8")+" ", mark

	def onSelect(self, session):
		self.allmarked = (self.value != "")
		if session is not None:
			from Screens.NumericalTextInputHelpDialog import NumericalTextInputHelpDialog
			self.help_window = session.instantiateDialog(NumericalTextInputHelpDialog, self)
			self.help_window.setAnimationMode(0)
			self.help_window.show()

	def onDeselect(self, session):
		self.marked_pos = 0
		self.offset = 0
		if self.help_window:
			session.deleteDialog(self.help_window)
			self.help_window = None
		if not self.last_value == self.value:
			self.changedFinal()
			self.last_value = self.value

	def getHTML(self, id):
		return '<input type="text" name="' + id + '" value="' + self.value + '" /><br>\n'

	def unsafeAssign(self, value):
		self.value = str(value)

class ConfigPosition(ConfigSequence):
	def __init__(self, default, args):
		ConfigSequence.__init__(self, seperator = ",", limits = [(0,args[0]),(0,args[1]),(0,args[2]),(0,args[3])], default = default)

clock_limits = [(0,23),(0,59)]
class ConfigClock(ConfigSequence):
	def __init__(self, default):
		t = localtime(default)
		ConfigSequence.__init__(self, seperator = ":", limits = clock_limits, default = [t.tm_hour, t.tm_min])

	def increment(self):
		# Check if Minutes maxed out
		if self._value[1] == 59:
			# Increment Hour, reset Minutes
			if self._value[0] < 23:
				self._value[0] += 1
			else:
				self._value[0] = 0
			self._value[1] = 0
		else:
			# Increment Minutes
			self._value[1] += 1
		# Trigger change
		self.changed()

	def decrement(self):
		# Check if Minutes is minimum
		if self._value[1] == 0:
			# Decrement Hour, set Minutes to 59
			if self._value[0] > 0:
				self._value[0] -= 1
			else:
				self._value[0] = 23
			self._value[1] = 59
		else:
			# Decrement Minutes
			self._value[1] -= 1
		# Trigger change
		self.changed()

integer_limits = (0, 9999999999)
class ConfigInteger(ConfigSequence):
	def __init__(self, default, limits = integer_limits):
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
		self.value = self.last_value = self.default = default

	def validateMarker(self):
		textlen = len(self.text)
		if self.fixed_size:
			if self.marked_pos > textlen-1:
				self.marked_pos = textlen-1
		else:
			if self.marked_pos > textlen:
				self.marked_pos = textlen
		if self.marked_pos < 0:
			self.marked_pos = 0
		if self.visible_width:
			if self.marked_pos < self.offset:
				self.offset = self.marked_pos
			if self.marked_pos >= self.offset + self.visible_width:
				if self.marked_pos == textlen:
					self.offset = self.marked_pos - self.visible_width
				else:
					self.offset = self.marked_pos - self.visible_width + 1
			if self.offset > 0 and self.offset + self.visible_width > textlen:
				self.offset = max(0, len - self.visible_width)

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
			if not self.useableChars or newChar in self.useableChars:
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
		try:
			return self.text.encode("utf-8")
		except UnicodeDecodeError:
			print "Broken UTF8!"
			return self.text

	def setValue(self, val):
		try:
			self.text = val.decode("utf-8")
		except UnicodeDecodeError:
			self.text = val.decode("utf-8", "ignore")
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
			return "mtext"[1-selected:], self.text[self.offset:self.offset+self.visible_width].encode("utf-8")+" ", mark
		else:
			if self.allmarked:
				mark = range(0, len(self.text))
			else:
				mark = [self.marked_pos]
			return "mtext"[1-selected:], self.text.encode("utf-8")+" ", mark

	def onSelect(self, session):
		self.allmarked = (self.value != "")
		if session is not None:
			from Screens.NumericalTextInputHelpDialog import NumericalTextInputHelpDialog
			self.help_window = session.instantiateDialog(NumericalTextInputHelpDialog, self)
			self.help_window.setAnimationMode(0)
			self.help_window.show()

	def onDeselect(self, session):
		self.marked_pos = 0
		self.offset = 0
		if self.help_window:
			session.deleteDialog(self.help_window)
			self.help_window = None
		if not self.last_value == self.value:
			self.changedFinal()
			self.last_value = self.value

	def getHTML(self, id):
		return '<input type="text" name="' + id + '" value="' + self.value + '" /><br>\n'

	def unsafeAssign(self, value):
		self.value = str(value)

class ConfigPassword(ConfigText):
	def __init__(self, default = "", fixed_size = False, visible_width = False, censor = "*"):
		ConfigText.__init__(self, default = default, fixed_size = fixed_size, visible_width = visible_width)
		self.censor_char = censor
		self.hidden = True

	def getMulti(self, selected):
		mtext, text, mark = ConfigText.getMulti(self, selected)
		if self.hidden:
			text = len(text) * self.censor_char
		return mtext, text, mark

	def onSelect(self, session):
		ConfigText.onSelect(self, session)
		self.hidden = False

	def onDeselect(self, session):
		ConfigText.onDeselect(self, session)
		self.hidden = True

# lets the user select between [min, min+stepwidth, min+(stepwidth*2)..., maxval] with maxval <= max depending
# on the stepwidth
# min, max, stepwidth, default are int values
# wraparound: pressing RIGHT key at max value brings you to min value and vice versa if set to True
class ConfigSelectionNumber(ConfigSelection):
	def __init__(self, min, max, stepwidth, default = None, wraparound = False):
		self.wraparound = wraparound
		if default is None:
			default = min
		default = str(default)
		choices = []
		step = min
		while step <= max:
			choices.append(str(step))
			step += stepwidth

		ConfigSelection.__init__(self, choices, default)

	def getValue(self):
		return int(ConfigSelection.getValue(self))

	def setValue(self, val):
		ConfigSelection.setValue(self, str(val))

	value = property(getValue, setValue)

	def getIndex(self):
		return self.choices.index(self.value)

	index = property(getIndex)

	def isChanged(self):
		sv = self.saved_value
		strv = str(self.tostring(self.value))
		if sv is None and strv == str(self.default):
			return False
		return strv != str(sv)

	def handleKey(self, key):
		if not self.wraparound:
			if key == KEY_RIGHT:
				if len(self.choices) == (self.choices.index(str(self.value)) + 1):
					return
			if key == KEY_LEFT:
				if self.choices.index(str(self.value)) == 0:
					return
		nchoices = len(self.choices)
		if nchoices > 1:
			i = self.choices.index(str(self.value))
			if key == KEY_LEFT:
				self.value = self.choices[(i + nchoices - 1) % nchoices]
			elif key == KEY_RIGHT:
				self.value = self.choices[(i + 1) % nchoices]
			elif key == KEY_HOME:
				self.value = self.choices[0]
			elif key == KEY_END:
				self.value = self.choices[nchoices - 1]

class ConfigNumber(ConfigText):
	def __init__(self, default = 0):
		ConfigText.__init__(self, str(default), fixed_size = False)

	def getValue(self):
		try:
			return int(self.text)
		except ValueError:
			if self.text == "true":
				self.text = "1"
			else:
				self.text = str(default)
			return int(self.text)

	def setValue(self, val):
		self.text = str(val)

	value = property(getValue, setValue)
	_value = property(getValue, setValue)

	def isChanged(self):
		sv = self.saved_value
		strv = self.tostring(self.value)
		if sv is None and strv == self.default:
			return False
		return strv != sv

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
		if not self.last_value == self.value:
			self.changedFinal()
			self.last_value = self.value

class ConfigSearchText(ConfigText):
	def __init__(self, default = "", fixed_size = False, visible_width = False):
		ConfigText.__init__(self, default = default, fixed_size = fixed_size, visible_width = visible_width)
		NumericalTextInput.__init__(self, nextFunc = self.nextFunc, handleTimeout = False, search = True)

class ConfigDirectory(ConfigText):
	def __init__(self, default="", visible_width=60):
		ConfigText.__init__(self, default, fixed_size = True, visible_width = visible_width)

	def handleKey(self, key):
		pass

	def getValue(self):
		if self.text == "":
			return None
		else:
			return ConfigText.getValue(self)

	def setValue(self, val):
		if val is None:
			val = ""
		ConfigText.setValue(self, val)

	def getMulti(self, selected):
		if self.text == "":
			return "mtext"[1-selected:], _("List of storage devices"), range(0)
		else:
			return ConfigText.getMulti(self, selected)

	def onSelect(self, session):
		self.allmarked = (self.value != "")

# a slider.
class ConfigSlider(ConfigElement):
	def __init__(self, default = 0, increment = 1, limits = (0, 100)):
		ConfigElement.__init__(self)
		self.value = self.last_value = self.default = default
		self.min = limits[0]
		self.max = limits[1]
		self.increment = increment

	def checkValues(self, value = None):
		if value is None:
			value = self.value
		if value < self.min:
			value = self.min
		elif value > self.max:
			value = self.max
		if self.value != value:		#avoid call of setter if value not changed
			self.value = value

	def handleKey(self, key):
		if key == KEY_LEFT:
			tmp = self.value - self.increment
		elif key == KEY_RIGHT:
			tmp = self.value + self.increment
		elif key == KEY_HOME:
			self.value = self.min
			return
		elif key == KEY_END:
			self.value = self.max
			return
		else:
			return
		self.checkValues(tmp)

	def getText(self):
		return "%d / %d" % (self.value, self.max)

	def getMulti(self, selected):
		self.checkValues()
		return "slider", self.value, self.max

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

class ConfigSet(ConfigElement):
	def __init__(self, choices, default=None):
		if not default: default = []
		ConfigElement.__init__(self)
		if isinstance(choices, list):
			choices.sort()
			self.choices = choicesList(choices, choicesList.LIST_TYPE_LIST)
		else:
			assert False, "ConfigSet choices must be a list!"
		if default is None:
			default = []
		self.pos = -1
		default.sort()
		self.last_value = self.default = default
		self.value = default[:]

	def toggleChoice(self, choice):
		value = self.value
		if choice in value:
			value.remove(choice)
		else:
			value.append(choice)
			value.sort()
		self.changed()

	def handleKey(self, key):
		if key in KEY_NUMBERS + [KEY_DELETE, KEY_BACKSPACE]:
			if self.pos != -1:
				self.toggleChoice(self.choices[self.pos])
		elif key == KEY_LEFT:
			if self.pos < 0:
				self.pos = len(self.choices)-1
			else:
				self.pos -= 1
		elif key == KEY_RIGHT:
			if self.pos >= len(self.choices)-1:
				self.pos = -1
			else:
				self.pos += 1
		elif key in (KEY_HOME, KEY_END):
			self.pos = -1

	def genString(self, lst):
		res = ""
		for x in lst:
			res += self.description[x]+" "
		return res

	def getText(self):
		return self.genString(self.value)

	def getMulti(self, selected):
		if not selected or self.pos == -1:
			return "text", self.genString(self.value)
		else:
			tmp = self.value[:]
			ch = self.choices[self.pos]
			mem = ch in self.value
			if not mem:
				tmp.append(ch)
				tmp.sort()
			ind = tmp.index(ch)
			val1 = self.genString(tmp[:ind])
			val2 = " "+self.genString(tmp[ind+1:])
			if mem:
				chstr = " "+self.description[ch]+" "
			else:
				chstr = "("+self.description[ch]+")"
			len_val1 = len(val1)
			return "mtext", val1+chstr+val2, range(len_val1, len_val1 + len(chstr))

	def onDeselect(self, session):
		self.pos = -1
		if not self.last_value == self.value:
			self.changedFinal()
			self.last_value = self.value[:]

	def tostring(self, value):
		return str(value)

	def fromstring(self, val):
		return eval(val)

	description = property(lambda self: descriptionList(self.choices.choices, choicesList.LIST_TYPE_LIST))


class ConfigDictionarySet(ConfigElement):
	def __init__(self, default = {}):
		ConfigElement.__init__(self)
		self.default = default
		self.dirs = {}
		self.value = self.default

	def getKeys(self):
		return self.dir_pathes

	def setValue(self, value):
		if isinstance(value, dict):
			self.dirs = value
			self.changed()

	def getValue(self):
		return self.dirs

	value = property(getValue, setValue)

	def tostring(self, value):
		return str(value)

	def fromstring(self, val):
		return eval(val)

	def load(self):
		sv = self.saved_value
		if sv is None:
			tmp = self.default
		else:
			tmp = self.fromstring(sv)
		self.dirs = tmp

	def changeConfigValue(self, value, config_key, config_value):
		if isinstance(value, str) and isinstance(config_key, str):
			if value in self.dirs:
				self.dirs[value][config_key] = config_value
			else:
				self.dirs[value] = {config_key : config_value}
			self.changed()

	def getConfigValue(self, value, config_key):
		if isinstance(value, str) and isinstance(config_key, str):
			if value in self.dirs and config_key in self.dirs[value]:
				return self.dirs[value][config_key]
		return None

	def removeConfigValue(self, value, config_key):
		if isinstance(value, str) and isinstance(config_key, str):
			if value in self.dirs and config_key in self.dirs[value]:
				try:
					del self.dirs[value][config_key]
				except KeyError:
					pass
				self.changed()

	def save(self):
		del_keys = []
		for key in self.dirs:
			if not len(self.dirs[key]):
				del_keys.append(key)
		for del_key in del_keys:
			try:
				del self.dirs[del_key]
			except KeyError:
				pass
			self.changed()
		self.saved_value = self.tostring(self.dirs)

class ConfigLocations(ConfigElement):
	def __init__(self, default=None, visible_width=False):
		if not default: default = []
		ConfigElement.__init__(self)
		self.visible_width = visible_width
		self.pos = -1
		self.default = default
		self.locations = []
		self.mountpoints = []
		self.value = default[:]

	def setValue(self, value):
		locations = self.locations
		loc = [x[0] for x in locations if x[3]]
		add = [x for x in value if not x in loc]
		diff = add + [x for x in loc if not x in value]
		locations = [x for x in locations if not x[0] in diff] + [[x, self.getMountpoint(x), True, True] for x in add]
		#locations.sort(key = lambda x: x[0])
		self.locations = locations
		self.changed()

	def getValue(self):
		self.checkChangedMountpoints()
		locations = self.locations
		for x in locations:
			x[3] = x[2]
		return [x[0] for x in locations if x[3]]

	value = property(getValue, setValue)

	def tostring(self, value):
		return str(value)

	def fromstring(self, val):
		return eval(val)

	def load(self):
		sv = self.saved_value
		if sv is None:
			tmp = self.default
		else:
			tmp = self.fromstring(sv)
		locations = [[x, None, False, False] for x in tmp]
		self.refreshMountpoints()
		for x in locations:
			if fileExists(x[0]):
				x[1] = self.getMountpoint(x[0])
				x[2] = True
		self.locations = locations

	def save(self):
		locations = self.locations
		if self.save_disabled or not locations:
			self.saved_value = None
		else:
			self.saved_value = self.tostring([x[0] for x in locations])

	def isChanged(self):
		sv = self.saved_value
		locations = self.locations
		if val is None and not locations:
			return False
		return self.tostring([x[0] for x in locations]) != sv

	def addedMount(self, mp):
		for x in self.locations:
			if x[1] == mp:
				x[2] = True
			elif x[1] is None and fileExists(x[0]):
				x[1] = self.getMountpoint(x[0])
				x[2] = True

	def removedMount(self, mp):
		for x in self.locations:
			if x[1] == mp:
				x[2] = False

	def refreshMountpoints(self):
		self.mountpoints = [p.mountpoint for p in harddiskmanager.getMountedPartitions() if p.mountpoint != "/"]
		self.mountpoints.sort(key = lambda x: -len(x))

	def checkChangedMountpoints(self):
		oldmounts = self.mountpoints
		self.refreshMountpoints()
		newmounts = self.mountpoints
		if oldmounts == newmounts:
			return
		for x in oldmounts:
			if not x in newmounts:
				self.removedMount(x)
		for x in newmounts:
			if not x in oldmounts:
				self.addedMount(x)

	def getMountpoint(self, file):
		file = os_path.realpath(file)+"/"
		for m in self.mountpoints:
			if file.startswith(m):
				return m
		return None

	def handleKey(self, key):
		if key == KEY_LEFT:
			self.pos -= 1
			if self.pos < -1:
				self.pos = len(self.value)-1
		elif key == KEY_RIGHT:
			self.pos += 1
			if self.pos >= len(self.value):
				self.pos = -1
		elif key in (KEY_HOME, KEY_END):
			self.pos = -1

	def getText(self):
		return " ".join(self.value)

	def getMulti(self, selected):
		if not selected:
			valstr = " ".join(self.value)
			if self.visible_width and len(valstr) > self.visible_width:
				return "text", valstr[0:self.visible_width]
			else:
				return "text", valstr
		else:
			i = 0
			valstr = ""
			ind1 = 0
			ind2 = 0
			for val in self.value:
				if i == self.pos:
					ind1 = len(valstr)
				valstr += str(val)+" "
				if i == self.pos:
					ind2 = len(valstr)
				i += 1
			if self.visible_width and len(valstr) > self.visible_width:
				if ind1+1 < self.visible_width/2:
					off = 0
				else:
					off = min(ind1+1-self.visible_width/2, len(valstr)-self.visible_width)
				return "mtext", valstr[off:off+self.visible_width], range(ind1-off,ind2-off)
			else:
				return "mtext", valstr, range(ind1,ind2)

	def onDeselect(self, session):
		self.pos = -1

# nothing.
class ConfigNothing(ConfigSelection):
	def __init__(self):
		ConfigSelection.__init__(self, choices = [("","")])

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
		list.__init__(self)
		self.stored_values = {}

	def save(self):
		for x in self:
			x.save()

	def load(self):
		for x in self:
			x.load()

	def getSavedValue(self):
		res = { }
		for i, val in enumerate(self):
			sv = val.saved_value
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
		return dict([(str(index), value) for index, value in enumerate(self)])

# same as ConfigSubList, just as a dictionary.
# care must be taken that the 'key' has a proper
# str() method, because it will be used in the config
# file.
class ConfigSubDict(dict, object):
	def __init__(self):
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
			sv = val.saved_value
			if sv is not None:
				res[str(key)] = sv
		return res

	def setSavedValue(self, values):
		self.stored_values = dict(values)
		for (key, val) in self.items():
			if str(key) in self.stored_values:
				val.saved_value = self.stored_values[str(key)]

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
		self.__dict__["content"] = ConfigSubsectionContent()
		self.content.items = { }
		self.content.stored_values = { }

	def __setattr__(self, name, value):
		if name == "saved_value":
			return self.setSavedValue(value)
		assert isinstance(value, (ConfigSubsection, ConfigElement, ConfigSubList, ConfigSubDict)), "ConfigSubsections can only store ConfigSubsections, ConfigSubLists, ConfigSubDicts or ConfigElements"
		content = self.content
		content.items[name] = value
		x = content.stored_values.get(name, None)
		if x is not None:
			#print "ok, now we have a new item,", name, "and have the following value for it:", x
			value.saved_value = x
			value.load()

	def __getattr__(self, name):
		return self.content.items[name]

	def getSavedValue(self):
		res = self.content.stored_values
		for (key, val) in self.content.items.items():
			sv = val.saved_value
			if sv is not None:
				res[key] = sv
			elif key in res:
				del res[key]
		return res

	def setSavedValue(self, values):
		values = dict(values)
		self.content.stored_values = values
		for (key, val) in self.content.items.items():
			value = values.get(key, None)
			if value is not None:
				val.saved_value = value

	saved_value = property(getSavedValue, setSavedValue)

	def save(self):
		for x in self.content.items.values():
			x.save()

	def load(self):
		for x in self.content.items.values():
			x.load()

	def dict(self):
		return self.content.items

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
		for (key, val) in sorted(topickle.items(), key=lambda x: int(x[0]) if x[0].isdigit() else x[0].lower()):
			name = '.'.join((prefix, key))
			if isinstance(val, dict):
				self.pickle_this(name, val, result)
			elif isinstance(val, tuple):
				result += [name, '=', str(val[0]), '\n']
			else:
				result += [name, '=', str(val), '\n']

	def pickle(self):
		result = []
		self.pickle_this("config", self.saved_value, result)
		return ''.join(result)

	def unpickle(self, lines, base_file=True):
		tree = { }
		configbase = tree.setdefault("config", {})
		for l in lines:
			if not l or l[0] == '#':
				continue

			result = l.split('=', 1)
			if len(result) != 2:
				continue
			(name, val) = result
			val = val.strip()

			#convert old settings
			if l.startswith("config.Nims."):
				tmp = name.split('.')
				if tmp[3] == "cable":
					tmp[3] = "dvbc"
				elif tmp[3].startswith ("cable"):
					tmp[3] = "dvbc." + tmp[3]
				elif tmp[3].startswith("terrestrial"):
					tmp[3] = "dvbt." + tmp[3]
				else:
					if tmp[3] not in ('dvbs', 'dvbc', 'dvbt', 'multiType'):
						tmp[3] = "dvbs." + tmp[3]
				name =".".join(tmp)

			names = name.split('.')

			base = configbase

			for n in names[1:-1]:
				base = base.setdefault(n, {})

			base[names[-1]] = val

			if not base_file: # not the initial config file..
				#update config.x.y.value when exist
				try:
					configEntry = eval(name)
					if configEntry is not None:
						configEntry.value = val
				except (SyntaxError, KeyError):
					pass

		# we inherit from ConfigSubsection, so ...
		#object.__setattr__(self, "saved_value", tree["config"])
		if "config" in tree:
			self.setSavedValue(tree["config"])

	def saveToFile(self, filename):
		text = self.pickle()
		try:
			import os
			f = open(filename + ".writing", "w")
			f.write(text)
			f.flush()
			os.fsync(f.fileno())
			f.close()
			os.rename(filename + ".writing", filename)
		except IOError:
			print "Config: Couldn't write %s" % filename

	def loadFromFile(self, filename, base_file=True):
		self.unpickle(open(filename, "r"), base_file)

config = Config()
config.misc = ConfigSubsection()

class ConfigFile:
	def __init__(self):
		pass

	CONFIG_FILE = resolveFilename(SCOPE_CONFIG, "settings")

	def load(self):
		try:
			config.loadFromFile(self.CONFIG_FILE, True)
		except IOError, e:
			print "unable to load config (%s), assuming defaults..." % str(e)

	def save(self):
#		config.save()
		config.saveToFile(self.CONFIG_FILE)

	def __resolveValue(self, pickles, cmap):
		key = pickles[0]
		if cmap.has_key(key):
			if len(pickles) > 1:
				return self.__resolveValue(pickles[1:], cmap[key].dict())
			else:
				return str(cmap[key].value)
		return None

	def getResolvedKey(self, key):
		names = key.split('.')
		if len(names) > 1:
			if names[0] == "config":
				ret = self.__resolveValue(names[1:], config.content.items)
				if ret and len(ret) or ret == "":
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

def updateConfigElement(element, newelement):
	newelement.value = element.value
	return newelement

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

cec_limits = [(0,15),(0,15),(0,15),(0,15)]
class ConfigCECAddress(ConfigSequence):
	def __init__(self, default, auto_jump = False):
		ConfigSequence.__init__(self, seperator = ".", limits = cec_limits, default = default)
		self.block_len = [len(str(x[1])) for x in self.limits]
		self.marked_block = 0
		self.overwrite = True
		self.auto_jump = auto_jump

	def handleKey(self, key):
		if key == KEY_LEFT:
			if self.marked_block > 0:
				self.marked_block -= 1
			self.overwrite = True

		elif key == KEY_RIGHT:
			if self.marked_block < len(self.limits)-1:
				self.marked_block += 1
			self.overwrite = True

		elif key == KEY_HOME:
			self.marked_block = 0
			self.overwrite = True

		elif key == KEY_END:
			self.marked_block = len(self.limits)-1
			self.overwrite = True

		elif key in KEY_NUMBERS or key == KEY_ASCII:
			if key == KEY_ASCII:
				code = getPrevAsciiCode()
				if code < 48 or code > 57:
					return
				number = code - 48
			else:
				number = getKeyNumber(key)
			oldvalue = self._value[self.marked_block]

			if self.overwrite:
				self._value[self.marked_block] = number
				self.overwrite = False
			else:
				oldvalue *= 10
				newvalue = oldvalue + number
				if self.auto_jump and newvalue > self.limits[self.marked_block][1] and self.marked_block < len(self.limits)-1:
					self.handleKey(KEY_RIGHT)
					self.handleKey(key)
					return
				else:
					self._value[self.marked_block] = newvalue

			if len(str(self._value[self.marked_block])) >= self.block_len[self.marked_block]:
				self.handleKey(KEY_RIGHT)

			self.validate()
			self.changed()

	def genText(self):
		value = ""
		block_strlen = []
		for i in self._value:
			block_strlen.append(len(str(i)))
			if value:
				value += self.seperator
			value += str(i)
		leftPos = sum(block_strlen[:self.marked_block])+self.marked_block
		rightPos = sum(block_strlen[:(self.marked_block+1)])+self.marked_block
		mBlock = range(leftPos, rightPos)
		return value, mBlock

	def getMulti(self, selected):
		(value, mBlock) = self.genText()
		if self.enabled:
			return "mtext"[1-selected:], value, mBlock
		else:
			return "text", value

	def getHTML(self, id):
		# we definitely don't want leading zeros
		return '.'.join(["%d" % d for d in self.value])

class ConfigAction(ConfigElement):
	def __init__(self, action, *args):
		ConfigElement.__init__(self)
		self.value = "(OK)"
		self.action = action
		self.actionargs = args
	def handleKey(self, key):
		if (key == KEY_OK):
			self.action(*self.actionargs)
	def getMulti(self, dummy):
		pass
