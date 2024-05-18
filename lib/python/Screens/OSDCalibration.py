from os import W_OK, access
from os.path import exists

from enigma import eAVControl, getDesktop

from Components.ActionMap import HelpableActionMap
from Components.AVSwitch import avSwitch
from Components.config import ConfigNumber, ConfigSelection, ConfigSelectionInteger, ConfigSlider, ConfigSubsection, ConfigText, ConfigYesNo, NoSave, config, configfile
from Components.Label import Label
from Components.SystemInfo import BoxInfo
from Components.Sources.StaticText import StaticText
from Screens.Setup import Setup
from Tools.Directories import fileReadLine, fileWriteLine

MODULE_NAME = __name__.split(".")[-1]


def InitOSDCalibration():
	def setPositionParameter(parameter, value):
		if BoxInfo.getItem("CanChangeOsdPosition"):
			fileWriteLine(f"/proc/stb/fb/dst_{parameter}", f"{value:08x}\n", source=MODULE_NAME)
			fileName = "/proc/stb/fb/dst_apply"
			if exists(fileName):
				fileWriteLine(fileName, "1", source=MODULE_NAME)
		elif BoxInfo.getItem("CanChangeOsdPositionAML"):
			value = f"{config.osd.dst_left.value} {config.osd.dst_top.value} {config.osd.dst_width.value} {config.osd.dst_height.value}"
			fileWriteLine("/sys/class/graphics/fb0/window_axis", value, source=MODULE_NAME)
			fileWriteLine("/sys/class/graphics/fb0/free_scale", "0x10001", source=MODULE_NAME)

	def setLeft(configElement):
		setPositionParameter("left", configElement.value)

	def setTop(configElement):
		setPositionParameter("top", configElement.value)

	def setWidth(configElement):
		setPositionParameter("width", configElement.value)

	def setHeight(configElement):
		setPositionParameter("height", configElement.value)

	def setAlpha(configElement):
		value = configElement.value
		print(f"[OSDCalibration] Setting OSD alpha to {value}.")
		config.av.osd_alpha.setValue(value)
		eAVControl.getInstance().setOSDAlpha(value)

	def set3DMode(configElement):
		value = configElement.value
		print(f"[OSDCalibration] Setting 3D mode to {value}.")
		if BoxInfo.getItem("CanUse3DModeChoices"):
			choices = fileReadLine("/proc/stb/fb/3dmode_choices", "", source=MODULE_NAME).split()
			if value not in choices:
				match value:
					case "sidebyside":
						value = "sbs"
					case "topandbottom":
						value = "tab"
					case "auto":
						value = "off"
			fileWriteLine("/proc/stb/fb/3dmode", value, source=MODULE_NAME)

	def set3DZnorm(configElement):
		value = configElement.value
		print(f"[OSDCalibration] Setting 3D depth to {value}.")
		fileWriteLine("/proc/stb/fb/znorm", str(value), source=MODULE_NAME)

	BoxInfo.setItem("CanChangeOsdPosition", access("/proc/stb/fb/dst_left", W_OK))
	BoxInfo.setItem("CanChangeOsdPositionAML", access("/sys/class/graphics/fb0/free_scale", W_OK))  # Is this the same as BoxInfo.getItem("AmlogicFamily")?
	BoxInfo.setItem("CanChangeOsdAlpha", eAVControl.getInstance().hasOSDAlpha())
	BoxInfo.setItem("OSDCalibration", BoxInfo.getItem("CanChangeOsdPosition") or BoxInfo.getItem("CanChangeOsdPositionAML") or BoxInfo.getItem("CanChangeOsdAlpha"))
	BoxInfo.setItem("OSD3DCalibration", access("/proc/stb/fb/3dmode", W_OK))
	print(f"[OSDCalibration] Setting OSD position to (X={config.osd.dst_left.value}, Y={config.osd.dst_top.value}) and size to (W={config.osd.dst_width.value}, H={config.osd.dst_height.value}).")
	config.osd.dst_left.addNotifier(setLeft)
	config.osd.dst_top.addNotifier(setTop)
	config.osd.dst_width.addNotifier(setWidth)
	config.osd.dst_height.addNotifier(setHeight)
	if BoxInfo.getItem("CanChangeOsdAlpha"):
		config.osd.alpha.addNotifier(setAlpha)
	if BoxInfo.getItem("OSD3DCalibration"):
		config.osd.threeDmode.addNotifier(set3DMode)
		config.osd.threeDznorm.addNotifier(set3DZnorm)


