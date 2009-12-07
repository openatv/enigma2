from Components.ActionMap import ActionMap
from Components.Sensors import sensors
from Components.Sources.Sensor import SensorSource
from Components.ConfigList import ConfigListScreen
from Components.config import getConfigListEntry

from Screens.Screen import Screen

from Plugins.Plugin import PluginDescriptor
from Components.FanControl import fancontrol

class TempFanControl(Screen, ConfigListScreen):
	skin = """
		<screen position="100,100" size="550,400" title="Fan Control" >
			<!--widget name="text" position="0,0" size="550,400" font="Regular;15" /-->
			<widget source="SensorTemp" render="Label" position="380,300" zPosition="1" size="150,20" font="Regular;19" halign="right">
				<convert type="SensorToText"></convert>
			</widget>
			<widget source="SensorFan" render="Label" position="380,325" zPosition="1" size="150,20" font="Regular;19" halign="right">
				<convert type="SensorToText"></convert>
			</widget>
			<widget name="config" position="10,10" size="500,225" scrollbarMode="showOnDemand" />
		</screen>"""
	
	def __init__(self, session, args = None):
		Screen.__init__(self, session)
		
		id = sensors.getSensorsList(sensors.TYPE_TEMPERATURE)[0]		
		self["SensorTemp"] = SensorSource(sensorid = id)
		id = sensors.getSensorsList(sensors.TYPE_FAN_RPM)[0]		
		self["SensorFan"] = SensorSource(sensorid = id, update_interval = 100)
		
		self.list = []
		if fancontrol.getFanCount() > 0:
			self.list.append(getConfigListEntry(_("Fan Voltage"), fancontrol.getConfig(0).vlt))
			self.list.append(getConfigListEntry(_("Fan PWM"), fancontrol.getConfig(0).pwm))
		ConfigListScreen.__init__(self, self.list, session = self.session)
		#self["config"].list = self.list
		#self["config"].setList(self.list)
		
		self["actions"] = ActionMap(["OkCancelActions"], 
		{
			"ok": self.save,
			"cancel": self.revert
		}, -1)
		
	def save(self):
		fancontrol.getConfig(0).vlt.save()
		fancontrol.getConfig(0).pwm.save()
		self.close()
		
	def revert(self):
		fancontrol.getConfig(0).vlt.load()
		fancontrol.getConfig(0).pwm.load()
		self.close()

def main(session, **kwargs):
	session.open(TempFanControl)

def Plugins(**kwargs):
	return PluginDescriptor(name = "Temperature and Fan control", description = _("Temperature and Fan control"), where = PluginDescriptor.WHERE_EXTENSIONSMENU, fnc = main)
	