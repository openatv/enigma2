from Screens.InputBox import InputBox as InputBoxBase
from Components.ActionMap import ActionMap

class InputBox(InputBoxBase):
	def __init__(self, session, title="", windowTitle=None, useableChars=None, overwrite=False, firstpos_end=False, allmarked=True, **kwargs):
		InputBoxBase.__init__(self, session, title=title, windowTitle=windowTitle, useableChars=useableChars, maxSize=overwrite, currPos=firstpos_end and len(kwargs["text"].decode("utf-8")) or 0, allMarked=allmarked, **kwargs)

		# Add action in InputBoxBase on KEY_DOWN
		self["actions"].actions["down"] = self.keyTab
		self["seekbarActions"] = ActionMap(["InfobarSeekActions"], {
			# Dummy actions for "seekBack" and "seekFwd"
			# They are already covered in InputBoxBase by actions
			# on "make", these actions are on "break"
			"seekBack": lambda: None,
			"seekFwd": lambda: None,
			# Toggle insert/overwrite action for remote
			"playpauseService": self.keyInsert,
		}, -1)

class InputBoxWide(InputBox):
	skin = """
		<screen position="center,center" size=" 1100, 95" title="Input">
			<widget name="text" position="10,10" size="1080,22" font="Regular;18" />
			<widget name="input" position="10,50" size="1080,24" font="Regular;22" />
		</screen>"""
