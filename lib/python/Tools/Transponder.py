from enigma import eDVBFrontendParametersSatellite, eDVBFrontendParametersCable, eDVBFrontendParametersTerrestrial
from Components.NimManager import nimmanager

def orbpos(pos):
	return pos > 3600 and "N/A" or "%d.%d\xc2\xb0%s" % (pos > 1800 and ((3600 - pos) / 10, (3600 - pos) % 10, "W") or (pos / 10, pos % 10, "E"))

def getTunerDescription(nim):
	try:
		return nimmanager.getTerrestrialDescription(nim)
	except:
		print "[ChannelNumber] nimmanager.getTerrestrialDescription(nim) failed, nim:", nim
	return ""

def getMHz(frequency):
	if str(frequency).endswith('MHz'):
		return frequency.split()[0]
	return (frequency+50000)/100000/10.

def getChannelNumber(frequency, nim):
	if nim == "DVB-T":
		for n in nimmanager.nim_slots:
			if n.isCompatible("DVB-T"):
				nim = n.slot
				break
	f = int(getMHz(frequency))
	descr = getTunerDescription(nim)
	if "DVB-T" in descr:
		if "Europe" in descr:
			if 174 < f < 230: 	# III
				d = (f + 1) % 7
				return str(int(f - 174)/7 + 5) + (d < 3 and "-" or d > 4 and "+" or "")
			elif 470 <= f < 863: 	# IV,V
				d = (f + 2) % 8
				return str(int(f - 470) / 8 + 21) + (d < 3.5 and "-" or d > 4.5 and "+" or "")
		elif "Australia" in descr:
			d = (f + 1) % 7
			ds = (d < 3 and "-" or d > 4 and "+" or "")
			if 174 < f < 202: 	# CH6-CH9
				return str(int(f - 174)/7 + 6) + ds
			elif 202 <= f < 209: 	# CH9A
				return "9A" + ds
			elif 209 <= f < 230: 	# CH10-CH12
				return str(int(f - 209)/7 + 10) + ds
			elif 526 < f < 820: 	# CH28-CH69
				d = (f - 1) % 7
				return str(int(f - 526)/7 + 28) + (d < 3 and "-" or d > 4 and "+" or "")
	return ""

def supportedChannels(nim):
	descr = getTunerDescription(nim)
	return "Europe" in descr and "DVB-T" in descr

def channel2frequency(channel, nim):
	descr = getTunerDescription(nim)
	if "Europe" in descr and "DVB-T" in descr:
		if 5 <= channel <= 12:
			return (177500 + 7000*(channel- 5))*1000
		elif 21 <= channel <= 69:
			return (474000 + 8000*(channel-21))*1000
	return 474000000

