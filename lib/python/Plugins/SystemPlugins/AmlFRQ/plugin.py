from glob import glob
from os.path import exists, join
from re import search

from enigma import eTimer

from Screens import Standby
from Components.ActionMap import HelpableActionMap
from Components.config import ConfigSelection, ConfigSubsection, config
from Components.Label import Label
from Components.Sources.StaticText import StaticText
from Plugins.Plugin import PluginDescriptor
from Screens.Setup import Setup


class CpuControl:
	CPUFREQ_PATH = "/sys/devices/system/cpu/cpufreq"
	DDR_PATH = "/sys/class/aml_ddr"
	GPU_PATH = "/sys/class/mpgpu"
	GPU_POWER_PATH = "/sys/class/misc/mali0/device/power/runtime_status"
	POLICIES = ("policy0", "policy2")
	FALLBACK_FREQUENCIES = ("500000", "667000", "1000000", "1200000", "1398000", "1512000", "1608000", "1704000")
	FALLBACK_GOVERNORS = ("interactive", "performance", "schedutil")
	DEFAULT_GOVERNOR = "performance"

	def __init__(self):
		self.governors = {
			"conservative": ("Conservative", _("Raise and lower the CPU frequency gradually depending on the load.")),
			"interactive": ("Interactive", _("Raise the CPU frequency quickly on load and lower it when the CPU is idle.")),
			"ondemand": ("On demand", _("Raise the CPU frequency to the maximum on load and lower it gradually when the CPU is idle.")),
			"performance": ("Performance", _("Always run the CPU at the maximum frequency.")),
			"powersave": ("Power save", _("Always run the CPU at the minimum frequency.")),
			"schedutil": (_("Schedutil (recommended)"), _("Adjust the CPU frequency to the load reported by the kernel scheduler.")),
			"userspace": ("User space", _("Let other programs set the CPU frequency."))
		}
		self.cpus = {}
		self.cpuTimes = {}
		self.frequencies = {}
		self.ramMonitorStarted = False
		self.regulators = {}
		self.thermalZones = {self.readValue(join(x, "type")): x for x in glob("/sys/class/thermal/thermal_zone*")}
		for policy in self.POLICIES:
			cpus = self.readValue(join(self.CPUFREQ_PATH, policy, "affected_cpus")).split() or [policy[-1]]
			self.cpus[policy] = {f"cpu{x}" for x in cpus}
			self.frequencies[policy] = tuple(self.readValue(join(self.CPUFREQ_PATH, policy, "scaling_available_frequencies")).split()) or self.FALLBACK_FREQUENCIES
			self.regulators[policy] = next((x for x in glob("/sys/class/regulator/regulator.*") if exists(join(x, f"cpu{cpus[0]}-cpu"))), None)

	def readValue(self, path):
		try:
			with open(path) as fd:
				value = fd.read().strip()
		except OSError:
			value = ""
		return value

	def writeValue(self, path, value):
		try:
			with open(path, "w") as fd:
				fd.write(value)
		except OSError as err:
			print(f"[AmlFRQ] Error {err.errno}: Unable to write '{value}' to '{path}'!  ({err.strerror})")

	def getFrequencyChoices(self, policy):
		return [(x, f"{int(x) // 1000} MHz") for x in self.frequencies[policy]]

	def getGovernorChoices(self):
		governors = self.readValue(join(self.CPUFREQ_PATH, self.POLICIES[0], "scaling_available_governors")).split() or self.FALLBACK_GOVERNORS
		return [(x, self.governors.get(x, (x,))[0]) for x in governors]

	def getGovernorDescription(self, governor):
		return self.governors.get(governor, ("", ""))[1]

	def applySettings(self, standby=False):
		print(f"[AmlFRQ] Apply {'standby' if standby else 'normal'} settings.")
		for policy, minConfig, maxConfig in (("policy0", config.plugins.aml.minfrq, config.plugins.aml.maxfrq), ("policy2", config.plugins.aml.minfrq2, config.plugins.aml.maxfrq2)):
			path = join(self.CPUFREQ_PATH, policy)
			minimum = min(int(minConfig.value), int(maxConfig.value))
			maximum = minimum if standby else int(maxConfig.value)
			currentMaximum = int(self.readValue(join(path, "scaling_max_freq")) or 0)
			order = ("scaling_max_freq", "scaling_min_freq") if minimum > currentMaximum else ("scaling_min_freq", "scaling_max_freq")  # The kernel rejects a minimum above the maximum.
			for fileName in order:
				self.writeValue(join(path, fileName), str(minimum if fileName == "scaling_min_freq" else maximum))
			self.writeValue(join(path, "scaling_governor"), config.plugins.aml.governor.value)

	def getStatus(self, policy, text):
		frequency = self.readValue(join(self.CPUFREQ_PATH, policy, "scaling_cur_freq"))
		text = text % (str(int(frequency) // 1000) if frequency.isdigit() else _("N/A"))
		voltage = self.readValue(join(self.regulators[policy], "microvolts")) if self.regulators[policy] else ""
		if voltage.isdigit():
			text = f"{text}, {int(voltage) / 1000000:.3f} V"
		return self.addLoad(text, self.getLoad(policy))

	def addLoad(self, text, load):
		return text if load is None else f"{text}, {_('Load: %s %%') % load}"

	def getLoad(self, policy):  # Load since the previous call from the busy and total times in /proc/stat.
		busy = total = 0
		for line in self.readValue("/proc/stat").splitlines():
			fields = line.split()
			if fields and fields[0] in self.cpus[policy]:
				times = [int(x) for x in fields[1:9]]  # user, nice, system, idle, iowait, irq, softirq, steal
				total += sum(times)
				busy += sum(times) - times[3] - times[4]
		lastBusy, lastTotal = self.cpuTimes.get(policy, (0, 0))
		self.cpuTimes[policy] = (busy, total)
		return round((busy - lastBusy) * 100 / (total - lastTotal)) if lastTotal and total > lastTotal else None

	def getGpuStatus(self, text):
		frequency = self.readValue(join(self.GPU_PATH, "cur_freq"))
		load = self.readValue(join(self.GPU_PATH, "utilization"))
		text = self.addLoad(text % (frequency if frequency.isdigit() else _("N/A")), int(load) if load.isdigit() else None)
		state = self.readValue(self.GPU_POWER_PATH)
		if state == "suspended":
			text = f"{text}, {_('suspended (GLES disabled)')}"
		elif state == "active":
			text = f"{text}, {_('active (GLES enabled)')}"
		return text

	def getRamStatus(self, text):
		frequency = self.readValue(join(self.DDR_PATH, "freq")).split()
		usage = search(r"usage:\s*([\d.]+)%", self.readValue(join(self.DDR_PATH, "bandwidth")))
		return self.addLoad(text % (frequency[0] if frequency else _("N/A")), round(float(usage.group(1))) if usage else None)

	def startRamMonitor(self):  # The DDR bandwidth is only measured while the monitor is enabled.
		self.ramMonitorStarted = self.readValue(join(self.DDR_PATH, "mode")).startswith("0")
		if self.ramMonitorStarted:
			self.writeValue(join(self.DDR_PATH, "mode"), "1")

	def stopRamMonitor(self):
		if self.ramMonitorStarted:
			self.writeValue(join(self.DDR_PATH, "mode"), "0")
			self.ramMonitorStarted = False

	def getTemperature(self, zoneType):
		temperature = self.readValue("/proc/stb/fp/temp_sensor_avs") if zoneType == "soc_thermal" else ""
		if not temperature and zoneType in self.thermalZones:
			temperature = self.readValue(join(self.thermalZones[zoneType], "temp"))
			temperature = f"{int(temperature) / 1000:.1f}" if temperature.isdigit() else ""
		return temperature or _("N/A")

	def standbyCounterChanged(self, configElement):
		self.applySettings(standby=True)
		Standby.inStandby.onClose.append(self.applySettings)


cpuControl = CpuControl()

config.plugins.aml = ConfigSubsection()
config.plugins.aml.governor = ConfigSelection(default=CpuControl.DEFAULT_GOVERNOR, choices=cpuControl.getGovernorChoices())
config.plugins.aml.minfrq = ConfigSelection(default=cpuControl.frequencies["policy0"][0], choices=cpuControl.getFrequencyChoices("policy0"))
config.plugins.aml.maxfrq = ConfigSelection(default=cpuControl.frequencies["policy0"][-1], choices=cpuControl.getFrequencyChoices("policy0"))
config.plugins.aml.minfrq2 = ConfigSelection(default=cpuControl.frequencies["policy2"][0], choices=cpuControl.getFrequencyChoices("policy2"))
config.plugins.aml.maxfrq2 = ConfigSelection(default=cpuControl.frequencies["policy2"][-1], choices=cpuControl.getFrequencyChoices("policy2"))


class AmlFRQ(Setup):
	skin = """
	<screen name="AmlFRQ" position="center,center" size="980,570" resolution="1280,720">
		<widget name="config" position="10,10" size="e-20,175" enableWrapAround="1" font="Regular;25" itemHeight="35" scrollbarMode="showOnDemand" />
		<widget name="tempc" position="10,205" size="e-20,25" font="Regular;20" verticalAlignment="center" />
		<widget name="ramtempc" position="10,235" size="e-20,25" font="Regular;20" verticalAlignment="center" />
		<widget name="frqc" position="10,265" size="e-20,25" font="Regular;20" verticalAlignment="center" />
		<widget name="frqc2" position="10,295" size="e-20,25" font="Regular;20" verticalAlignment="center" />
		<widget name="gpuc" position="10,325" size="e-20,25" font="Regular;20" verticalAlignment="center" />
		<widget name="ramc" position="10,355" size="e-20,25" font="Regular;20" verticalAlignment="center" />
		<widget name="footnote" position="10,e-185" size="e-20,25" font="Regular;20" verticalAlignment="center" />
		<widget name="description" position="10,e-160" size="e-20,100" font="Regular;20" verticalAlignment="center" />
		<widget source="key_red" render="Label" position="10,e-50" size="180,40" backgroundColor="key_red" font="Regular;20" foregroundColor="key_text" horizontalAlignment="center" wrap="off" verticalAlignment="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_green" render="Label" position="200,e-50" size="180,40" backgroundColor="key_green" font="Regular;20" foregroundColor="key_text" horizontalAlignment="center" wrap="off" verticalAlignment="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_yellow" render="Label" position="390,e-50" size="180,40" backgroundColor="key_yellow" font="Regular;20" foregroundColor="key_text" horizontalAlignment="center" wrap="off" verticalAlignment="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_menu" render="Label" position="e-200,e-50" size="90,40" backgroundColor="key_back" font="Regular;20" foregroundColor="key_text" horizontalAlignment="center" wrap="off" verticalAlignment="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_help" render="Label" position="e-100,e-50" size="90,40" backgroundColor="key_back" font="Regular;20" foregroundColor="key_text" horizontalAlignment="center" wrap="off" verticalAlignment="center">
			<convert type="ConditionalShowHide" />
		</widget>
	</screen>"""

	def __init__(self, session):
		Setup.__init__(self, session, setup=None)
		self.mandatoryWidgets = ["config", "footnote", "description", "tempc", "ramtempc", "frqc", "frqc2", "gpuc", "ramc"]  # Skip skin screens without the status widgets.
		self["key_yellow"] = StaticText(_("Test"))
		self["tempc"] = Label()
		self["ramtempc"] = Label()
		self["frqc"] = Label()
		self["frqc2"] = Label()
		self["gpuc"] = Label()
		self["ramc"] = Label()
		self["testAction"] = HelpableActionMap(self, ["ColorActions"], {
			"yellow": (self.keyTest, _("Apply the settings without saving them"))
		}, prio=0, description=_("CPU Control Actions"))
		self.statusTimer = eTimer()
		self.statusTimer.callback.append(self.updateStatus)
		self.onLayoutFinish.append(cpuControl.startRamMonitor)
		self.onLayoutFinish.append(self.updateStatus)
		self.onClose.append(self.screenClosed)

	def createSetup(self):
		governor = config.plugins.aml.governor
		items = (
			(_("Set MAX CPU frequency for cores 0 and 1"), config.plugins.aml.maxfrq, _("Select the highest frequency these CPU cores may run at.")),
			(_("Set MIN CPU frequency for cores 0 and 1"), config.plugins.aml.minfrq, _("Select the lowest frequency these CPU cores may run at. This frequency is also used in standby.")),
			(_("Set MAX CPU frequency for cores 2, 3, 4 and 5"), config.plugins.aml.maxfrq2, _("Select the highest frequency these CPU cores may run at.")),
			(_("Set MIN CPU frequency for cores 2, 3, 4 and 5"), config.plugins.aml.minfrq2, _("Select the lowest frequency these CPU cores may run at. This frequency is also used in standby.")),
			(_("Set Scaling governor"), governor, cpuControl.getGovernorDescription(governor.value))
		)
		Setup.createSetup(self, appendItems=[(x[0], x[1], self.formatItemDescription(x[1], x[2])) for x in items])
		self.setTitle(_("CPU Control"))

	def changedEntry(self):
		Setup.changedEntry(self)
		self.selectionChanged()  # Update the governor description.

	def updateStatus(self):
		self["tempc"].setText(_("Current Temperature (SoC): %s °C") % cpuControl.getTemperature("soc_thermal"))
		self["ramtempc"].setText(_("Current Temperature (RAM): %s °C") % cpuControl.getTemperature("ddr_thermal"))
		self["frqc"].setText(cpuControl.getStatus("policy0", _("Current CPU Frequency cores 0 and 1: %s MHz")))
		self["frqc2"].setText(cpuControl.getStatus("policy2", _("Current CPU Frequency other cores: %s MHz")))
		self["gpuc"].setText(cpuControl.getGpuStatus(_("Current GPU Frequency: %s MHz")))
		self["ramc"].setText(cpuControl.getRamStatus(_("Current RAM Frequency: %s MHz")))
		self.statusTimer.start(1000, True)

	def keyTest(self):
		cpuControl.applySettings()

	def screenClosed(self):
		self.statusTimer.stop()
		cpuControl.cpuTimes.clear()
		cpuControl.stopRamMonitor()
		cpuControl.applySettings()  # Apply the saved settings, also after a cancelled test.


def main(menuid, **kwargs):
	return [(_("CPU Control"), startSetup, "CPU Control", None)] if menuid == "system" else []


def startSetup(session, **kwargs):
	session.open(AmlFRQ)


def sessionstart(reason, **kwargs):
	if reason == 0:
		cpuControl.applySettings()
		config.misc.standbyCounter.addNotifier(cpuControl.standbyCounterChanged, initial_call=False)


def Plugins(**kwargs):
	return [
		PluginDescriptor(where=PluginDescriptor.WHERE_SESSIONSTART, fnc=sessionstart),
		PluginDescriptor(name=_("CPU Control"), description=_("Set the CPU frequencies and the governor"), where=PluginDescriptor.WHERE_MENU, fnc=main)
	]
