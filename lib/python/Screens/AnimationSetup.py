from enigma import getGraphicsInfo, setAnimation_current, setAnimation_current_listbox, setAnimation_profiles, setAnimation_speed, setAnimation_toast_speed, supportsEGLAnimations

from Components.ActionMap import ActionMap
from Components.Sources.StaticText import StaticText
from Components.SystemInfo import BoxInfo
from Components.config import config, ConfigSelection, ConfigSelectionNumber, ConfigSubsection, ConfigYesNo
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from Screens.Setup import Setup


def hasE2EGLAnimations():
	graphicsInfo = getGraphicsInfo()
	return bool(supportsEGLAnimations()
		and BoxInfo.getItem("e2egl", False)
		and graphicsInfo.get("backend", "") == "e2egl"
		and graphicsInfo.get("animations_supported", 0))


E2EGL_ANIMATIONS = hasE2EGLAnimations()

ANIMATION_DEFAULT = 15 if E2EGL_ANIMATIONS else 0
ANIMATION_SPEED_DEFAULT = 15
ANIMATION_TOAST_SPEED_DEFAULT = 10
ANIMATION_SPEED_MIN = 5 if BoxInfo.getItem("machinebuild") in ("dreamone", "dreamtwo") else 15
ANIMATION_SPEED_MAX = 30
ANIMATION_CLASSIC_GROUP = 100

ANIMATION_CHOICES = [
	(0, _("Disable Animations")),
	(15, _("Basis animation")),
	(16, _("Modern adaptive")),
	(17, _("Fade in / fade out")),
	(18, _("Dialog pop")),
	(19, _("Toast slide")),
	(20, _("Side sheet")),
	(21, _("Zoom and fade")),
	(ANIMATION_CLASSIC_GROUP, _("Classic animation")),
]

CLASSIC_ANIMATION_CHOICES = [
	(1, _("Simple fade")),
	(2, _("Simple zoom")),
	(3, _("Grow drop")),
	(4, _("Grow from left")),
	(5, _("Extrude from left")),
	(6, _("Popup")),
	(7, _("Slide drop")),
	(8, _("Slide from left")),
	(9, _("Slide left to right")),
	(10, _("Slide right to left")),
	(11, _("Slide top to bottom")),
	(12, _("Zoom from left")),
	(13, _("Zoom from right")),
	(14, _("Stripes")),
]

if not hasattr(config.misc, "animation"):
	config.misc.animation = ConfigSubsection()
config.misc.animation.default = ConfigSelection(choices=ANIMATION_CHOICES, default=ANIMATION_DEFAULT)
config.misc.animation.classic = ConfigSelection(choices=CLASSIC_ANIMATION_CHOICES, default=1)
config.misc.animation.speed = ConfigSelectionNumber(ANIMATION_SPEED_MIN, ANIMATION_SPEED_MAX, 1, default=ANIMATION_SPEED_DEFAULT)
config.misc.animation.toast_speed = ConfigSelectionNumber(5, ANIMATION_SPEED_MAX, 1, default=ANIMATION_TOAST_SPEED_DEFAULT)
config.misc.animation.listbox = ConfigYesNo(default=False)
config.misc.animation.profiles = ConfigYesNo(default=True)
config.misc.animation.dialog = ConfigSelection(choices=ANIMATION_CHOICES, default=18)
config.misc.animation.popup = ConfigSelection(choices=ANIMATION_CHOICES, default=16)
config.misc.animation.toast = ConfigSelection(choices=ANIMATION_CHOICES, default=17 if E2EGL_ANIMATIONS else 0)

ANIMATION_CONFIGS = (
	config.misc.animation.default,
	config.misc.animation.classic,
	config.misc.animation.speed,
	config.misc.animation.toast_speed,
	config.misc.animation.listbox,
	config.misc.animation.profiles,
	config.misc.animation.dialog,
	config.misc.animation.popup,
	config.misc.animation.toast,
)

animationPaused = False
origShow = None
origDoClose = None


