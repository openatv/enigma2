from Components.ActionMap import ActionMap
from Components.Harddisk import harddiskmanager
from Components.MenuList import MenuList
from Components.Storage import StorageDevice
from Components.Task import job_manager
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen


class HarddiskSelection(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		self.curentservice = None
		self.setTitle(_("Format Storage Device"))
		if harddiskmanager.HDDCount() == 0:
			tlist = [(_("no storage devices found"), 0)]
			self["hddlist"] = MenuList(tlist)
		else:
			self["hddlist"] = MenuList(harddiskmanager.HDDList())

		self["actions"] = ActionMap(["OkCancelActions"],
		{
			"ok": self.keyOK,
			"cancel": self.close
		})

	def hddConfirmed(self, confirmed):
		if confirmed:
			options = {"partitionType": "gpt", "partitions": [{"fsType": "ext4"}], "mountDevice": True}
			selection = self["hddlist"].getCurrent()[1]
			disk = selection.device
			storageDevice = {
				"devicePoint": f"/dev/{disk}",
				"disk": disk,
				"device": disk,
				"size": 0
			}
			self.storageDevice = StorageDevice(storageDevice)
			try:
				job_manager.AddJob(self.storageDevice.createInitializeJob(options))
				for job in job_manager.getPendingJobs():
					if job.name in (_("Initializing storage device...")):
						self.showJobView(job)
						return
			except Exception as ex:
				self.session.openWithCallback(self.close, MessageBox, str(ex), type=MessageBox.TYPE_ERROR, timeout=10)
		self.close()

	def keyOK(self):
		selection = self["hddlist"].getCurrent()
		if selection[1] != 0:
			self.session.openWithCallback(self.hddConfirmed, MessageBox, _("Do you really want to format the device in the Linux file system?\nAll data on the device will be lost!"))

	def showJobView(self, job):
		from Screens.TaskView import JobView
		job_manager.in_background = False
		self.session.openWithCallback(self.JobViewCB, JobView, job, cancelable=False, afterEventChangeable=False, afterEvent="close")

	def JobViewCB(self, in_background):
		job_manager.in_background = in_background
		self.close()
