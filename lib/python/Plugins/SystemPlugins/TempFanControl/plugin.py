from Components.ActionMap import ActionMap
from Components.Sensors import sensors
from Components.Sources.Sensor import SensorSource
from Components.Sources.StaticText import StaticText
from Components.ConfigList import ConfigListScreen
from Components.config import getConfigListEntry

from Screens.Screen import Screen

from Plugins.Plugin import PluginDescriptor
from Components.FanControl import fancontrol

class TempFanControl(Screen, ConfigListScreen):
	skin = """
		<screen position="100,100" size="550,400" title="Fan Control" >
			<!--widget name="text" position="0,0" size="550,400" font="Regular;15" /-->
			
			<widget source="SensorTempText0" render="Label" position="10,150" zPosition="1" size="90,40" font="Regular;20" halign="left" valign="top" backgroundColor="#9f1313" transparent="1" />
			<widget source="SensorTemp0" render="Label" position="100,150" zPosition="1" size="100,20" font="Regular;19" halign="right">
				<convert type="SensorToText"></convert>
			</widget>
			<widget source="SensorTempText1" render="Label" position="10,170" zPosition="1" size="90,40" font="Regular;20" halign="left" valign="top" backgroundColor="#9f1313" transparent="1" />
			<widget source="SensorTemp1" render="Label" position="100,170" zPosition="1" size="100,20" font="Regular;19" halign="right">
				<convert type="SensorToText"></convert>
			</widget>
			<widget source="SensorTempText2" render="Label" position="10,190" zPosition="1" size="90,40" font="Regular;20" halign="left" valign="top" backgroundColor="#9f1313" transparent="1" />
			<widget source="SensorTemp2" render="Label" position="100,190" zPosition="1" size="100,20" font="Regular;19" halign="right">
				<convert type="SensorToText"></convert>
			</widget>
			<widget source="SensorTempText3" render="Label" position="10,210" zPosition="1" size="90,40" font="Regular;20" halign="left" valign="top" backgroundColor="#9f1313" transparent="1" />
			<widget source="SensorTemp3" render="Label" position="100,210" zPosition="1" size="100,20" font="Regular;19" halign="right">
				<convert type="SensorToText"></convert>
			</widget>
			<widget source="SensorTempText4" render="Label" position="10,230" zPosition="1" size="90,40" font="Regular;20" halign="left" valign="top" backgroundColor="#9f1313" transparent="1" />
			<widget source="SensorTemp4" render="Label" position="100,230" zPosition="1" size="100,20" font="Regular;19" halign="right">
				<convert type="SensorToText"></convert>
			</widget>
			<widget source="SensorTempText5" render="Label" position="10,250" zPosition="1" size="90,40" font="Regular;20" halign="left" valign="top" backgroundColor="#9f1313" transparent="1" />
			<widget source="SensorTemp5" render="Label" position="100,250" zPosition="1" size="100,20" font="Regular;19" halign="right">
				<convert type="SensorToText"></convert>
			</widget>
			<widget source="SensorTempText6" render="Label" position="10,270" zPosition="1" size="90,40" font="Regular;20" halign="left" valign="top" backgroundColor="#9f1313" transparent="1" />
			<widget source="SensorTemp6" render="Label" position="100,270" zPosition="1" size="100,20" font="Regular;19" halign="right">
				<convert type="SensorToText"></convert>
			</widget>
			<widget source="SensorTempText7" render="Label" position="10,290" zPosition="1" size="90,40" font="Regular;20" halign="left" valign="top" backgroundColor="#9f1313" transparent="1" />
			<widget source="SensorTemp7" render="Label" position="100,290" zPosition="1" size="100,20" font="Regular;19" halign="right">
				<convert type="SensorToText"></convert>
			</widget>
			
			<widget source="SensorFanText0" render="Label" position="290,150" zPosition="1" size="90,40" font="Regular;20" halign="left" valign="top" backgroundColor="#9f1313" transparent="1" />
			<widget source="SensorFan0" render="Label" position="380,150" zPosition="1" size="150,20" font="Regular;19" halign="right">
				<convert type="SensorToText"></convert>
			</widget>
			<widget source="SensorFanText1" render="Label" position="290,170" zPosition="1" size="90,40" font="Regular;20" halign="left" valign="top" backgroundColor="#9f1313" transparent="1" />
			<widget source="SensorFan1" render="Label" position="380,170" zPosition="1" size="150,20" font="Regular;19" halign="right">
				<convert type="SensorToText"></convert>
			</widget>
			<widget source="SensorFanText2" render="Label" position="290,190" zPosition="1" size="90,40" font="Regular;20" halign="left" valign="top" backgroundColor="#9f1313" transparent="1" />
			<widget source="SensorFan2" render="Label" position="380,190" zPosition="1" size="150,20" font="Regular;19" halign="right">
				<convert type="SensorToText"></convert>
			</widget>
			<widget source="SensorFanText3" render="Label" position="290,210" zPosition="1" size="90,40" font="Regular;20" halign="left" valign="top" backgroundColor="#9f1313" transparent="1" />
			<widget source="SensorFan3" render="Label" position="380,210" zPosition="1" size="150,20" font="Regular;19" halign="right">
				<convert type="SensorToText"></convert>
			</widget>
			<widget source="SensorFanText4" render="Label" position="290,230" zPosition="1" size="90,40" font="Regular;20" halign="left" valign="top" backgroundColor="#9f1313" transparent="1" />
			<widget source="SensorFan4" render="Label" position="380,230" zPosition="1" size="150,20" font="Regular;19" halign="right">
				<convert type="SensorToText"></convert>
			</widget>
			<widget source="SensorFanText5" render="Label" position="290,250" zPosition="1" size="90,40" font="Regular;20" halign="left" valign="top" backgroundColor="#9f1313" transparent="1" />
			<widget source="SensorFan5" render="Label" position="380,250" zPosition="1" size="150,20" font="Regular;19" halign="right">
				<convert type="SensorToText"></convert>
			</widget>
			<widget source="SensorFanText6" render="Label" position="290,270" zPosition="1" size="90,40" font="Regular;20" halign="left" valign="top" backgroundColor="#9f1313" transparent="1" />
			<widget source="SensorFan6" render="Label" position="380,270" zPosition="1" size="150,20" font="Regular;19" halign="right">
				<convert type="SensorToText"></convert>
			</widget>
			<widget source="SensorFanText7" render="Label" position="290,290" zPosition="1" size="90,40" font="Regular;20" halign="left" valign="top" backgroundColor="#9f1313" transparent="1" />
			<widget source="SensorFan7" render="Label" position="380,290" zPosition="1" size="150,20" font="Regular;19" halign="right">
				<convert type="SensorToText"></convert>
			</widget>
			<widget name="config" position="10,10" size="500,225" scrollbarMode="showOnDemand" />
		</screen>"""
	
	def __init__(self, session, args = None):
		Screen.__init__(self, session)
		
		templist = sensors.getSensorsList(sensors.TYPE_TEMPERATURE)
		tempcount = len(templist)
		fanlist = sensors.getSensorsList(sensors.TYPE_FAN_RPM)
		fancount = len(fanlist)
		
		for count in range(8):
			if count < tempcount:
				id = templist[count]
				self["SensorTempText%d" % count] = StaticText(sensors.getSensorName(id))		
				self["SensorTemp%d" % count] = SensorSource(sensorid = id)
			else:
				self["SensorTempText%d" % count] = StaticText("")
				self["SensorTemp%d" % count] = SensorSource()
				
			if count < fancount:
				id = fanlist[count]
				self["SensorFanText%d" % count] = StaticText(sensors.getSensorName(id))		
				self["SensorFan%d" % count] = SensorSource(sensorid = id)
			else:
				self["SensorFanText%d" % count] = StaticText("")
				self["SensorFan%d" % count] = SensorSource()
		
		self.list = []
		for count in range(fancontrol.getFanCount()):
			self.list.append(getConfigListEntry(_("Fan %d Voltage") % (count + 1), fancontrol.getConfig(count).vlt))
			self.list.append(getConfigListEntry(_("Fan %d PWM") % (count + 1), fancontrol.getConfig(count).pwm))
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
	