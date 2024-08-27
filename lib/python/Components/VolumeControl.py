from enigma import eDVBVolumecontrol, eTimer

from GlobalActions import globalActionMap
from Components.config import ConfigBoolean, ConfigInteger, ConfigSelectionNumber, ConfigSubsection, config
from Screens.VolumeControl import Mute, Volume


# NOTE: This code does not remember the current volume as other code can change
# 	the volume directly. Always get the current volume from the driver.
#
class VolumeControl:
	"""Volume control, handles volumeUp, volumeDown, volumeMute, and other actions and display a corresponding dialog."""
	instance = None

	def __init__(self, session):
		def updateStep(configElement):
			self.volumeControl.setVolumeSteps(configElement.value)

		if VolumeControl.instance:
			print("[VolumeControl] Error: Only one VolumeControl instance is allowed!")
		else:
			VolumeControl.instance = self
			global globalActionMap
			globalActionMap.actions["volumeUp"] = self.keyVolumeUp
			globalActionMap.actions["volumeUpLong"] = self.keyVolumeLong
			globalActionMap.actions["volumeUpStop"] = self.keyVolumeStop
			globalActionMap.actions["volumeDown"] = self.keyVolumeDown
			globalActionMap.actions["volumeDownLong"] = self.keyVolumeLong
			globalActionMap.actions["volumeDownStop"] = self.keyVolumeStop
			globalActionMap.actions["volumeMute"] = self.keyVolumeMute
			globalActionMap.actions["volumeMuteLong"] = self.keyVolumeMuteLong
			self.volumeControl = eDVBVolumecontrol.getInstance()
			config.volumeControl = ConfigSubsection()
			config.volumeControl.volume = ConfigInteger(default=20, limits=(0, 100))
			config.volumeControl.mute = ConfigBoolean(default=False)
			config.volumeControl.pressStep = ConfigSelectionNumber(1, 10, 1, default=1)
			config.volumeControl.pressStep.addNotifier(updateStep, initial_call=True, immediate_feedback=True)
			config.volumeControl.longStep = ConfigSelectionNumber(1, 10, 1, default=5)
			config.volumeControl.hideTimer = ConfigSelectionNumber(1, 10, 1, default=3)
			self.muteDialog = session.instantiateDialog(Mute)
			self.muteDialog.setAnimationMode(0)
			self.volumeDialog = session.instantiateDialog(Volume)
			self.volumeDialog.setAnimationMode(0)
			self.hideTimer = eTimer()
			self.hideTimer.callback.append(self.hideVolume)
			if config.volumeControl.mute.value:
				self.volumeControl.volumeMute()
				self.muteDialog.show()
			volume = config.volumeControl.volume.value
			self.volumeDialog.setValue(volume)
			self.volumeControl.setVolume(volume, volume)
			# Compatibility interface for shared plugins.
			self.volctrl = self.volumeControl
			self.hideVolTimer = self.hideTimer

	def keyVolumeUp(self):
		self.volumeControl.volumeUp(0, 0)
		self.updateVolume()

	def keyVolumeDown(self):
		self.volumeControl.volumeDown(0, 0)
		self.updateVolume()

	def keyVolumeLong(self):
		self.volumeControl.setVolumeSteps(config.volumeControl.longStep.value)

	def keyVolumeStop(self):
		self.volumeControl.setVolumeSteps(config.volumeControl.pressStep.value)

	def keyVolumeMute(self):  # This will toggle the current mute status. Mute will not be activated if the volume is at 0.
		volume = self.volumeControl.getVolume()
		isMuted = self.volumeControl.isMuted()
		if volume or (volume == 0 and isMuted):
			self.volumeControl.volumeToggleMute()
			if self.volumeControl.isMuted():
				self.muteDialog.show()
				self.volumeDialog.hide()
			else:
				self.muteDialog.hide()
				self.volumeDialog.setValue(volume)
				self.volumeDialog.show()
			self.hideTimer.start(config.volumeControl.hideTimer.value * 1000, True)

	def keyVolumeMuteLong(self):  # Long press MUTE will keep the mute icon on-screen without a timeout.
		if self.volumeControl.isMuted():
			self.hideTimer.stop()

	def updateVolume(self):
		if self.volumeControl.isMuted():
			self.keyVolumeMute()  # Unmute.
		else:
			self.volumeDialog.setValue(self.volumeControl.getVolume())
			self.volumeDialog.show()
			self.hideTimer.start(config.volumeControl.hideTimer.value * 1000, True)

	def hideVolume(self):
		self.muteDialog.hide()
		self.volumeDialog.hide()

	def saveVolumeState(self):
		config.volumeControl.mute.value = self.volumeControl.isMuted()
		config.volumeControl.volume.setValue(self.volumeControl.getVolume())
		config.volumeControl.save()

	def showMute(self):  # This method is only called by InfoBarGenerics.py:
		if self.volumeControl.isMuted():
			self.muteDialog.show()
			self.hideTimer.start(config.volumeControl.hideTimer.value * 1000, True)

	# These methods are provided for compatibly with shared plugins.
	#
	def volUp(self):
		self.keyVolumeUp()

	def volDown(self):
		self.keyVolumeDown()

	def volMute(self):
		self.keyVolumeMute()

	def volSave(self):
		pass