def ConvertToHumanReadable(tp, tunertype = None):
	ret = { }
	if tunertype is None:
		tunertype = tp.get("tuner_type", "None")
	if tunertype == "DVB-S":
		ret["tuner_type"] = _("Satellite")
		ret["inversion"] = {
			eDVBFrontendParametersSatellite.Inversion_Unknown : _("Auto"),
			eDVBFrontendParametersSatellite.Inversion_On : _("On"),
			eDVBFrontendParametersSatellite.Inversion_Off : _("Off")}.get(tp.get("inversion"))
		ret["fec_inner"] = {
			eDVBFrontendParametersSatellite.FEC_None : _("None"),
			eDVBFrontendParametersSatellite.FEC_Auto : _("Auto"),
			eDVBFrontendParametersSatellite.FEC_1_2 : "1/2",
			eDVBFrontendParametersSatellite.FEC_2_3 : "2/3",
			eDVBFrontendParametersSatellite.FEC_3_4 : "3/4",
			eDVBFrontendParametersSatellite.FEC_5_6 : "5/6",
			eDVBFrontendParametersSatellite.FEC_6_7 : "6/7",
			eDVBFrontendParametersSatellite.FEC_7_8 : "7/8",
			eDVBFrontendParametersSatellite.FEC_3_5 : "3/5",
			eDVBFrontendParametersSatellite.FEC_4_5 : "4/5",
			eDVBFrontendParametersSatellite.FEC_8_9 : "8/9",
			eDVBFrontendParametersSatellite.FEC_9_10 : "9/10"}.get(tp.get("fec_inner"))
		ret["modulation"] = {
			eDVBFrontendParametersSatellite.Modulation_Auto : _("Auto"),
			eDVBFrontendParametersSatellite.Modulation_QPSK : "QPSK",
			eDVBFrontendParametersSatellite.Modulation_QAM16 : "QAM16",
			eDVBFrontendParametersSatellite.Modulation_8PSK : "8PSK"}.get(tp.get("modulation"))
		ret["orbital_position"] = nimmanager.getSatName(int(tp.get("orbital_position")))
		ret["orb_pos"] = orbpos(int(tp.get("orbital_position")))
		ret["polarization"] = {
			eDVBFrontendParametersSatellite.Polarisation_Horizontal : _("Horizontal"),
			eDVBFrontendParametersSatellite.Polarisation_Vertical : _("Vertical"),
			eDVBFrontendParametersSatellite.Polarisation_CircularLeft : _("Circular left"),
			eDVBFrontendParametersSatellite.Polarisation_CircularRight : _("Circular right")}.get(tp.get("polarization"))
		ret["polarization_abbreviation"] = {
			eDVBFrontendParametersSatellite.Polarisation_Horizontal : "H",
			eDVBFrontendParametersSatellite.Polarisation_Vertical : "V",
			eDVBFrontendParametersSatellite.Polarisation_CircularLeft : "L",
			eDVBFrontendParametersSatellite.Polarisation_CircularRight : "R"}.get(tp.get("polarization"))
		ret["system"] = {
			eDVBFrontendParametersSatellite.System_DVB_S : "DVB-S",
			eDVBFrontendParametersSatellite.System_DVB_S2 : "DVB-S2"}.get(tp.get("system"))
		if ret["system"] == "DVB-S2":
			ret["rolloff"] = {
				eDVBFrontendParametersSatellite.RollOff_alpha_0_35 : "0.35",
				eDVBFrontendParametersSatellite.RollOff_alpha_0_25 : "0.25",
				eDVBFrontendParametersSatellite.RollOff_alpha_0_20 : "0.20",
				eDVBFrontendParametersSatellite.RollOff_auto : _("Auto")}.get(tp.get("rolloff"))
			ret["pilot"] = {
				eDVBFrontendParametersSatellite.Pilot_Unknown : _("Auto"),
				eDVBFrontendParametersSatellite.Pilot_On : _("On"),
				eDVBFrontendParametersSatellite.Pilot_Off : _("Off")}.get(tp.get("pilot"))
		ret["frequency"] = (tp.get("frequency") and str(tp.get("frequency")/1000) + ' MHz') or '0 MHz'
		ret["symbol_rate"] = (tp.get("symbol_rate") and tp.get("symbol_rate")/1000) or 0
	elif tunertype == "DVB-C":
		ret["tuner_type"] = _("Cable")
		ret["modulation"] = {
			eDVBFrontendParametersCable.Modulation_Auto: _("Auto"),
			eDVBFrontendParametersCable.Modulation_QAM16 : "QAM16",
			eDVBFrontendParametersCable.Modulation_QAM32 : "QAM32",
			eDVBFrontendParametersCable.Modulation_QAM64 : "QAM64",
			eDVBFrontendParametersCable.Modulation_QAM128 : "QAM128",
			eDVBFrontendParametersCable.Modulation_QAM256 : "QAM256"}.get(tp.get("modulation"))
		ret["inversion"] = {
			eDVBFrontendParametersCable.Inversion_Unknown : _("Auto"),
			eDVBFrontendParametersCable.Inversion_On : _("On"),
			eDVBFrontendParametersCable.Inversion_Off : _("Off")}.get(tp.get("inversion"))
		ret["fec_inner"] = {
			eDVBFrontendParametersCable.FEC_None : _("None"),
			eDVBFrontendParametersCable.FEC_Auto : _("Auto"),
			eDVBFrontendParametersCable.FEC_1_2 : "1/2",
			eDVBFrontendParametersCable.FEC_2_3 : "2/3",
			eDVBFrontendParametersCable.FEC_3_4 : "3/4",
			eDVBFrontendParametersCable.FEC_5_6 : "5/6",
			eDVBFrontendParametersCable.FEC_7_8 : "7/8",
			eDVBFrontendParametersCable.FEC_8_9 : "8/9",
			eDVBFrontendParametersCable.FEC_3_5 : "3/5",
			eDVBFrontendParametersCable.FEC_4_5 : "4/5",
			eDVBFrontendParametersCable.FEC_9_10 : "9/10"}.get(tp.get("fec_inner"))
		ret["system"] = {
			eDVBFrontendParametersCable.System_DVB_C_ANNEX_A : "DVB-C",
			eDVBFrontendParametersCable.System_DVB_C_ANNEX_C : "DVB-C ANNEX C"}.get(tp.get("system"))
		ret["frequency"] = (tp.get("frequency") and str(tp.get("frequency")/1000) + ' MHz') or '0 MHz'
	elif tunertype == "DVB-T":
		ret["tuner_type"] = _("Terrestrial")
		ret["bandwidth"] = {
			0 : _("Auto"),
			10000000 : "10 MHz",
			8000000 : "8 MHz",
			7000000 : "7 MHz",
			6000000 : "6 MHz",
			5000000 : "5 MHz",
			1712000 : "1.712 MHz"}.get(tp.get("bandwidth"))
		#print 'bandwidth:',tp.get("bandwidth")
		ret["code_rate_lp"] = {
			eDVBFrontendParametersTerrestrial.FEC_Auto : _("Auto"),
			eDVBFrontendParametersTerrestrial.FEC_1_2 : "1/2",
			eDVBFrontendParametersTerrestrial.FEC_2_3 : "2/3",
			eDVBFrontendParametersTerrestrial.FEC_3_4 : "3/4",
			eDVBFrontendParametersTerrestrial.FEC_5_6 : "5/6",
			eDVBFrontendParametersTerrestrial.FEC_6_7 : "6/7",
			eDVBFrontendParametersTerrestrial.FEC_7_8 : "7/8",
			eDVBFrontendParametersTerrestrial.FEC_8_9 : "8/9"}.get(tp.get("code_rate_lp"))
		#print 'code_rate_lp:',tp.get("code_rate_lp")
		ret["code_rate_hp"] = {
			eDVBFrontendParametersTerrestrial.FEC_Auto : _("Auto"),
			eDVBFrontendParametersTerrestrial.FEC_1_2 : "1/2",
			eDVBFrontendParametersTerrestrial.FEC_2_3 : "2/3",
			eDVBFrontendParametersTerrestrial.FEC_3_4 : "3/4",
			eDVBFrontendParametersTerrestrial.FEC_5_6 : "5/6",
			eDVBFrontendParametersTerrestrial.FEC_6_7 : "6/7",
			eDVBFrontendParametersTerrestrial.FEC_7_8 : "7/8",
			eDVBFrontendParametersTerrestrial.FEC_8_9 : "8/9"}.get(tp.get("code_rate_hp"))
		#print 'code_rate_hp:',tp.get("code_rate_hp")
		ret["constellation"] = {
			eDVBFrontendParametersTerrestrial.Modulation_Auto : _("Auto"),
			eDVBFrontendParametersTerrestrial.Modulation_QPSK : "QPSK",
			eDVBFrontendParametersTerrestrial.Modulation_QAM16 : "QAM16",
			eDVBFrontendParametersTerrestrial.Modulation_QAM64 : "QAM64",
			eDVBFrontendParametersTerrestrial.Modulation_QAM256 : "QAM256"}.get(tp.get("constellation"))
		#print 'constellation:',tp.get("constellation")
		ret["transmission_mode"] = {
			eDVBFrontendParametersTerrestrial.TransmissionMode_Auto : _("Auto"),
			eDVBFrontendParametersTerrestrial.TransmissionMode_1k : "1k",
			eDVBFrontendParametersTerrestrial.TransmissionMode_2k : "2k",
			eDVBFrontendParametersTerrestrial.TransmissionMode_4k : "4k",
			eDVBFrontendParametersTerrestrial.TransmissionMode_8k : "8k",
			eDVBFrontendParametersTerrestrial.TransmissionMode_16k : "16k",
			eDVBFrontendParametersTerrestrial.TransmissionMode_32k : "32k"}.get(tp.get("transmission_mode"))
		#print 'transmission_mode:',tp.get("transmission_mode")
		ret["guard_interval"] = {
			eDVBFrontendParametersTerrestrial.GuardInterval_Auto : _("Auto"),
			eDVBFrontendParametersTerrestrial.GuardInterval_19_256 : "19/256",
			eDVBFrontendParametersTerrestrial.GuardInterval_19_128 : "19/128",
			eDVBFrontendParametersTerrestrial.GuardInterval_1_128 : "1/128",
			eDVBFrontendParametersTerrestrial.GuardInterval_1_32 : "1/32",
			eDVBFrontendParametersTerrestrial.GuardInterval_1_16 : "1/16",
			eDVBFrontendParametersTerrestrial.GuardInterval_1_8 : "1/8",
			eDVBFrontendParametersTerrestrial.GuardInterval_1_4 : "1/4"}.get(tp.get("guard_interval"))
		#print 'guard_interval:',tp.get("guard_interval")
		ret["hierarchy_information"] = {
			eDVBFrontendParametersTerrestrial.Hierarchy_Auto : _("Auto"),
			eDVBFrontendParametersTerrestrial.Hierarchy_None : _("None"),
			eDVBFrontendParametersTerrestrial.Hierarchy_1 : "1",
			eDVBFrontendParametersTerrestrial.Hierarchy_2 : "2",
			eDVBFrontendParametersTerrestrial.Hierarchy_4 : "4"}.get(tp.get("hierarchy_information"))
		#print 'hierarchy_information:',tp.get("hierarchy_information")
		ret["inversion"] = {
			eDVBFrontendParametersTerrestrial.Inversion_Unknown : _("Auto"),
			eDVBFrontendParametersTerrestrial.Inversion_On : _("On"),
			eDVBFrontendParametersTerrestrial.Inversion_Off : _("Off")}.get(tp.get("inversion"))
		#print 'inversion:',tp.get("inversion")
		ret["system"] = {
			eDVBFrontendParametersTerrestrial.System_DVB_T_T2 : "DVB-T/T2",
			eDVBFrontendParametersTerrestrial.System_DVB_T : "DVB-T",
			eDVBFrontendParametersTerrestrial.System_DVB_T2 : "DVB-T2"}.get(tp.get("system"))
