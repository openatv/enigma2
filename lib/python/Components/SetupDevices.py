from config import config				#global config instance

from config import configElement
from config import ConfigSubsection
from config import ConfigSlider
from config import configBoolean

def InitSetupDevices():
	config.timezone = ConfigSubsection();
	config.timezone.val = configElement("", configBoolean, 1, ("GMT", "GMT+1", "GMT+2", "GMT+3", "GMT+4", "GMT+5", "GMT+6", "GMT+7", "GMT+8", "GMT+9") );

	config.rc = ConfigSubsection();
	config.rc.map = configElement("", configBoolean, 0, ("Default", "Classic") );

#	config.av = ConfigSubsection();
#	config.av.colorformat = configElement("", configBoolean, 1, ("CVBS", "RGB", "S-Video") );
#	config.av.aspectratio = configElement("", configBoolean, 0, ("4:3 Letterbox", "4:3 PanScan", "16:9", "16:9 always") );
#	config.av.tvsystem = configElement("", configBoolean, 0, ("PAL", "PAL + PAL60", "Multi", "NTSC") );
#	config.av.wss = configElement("", configBoolean, 0, ("Enable", "Disable") );
#	config.av.defaultac3 = configElement("", configBoolean, 1, ("Enable", "Disable") );
#	config.av.vcrswitch = configElement("", configBoolean, 0, ("Enable", "Disable") );

	config.rfmod = ConfigSubsection();
	config.rfmod.enable = configElement("", configBoolean, 1, ("Enable", "Disable") );
	config.rfmod.test = configElement("", configBoolean, 1, ("Enable", "Disable") );
	config.rfmod.sound = configElement("", configBoolean, 0, ("Enable", "Disable") );
	config.rfmod.soundcarrier = configElement("", configBoolean, 1, ("4.5 MHz", "5.5 MHz", "6.0 MHz", "6.5 MHz") );
	config.rfmod.channel = configElement("", configBoolean, 6, ("30", "31", "32", "33", "34", "35", "36", "37", "38", "39") );
	config.rfmod.finetune = configElement("", ConfigSlider, 5, "");

	config.keyboard = ConfigSubsection();
	config.keyboard.keymap = configElement("", configBoolean, 1, ("English", "German") );

	config.osd = ConfigSubsection();
	config.osd.alpha = configElement("", ConfigSlider, 0, "");
	config.osd.bright = configElement("", ConfigSlider, 5, "");
	config.osd.contrast = configElement("", ConfigSlider, 5, "");
	config.osd.language = configElement("", configBoolean, 0, ("English", "English US") );

	config.lcd = ConfigSubsection();
	config.lcd.bright = configElement("", ConfigSlider, 7, "");
	config.lcd.standby = configElement("", ConfigSlider, 1, "");
	config.lcd.invert = configElement("", configBoolean, 1, ("Enable", "Disable") );

	config.parental = ConfigSubsection();
	config.parental.lock = configElement("", configBoolean, 1, ("Enable", "Disable") );
	config.parental.setuplock = configElement("", configBoolean, 1, ("Enable", "Disable") );

	config.expert = ConfigSubsection();
	config.expert.splitsize = configElement("", configBoolean, 1, ("0.5Gbyte", "1.0 GByte", "1.5 GByte", "2.0 GByte") );
	config.expert.satpos = configElement("", configBoolean, 1, ("Enable", "Disable") );
	config.expert.fastzap = configElement("", configBoolean, 0, ("Enable", "Disable") );
	config.expert.skipconfirm = configElement("", configBoolean, 1, ("Enable", "Disable") );
	config.expert.hideerrors = configElement("", configBoolean, 1, ("Enable", "Disable") );
	config.expert.autoinfo = configElement("", configBoolean, 1, ("Enable", "Disable") );

	config.sat = ConfigSubsection();
	config.sat.satA = configElement("", configBoolean, 1, ("Disabled" ,"Astra 19.2", "Hotbird 13.0") );
	config.sat.satB = configElement("", configBoolean, 0, ("Disabled" ,"Astra 19.2", "Hotbird 13.0") );
	config.sat.diseqcA = configElement("", configBoolean, 3, ("no DiSEqC", "DiSEqC 1.0", "DiSEqC 1.1", "DiSEqC 1.2") );
	config.sat.diseqcB = configElement("", configBoolean, 0, ("no DiSEqC", "DiSEqC 1.0", "DiSEqC 1.1", "DiSEqC 1.2") );
	config.sat.posA = configElement("", configBoolean, 0, ("DiSEqC A", "DiSEqC B", "DiSEqC C", "DiSEqC D") );
	config.sat.posB = configElement("", configBoolean, 1, ("DiSEqC A", "DiSEqC B", "DiSEqC C", "DiSEqC D") );

	#config.blasel = ConfigSubsection();
	#config.blasel.val = configElement("", configBoolean, 0, ("bunt", "s/w", "gruen") );
	#config.inputDevices.delay = configElement("config.inputDevices.delay", ConfigSlider, 3);

	#this instance anywhere else needed?	
	#iDevices = inputDevices();	
	
	#def inputDevicesRepeatChanged(configElement):
	#	iDevices.setRepeat(configElement.value);

	#def inputDevicesDelayChanged(configElement):
	#	iDevices.setDelay(configElement.value);

	# this will call the "setup-val" initial
	#config.inputDevices.repeat.addNotifier(inputDevicesRepeatChanged);
	#config.inputDevices.delay.addNotifier(inputDevicesDelayChanged);