class OSDCalibration(Setup):
	match getDesktop(0).size().width():  # This skin shouldn't be scaled as we need pixel perfect accuracy at each resolution!
		case 1920:  # 1920x1080 resolution.
			buttonHeight = 60
			colorButtonWidth = 270
			fontSize = 30
			iconButtonWidth = 120
			itemHeight = 37
			menuFontSize = 52
			spacer = 38
			spacing = 15
			textHeight = 150
		case 1280:  # 1280x720 resolution.
			buttonHeight = 40
			colorButtonWidth = 180
			fontSize = 20
			iconButtonWidth = 80
			itemHeight = 35
			menuFontSize = 25
			spacer = 25
			spacing = 10
			textHeight = 100
		case 1024:  # 1024x576 resolution.
			buttonHeight = 22
			colorButtonWidth = 140
			fontSize = 18
			iconButtonWidth = 70
			itemHeight = 25
			menuFontSize = 20
			spacer = 10
			spacing = 10
			textHeight = 80
		case _:  # 720x576 resolution.
			buttonHeight = 22
			colorButtonWidth = 140
			fontSize = 18
			iconButtonWidth = 70
			itemHeight = 25
			menuFontSize = 20
			spacer = 10
			spacing = 10
			textHeight = 80
	skin = f"""
	<screen name="OSDCalibration" title="OSD Calibration Settings" position="fill" backgroundColor="#00000000" >
		<eRectangle position="0,0" size="e,e" borderColor="#00FF0000" backgroundColor="#00000000" borderWidth="1" zPosition="+0" />
		<eRectangle position="25,25" size="e-50,e-50" backgroundColor="#00000000" borderColor="#0000FF00" borderWidth="1" zPosition="+1" />
		<eRectangle position="50,50" size="e-100,e-100" backgroundColor="#00000000" borderColor="#00FFFF00" borderWidth="1" zPosition="+2" />
		<eRectangle position="75,75" size="e-150,e-150" backgroundColor="#00000000" borderColor="#000000FF" borderWidth="1" zPosition="+3" />
		<widget name="text" position="85,85" size="e-170,{textHeight}" font="Regular;{fontSize}" foregroundColor="#00FFFF00" transparent="1" verticalAlignment="center" zPosition="+4" />
		<widget name="config" position="300,{85 + textHeight + spacer}" size="e-600,{itemHeight * 7}" font="Regular;{menuFontSize}" itemHeight="{itemHeight}" transparent="1" zPosition="+4" />
		<widget name="footnote" position="0,0" size="0,0" />
		<widget name="description" position="300,{85 + textHeight + spacer + (itemHeight * 7) + spacer}" size="e-600,{textHeight}" font="Regular;{fontSize}" foregroundColor="#00FFFFFF" transparent="1" verticalAlignment="center" zPosition="+4" />
		<panel position="85,e-{85 + buttonHeight}" size="e-170,{buttonHeight}" layout="horizontal" spacing="{spacing}">
			<widget source="key_red" render="Label" position="left" size="{colorButtonWidth},{buttonHeight}" backgroundColor="key_red" conditional="key_red" font="Regular;{fontSize}" foregroundColor="key_text" horizontalAlignment="center" verticalAlignment="center" zPosition="+4">
				<convert type="ConditionalShowHide" />
			</widget>
			<widget source="key_green" render="Label" position="left" size="{colorButtonWidth},{buttonHeight}" backgroundColor="key_green" conditional="key_green" font="Regular;{fontSize}" foregroundColor="key_text" horizontalAlignment="center" verticalAlignment="center" zPosition="+4">
				<convert type="ConditionalShowHide" />
			</widget>
			<widget source="key_yellow" render="Label" position="left" size="{colorButtonWidth},{buttonHeight}" backgroundColor="key_yellow" conditional="key_yellow" font="Regular;{fontSize}" foregroundColor="key_text" horizontalAlignment="center" verticalAlignment="center" zPosition="+4">
				<convert type="ConditionalShowHide" />
			</widget>
			<widget source="key_help" render="Label" position="right" size="{iconButtonWidth},{buttonHeight}" backgroundColor="key_back" conditional="key_help" font="Regular;{fontSize}" foregroundColor="key_text" horizontalAlignment="center" verticalAlignment="center" zPosition="+4">
				<convert type="ConditionalShowHide" />
			</widget>
			<widget source="key_menu" render="Label" position="right" size="{iconButtonWidth},{buttonHeight}" backgroundColor="key_back" conditional="key_menu" font="Regular;{fontSize}" foregroundColor="key_text" horizontalAlignment="center" verticalAlignment="center" zPosition="+4">
				<convert type="ConditionalShowHide" />
			</widget>
		</panel>
	</screen>"""

	def __init__(self, session):
		Setup.__init__(self, session, "OSDCalibration")
		self.skinName = ["OSDCalibration"]  # Don't use the standard Setup screen.
		text = []
		text.append(_("Before changing these settings try to disable any overscan settings on th TV / display screen. To calibrate the On-Screen-Display (OSD) adjust the position and size values until the red box is *just* visible and touches the edges of the screen."))
		text.append(_("When the red box is correctly visible press the GREEN button to save the settings and exit."))
		self["text"] = Label("\n".join(text))
		self.screenWidthScale = getDesktop(0).size().width() / 720.0
		self.screenHeightScale = getDesktop(0).size().height() / 576.0

	def keyLeft(self):
		Setup.keyLeft(self)
		if BoxInfo.getItem("CanChangeOsdPosition"):
			self.setPreviewPosition()

	def keyRight(self):
		Setup.keyRight(self)
		if BoxInfo.getItem("CanChangeOsdPosition"):
			self.setPreviewPosition()

	def setPreviewPosition(self):
		left = config.osd.dst_left.value
		top = config.osd.dst_top.value
		width = config.osd.dst_width.value
		height = config.osd.dst_height.value
		while width + (left / self.screenWidthScale) >= 720.5 or width + left > 720:
			width -= 1
		while height + (top / self.screenHeightScale) >= 576.5 or height + top > 576:
			height -= 1
		print(f"[OSDCalibration] Setting OSD position to (X={left}, Y={top}) and size to (W={width}, H={height}).")
		config.osd.dst_left.setValue(left)
		config.osd.dst_top.setValue(top)
		config.osd.dst_width.setValue(width)
		config.osd.dst_height.setValue(height)
		for entry in self["config"].getList():
			self["config"].invalidate(entry)

	def run(self):  # This is called by the Wizard.
		config.osd.save()
		configfile.save()
		self.close()