#		print 'system:',tp.get("system")
		ret["frequency"] = (tp.get("frequency") and ('%i MHz' % int(round(tp.get("frequency"), -6)/1000000))) or '0 MHz'
#		print 'frequency:',tp.get("frequency")
		ret["channel"] = _("CH%s") % getChannelNumber(tp.get("frequency"), "DVB-T")
	elif tunertype == "ATSC":
		ret["tuner_type"] = "ATSC"
		ret["modulation"] = {
			eDVBFrontendParametersATSC.Modulation_Auto: _("Auto"),
			eDVBFrontendParametersATSC.Modulation_QAM16 : "QAM16",
			eDVBFrontendParametersATSC.Modulation_QAM32 : "QAM32",
			eDVBFrontendParametersATSC.Modulation_QAM64 : "QAM64",
			eDVBFrontendParametersATSC.Modulation_QAM128 : "QAM128",
			eDVBFrontendParametersATSC.Modulation_QAM256 : "QAM256",
			eDVBFrontendParametersATSC.Modulation_VSB_8 : "VSB_8",
			eDVBFrontendParametersATSC.Modulation_VSB_16 : "VSB_16"}.get(tp.get("modulation"))
		ret["inversion"] = {
			eDVBFrontendParametersATSC.Inversion_Unknown : _("Auto"),
			eDVBFrontendParametersATSC.Inversion_On : _("On"),
			eDVBFrontendParametersATSC.Inversion_Off : _("Off")}.get(tp.get("inversion"))
		ret["system"] = {
			eDVBFrontendParametersATSC.System_ATSC : "ATSC",
			eDVBFrontendParametersATSC.System_DVB_C_ANNEX_B : "DVB-C ANNEX B"}.get(tp.get("system"))
	elif tunertype != "None":
		print "ConvertToHumanReadable: no or unknown tunertype in tpdata dict for tunertype:", tunertype
	for k,v in tp.items():
		if k not in ret:
			ret[k] = v
	return ret
