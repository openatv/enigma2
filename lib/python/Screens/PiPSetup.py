from Screens.Screen import Screen
from Components.ActionMap import NumberActionMap
from Components.Label import Label

# this is not so great.
MAX_X = 720
MAX_Y = 576
MAX_W = MAX_X * 3 / 4
MAX_H = MAX_Y * 3 / 4
MIN_W = MAX_X / 8
MIN_H = MAX_Y / 8

def clip(val, min, max):
	if min <= val <= max:
		return val
	if min <= val:
		return max
	return min

class PiPSetup(Screen):
	def __init__(self, session, pip):
		Screen.__init__(self, session)
		
		self.pip = pip
		
		self.pos = (self.pip.instance.position().x(), self.pip.instance.position().y())
		self.size = self.pip.getSize()

		self.orgpos = self.pos
		self.orgsize = self.size
		
		self.resize = 100

		self["text"] = Label(_("Please use direction keys to move the PiP window.\nPress Bouquet +/- to resize the window.\nPress OK to go back to the TV mode or EXIT to cancel the moving."))

		self["actions"] = NumberActionMap(["PiPSetupActions", "NumberActions"], 
		{
			"ok": self.go,
			"cancel": self.cancel,
			"up": self.up,
			"down": self.down,
			"left": self.left,
			"right": self.right,
			"size+": self.bigger,
			"size-": self.smaller,
			"1": self.keyNumberGlobal,
			"2": self.keyNumberGlobal,
			"3": self.keyNumberGlobal,
			"4": self.keyNumberGlobal,
			"5": self.keyNumberGlobal,
			"6": self.keyNumberGlobal,
			"7": self.keyNumberGlobal,
			"8": self.keyNumberGlobal,
			"9": self.keyNumberGlobal,
			"0": self.keyNumberGlobal
		}, -1)
		
	def go(self):
		self.close()
	
	def cancel(self):
		self.pos = self.orgpos
		self.size = self.orgsize
		self.setPiPPosition()
		self.close()
	
	def setPiPPosition(self):
		self.pip.move(self.pos[0], self.pos[1])
		self.pip.resize(self.size[0], self.size[1])

	def resizePiP(self, resize):
		resize += 100 # resize is in percent, so resize=+20 means: 120%
		
		oldsize = self.size
		w = clip(self.size[0] * resize / 100, MIN_W, MAX_W)
		h = clip(self.size[1] * resize / 100, MIN_H, MAX_H)
		
		# calculate offset from center
		mx = (oldsize[0] - w) / 2
		my = (oldsize[1] - h) / 2
		
		self.size = (w, h)
		# reclip, account for new center
		self.moveRelative(x=mx, y=my)
	
	def moveRelative(self, x=0, y=0):
		self.pos = (clip(self.pos[0] + x, 0, MAX_X - self.size[0]), clip(self.pos[1] + y, 0, MAX_Y - self.size[1]))
		self.setPiPPosition()
	
	def up(self):
		self.moveRelative(y=-32)

	def down(self):
		self.moveRelative(y=+32)
	
	def left(self):
		self.moveRelative(x=-24)
	
	def right(self):
		self.moveRelative(x=+24)
	
	def bigger(self):
		self.resizePiP(+10)
	
	def smaller(self):
		self.resizePiP(-10)
	
	def keyNumberGlobal(self, number):
		
		if number > 0:
			colsize = MAX_X / 3
			rowsize = MAX_Y / 3
			col = (number-1) % 3
			row = (number-1) / 3

			self.size = (180, 135)

			# offset to keep center
			ox = (colsize - self.size[0]) / 2
			oy = (rowsize - self.size[1]) / 2

			self.pos = (col * colsize + ox, row * rowsize + oy)
		else:
			# restore old position
			self.pos = self.orgpos
			self.size = self.orgsize
		# reclip
		self.moveRelative()