def _animationValue(configElement):
	try:
		return int(configElement.value)
	except (TypeError, ValueError):
		return 0


def _animationSelectionValue(configElement):
	value = _animationValue(configElement)
	return _animationValue(config.misc.animation.classic) if value == ANIMATION_CLASSIC_GROUP else value


def applyAnimationSettings():
	setAnimation_current(_animationSelectionValue(config.misc.animation.default))
	setAnimation_speed(int(config.misc.animation.speed.value))
	setAnimation_toast_speed(int(config.misc.animation.toast_speed.value))
	setAnimation_current_listbox(1 if config.misc.animation.listbox.value else 0)
	setAnimation_profiles(
		1 if config.misc.animation.profiles.value else 0,
		_animationSelectionValue(config.misc.animation.dialog),
		_animationSelectionValue(config.misc.animation.popup),
		_animationSelectionValue(config.misc.animation.toast))


class AnimationSetup(Setup):
	def __init__(self, session):
		Setup.__init__(self, session, "AnimationSetup")
		if "key_blue" not in self:
			self["key_blue"] = StaticText(_("Preview"))
		else:
			self["key_blue"].setText(_("Preview"))
		self["animationActions"] = ActionMap(["ColorActions"], {
			"blue": self.keyPreview
		}, -2)
		self.addSaveNotifier(applyAnimationSettings)
		self.onClose.append(applyAnimationSettings)

	def changedEntry(self):
		Setup.changedEntry(self)
		if self.getCurrentItem() in ANIMATION_CONFIGS:
			applyAnimationSettings()

	def saveAll(self):
		for item in ANIMATION_CONFIGS:
			item.save()
		return Setup.saveAll(self)

	def keyCancel(self):
		self.cancelAnimationSetup(())

	def closeRecursive(self):
		self.cancelAnimationSetup((True,))

	def cancelAnimationSetup(self, closeParameters):
		if any(item.isChanged() for item in ANIMATION_CONFIGS):
			self.closeParameters = closeParameters
			self.session.openWithCallback(self.cancelConfirm, MessageBox, self.cancelMsg, default=False, type=MessageBox.TYPE_YESNO)
		else:
			self.close(*closeParameters)

	def cancelConfirm(self, result):
		if not result:
			return
		for item in ANIMATION_CONFIGS:
			item.cancel()
		applyAnimationSettings()
		if not hasattr(self, "closeParameters"):
			self.closeParameters = ()
		self.close(*self.closeParameters)

	def keyPreview(self):
		current = self.getCurrentItem()
		if current in ANIMATION_CONFIGS and current is not config.misc.animation.speed and current is not config.misc.animation.profiles and current is not config.misc.animation.listbox:
			previewAnimation = _animationSelectionValue(current)
		else:
			previewAnimation = _animationSelectionValue(config.misc.animation.default)
		setAnimation_current(previewAnimation)
		self.session.openWithCallback(self.previewClosed, MessageBox, _("Animation preview"), MessageBox.TYPE_INFO, timeout=3)

	def previewClosed(self, *result):
		applyAnimationSettings()


def checkAttrib(screen, paused):
	global animationPaused
	if animationPaused is paused and hasattr(screen, "skinAttributes") and screen.skinAttributes:
		for (attr, value) in screen.skinAttributes:
			if attr == "animationPaused" and value in ("1", "on"):
				return True
	return False


def screenShow(screen):
	global animationPaused
	if animationPaused:
		setAnimation_current(0)

	origShow(screen)

	if checkAttrib(screen, False):
		animationPaused = True


def screenDoClose(screen):
	global animationPaused
	if checkAttrib(screen, True):
		animationPaused = False
		applyAnimationSettings()
	origDoClose(screen)


def InitAnimationSetup():
	applyAnimationSettings()

	if not E2EGL_ANIMATIONS:
		return

	global origShow, origDoClose
	if origShow is None:
		origShow = Screen.show
	if origDoClose is None:
		origDoClose = Screen.doClose
	Screen.show = screenShow
	Screen.doClose = screenDoClose
