import os
from Tools.HardwareInfo import HardwareInfo
from Tools.Directories import SCOPE_SKIN, resolveFilename

class RcModel:
        RcModels = {}

	def __init__(self):
		self.model = HardwareInfo().get_device_model()
		# cfg files has modelname  rcname entries.
		# modelname is boxname optionally followed by .rctype
		for line in open((resolveFilename(SCOPE_SKIN, 'rc_models/rc_models.cfg')), 'r'):
			if line.startswith(self.model):
				m, r = line.strip().split()
				self.RcModels[m] = r

	def rcIsDefault(self):
		# Default RC can only happen with DMM type remote controls...
		return self.model.startswith('dm')

	def getRcFile(self, ext):
		# check for rc/type every time so rctype changes will be noticed
		if os.path.exists('/proc/stb/ir/rc/type'):
			rc = open('/proc/stb/ir/rc/type').read().strip()
			modeltype = '%s.%s' % (self.model, rc)
		else:
			modeltype = None

		if modeltype is not None and modeltype in self.RcModels.keys():
			remote = self.RcModels[modeltype]
		elif self.model in self.RcModels.keys():
			remote = self.RcModels[self.model]
		else:
			remote = 'dmm'	# default. Assume files for dmm exists
		f = resolveFilename(SCOPE_SKIN, 'rc_models/' + remote + '.' + ext)
		if not os.path.exists(f):
			f = resolveFilename(SCOPE_SKIN, 'rc_models/dmm.' + ext)
		return f

	def getRcImg(self):
		return self.getRcFile('png')

	def getRcPositions(self):
		return self.getRcFile('xml')

rc_model = RcModel()
