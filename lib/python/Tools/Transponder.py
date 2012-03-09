from enigma import eDVBFrontendParametersSatellite, eDVBFrontendParametersCable, eDVBFrontendParametersTerrestrial
from Components.NimManager import nimmanager

def ConvertToHumanReadable(tp, type = None):
	ret = { }
	if type is None:
		type = tp.get("tuner_type", "None")
	if type == "DVB-S":
		ret["tuner_type"] = _("Satellite")
		ret["inversion"] = {
			eDVBFrontendParametersSatellite.Inversion_Unknown : _("Auto"),
			eDVBFrontendParametersSatellite.Inversion_On : _("On"),
			eDVBFrontendParametersSatellite.Inversion_Off : _("Off")}[tp["inversion"]]
		ret["fec_inner"] = {
			eDVBFrontendParametersSatellite.FEC_None : _("None"),
			eDVBFrontendParametersSatellite.FEC_Auto : _("Auto"),
			eDVBFrontendParametersSatellite.FEC_1_2 : "1/2",
			eDVBFrontendParametersSatellite.FEC_2_3 : "2/3",
			eDVBFrontendParametersSatellite.FEC_3_4 : "3/4",
			eDVBFrontendParametersSatellite.FEC_5_6 : "5/6",
			eDVBFrontendParametersSatellite.FEC_7_8 : "7/8",
			eDVBFrontendParametersSatellite.FEC_3_5 : "3/5",
			eDVBFrontendParametersSatellite.FEC_4_5 : "4/5",
			eDVBFrontendParametersSatellite.FEC_8_9 : "8/9",
			eDVBFrontendParametersSatellite.FEC_9_10 : "9/10"}[tp["fec_inner"]]
		ret["modulation"] = {
			eDVBFrontendParametersSatellite.Modulation_Auto : _("Auto"),
			eDVBFrontendParametersSatellite.Modulation_QPSK : "QPSK",
			eDVBFrontendParametersSatellite.Modulation_QAM16 : "QAM16",
			eDVBFrontendParametersSatellite.Modulation_8PSK : "8PSK"}[tp["modulation"]]
		ret["orbital_position"] = nimmanager.getSatName(int(tp["orbital_position"]))
		ret["polarization"] = {
			eDVBFrontendParametersSatellite.Polarisation_Horizontal : _("Horizontal"),
			eDVBFrontendParametersSatellite.Polarisation_Vertical : _("Vertical"),
			eDVBFrontendParametersSatellite.Polarisation_CircularLeft : _("Circular left"),
			eDVBFrontendParametersSatellite.Polarisation_CircularRight : _("Circular right")}[tp["polarization"]]
		ret["polarization_abbreviation"] = {
			eDVBFrontendParametersSatellite.Polarisation_Horizontal : "H",
			eDVBFrontendParametersSatellite.Polarisation_Vertical : "V",
			eDVBFrontendParametersSatellite.Polarisation_CircularLeft : "L",
			eDVBFrontendParametersSatellite.Polarisation_CircularRight : "R"}[tp["polarization"]]
		ret["system"] = {
			eDVBFrontendParametersSatellite.System_DVB_S : "DVB-S",
			eDVBFrontendParametersSatellite.System_DVB_S2 : "DVB-S2"}[tp["system"]]
		if ret["system"] == "DVB-S2":
			ret["rolloff"] = {
				eDVBFrontendParametersSatellite.RollOff_alpha_0_35 : "0.35",
				eDVBFrontendParametersSatellite.RollOff_alpha_0_25 : "0.25",
				eDVBFrontendParametersSatellite.RollOff_alpha_0_20 : "0.20",
				eDVBFrontendParametersSatellite.RollOff_auto : _("Auto")}[tp["rolloff"]]
			ret["pilot"] = {
				eDVBFrontendParametersSatellite.Pilot_Unknown : _("Auto"),
				eDVBFrontendParametersSatellite.Pilot_On : _("On"),
				eDVBFrontendParametersSatellite.Pilot_Off : _("Off")}[tp["pilot"]]
	elif type == "DVB-C":
		ret["tuner_type"] = _("Cable")
		ret["modulation"] = {
			eDVBFrontendParametersCable.Modulation_Auto: _("Auto"),
			eDVBFrontendParametersCable.Modulation_QAM16 : "QAM16",
			eDVBFrontendParametersCable.Modulation_QAM32 : "QAM32",
			eDVBFrontendParametersCable.Modulation_QAM64 : "QAM64",
			eDVBFrontendParametersCable.Modulation_QAM128 : "QAM128",
			eDVBFrontendParametersCable.Modulation_QAM256 : "QAM256"}[tp["modulation"]]
		ret["inversion"] = {
			eDVBFrontendParametersCable.Inversion_Unknown : _("Auto"),
			eDVBFrontendParametersCable.Inversion_On : _("On"),
			eDVBFrontendParametersCable.Inversion_Off : _("Off")}[tp["inversion"]]
		ret["fec_inner"] = {
			eDVBFrontendParametersCable.FEC_None : _("None"),
			eDVBFrontendParametersCable.FEC_Auto : _("Auto"),
			eDVBFrontendParametersCable.FEC_1_2 : "1/2",
			eDVBFrontendParametersCable.FEC_2_3 : "2/3",
			eDVBFrontendParametersCable.FEC_3_4 : "3/4",
			eDVBFrontendParametersCable.FEC_5_6 : "5/6",
			eDVBFrontendParametersCable.FEC_7_8 : "7/8",
			eDVBFrontendParametersCable.FEC_8_9 : "8/9"}[tp["fec_inner"]]
		ret["system"] = "DVB-C"
	elif type == "DVB-T":
		ret["tuner_type"] = _("Terrestrial")
		ret["bandwidth"] = {
			eDVBFrontendParametersTerrestrial.Bandwidth_Auto : _("Auto"),
			eDVBFrontendParametersTerrestrial.Bandwidth_8MHz : "8 MHz",
			eDVBFrontendParametersTerrestrial.Bandwidth_7MHz : "7 MHz",
			eDVBFrontendParametersTerrestrial.Bandwidth_6MHz : "6 MHz"}[tp["bandwidth"]]
		ret["code_rate_lp"] = {
			eDVBFrontendParametersTerrestrial.FEC_Auto : _("Auto"),
			eDVBFrontendParametersTerrestrial.FEC_1_2 : "1/2",
			eDVBFrontendParametersTerrestrial.FEC_2_3 : "2/3",
			eDVBFrontendParametersTerrestrial.FEC_3_4 : "3/4",
			eDVBFrontendParametersTerrestrial.FEC_5_6 : "5/6",
			eDVBFrontendParametersTerrestrial.FEC_7_8 : "7/8"}[tp["code_rate_lp"]]
		ret["code_rate_hp"] = {
			eDVBFrontendParametersTerrestrial.FEC_Auto : _("Auto"),
			eDVBFrontendParametersTerrestrial.FEC_1_2 : "1/2",
			eDVBFrontendParametersTerrestrial.FEC_2_3 : "2/3",
			eDVBFrontendParametersTerrestrial.FEC_3_4 : "3/4",
			eDVBFrontendParametersTerrestrial.FEC_5_6 : "5/6",
			eDVBFrontendParametersTerrestrial.FEC_7_8 : "7/8"}[tp["code_rate_hp"]]
		ret["constellation"] = {
			eDVBFrontendParametersTerrestrial.Modulation_Auto : _("Auto"),
			eDVBFrontendParametersTerrestrial.Modulation_QPSK : "QPSK",
			eDVBFrontendParametersTerrestrial.Modulation_QAM16 : "QAM16",
			eDVBFrontendParametersTerrestrial.Modulation_QAM64 : "QAM64"}[tp["constellation"]]
		ret["transmission_mode"] = {
			eDVBFrontendParametersTerrestrial.TransmissionMode_Auto : _("Auto"),
			eDVBFrontendParametersTerrestrial.TransmissionMode_2k : "2k",
			eDVBFrontendParametersTerrestrial.TransmissionMode_8k : "8k"}[tp["transmission_mode"]]
		ret["guard_interval"] = {
			eDVBFrontendParametersTerrestrial.GuardInterval_Auto : _("Auto"),
			eDVBFrontendParametersTerrestrial.GuardInterval_1_32 : "1/32",
			eDVBFrontendParametersTerrestrial.GuardInterval_1_16 : "1/16",
			eDVBFrontendParametersTerrestrial.GuardInterval_1_8 : "1/8",
			eDVBFrontendParametersTerrestrial.GuardInterval_1_4 : "1/4"}[tp["guard_interval"]]
		ret["hierarchy_information"] = {
			eDVBFrontendParametersTerrestrial.Hierarchy_Auto : _("Auto"),
			eDVBFrontendParametersTerrestrial.Hierarchy_None : _("None"),
			eDVBFrontendParametersTerrestrial.Hierarchy_1 : "1",
			eDVBFrontendParametersTerrestrial.Hierarchy_2 : "2",
			eDVBFrontendParametersTerrestrial.Hierarchy_4 : "4"}[tp["hierarchy_information"]]
		ret["inversion"] = {
			eDVBFrontendParametersTerrestrial.Inversion_Unknown : _("Auto"),
			eDVBFrontendParametersTerrestrial.Inversion_On : _("On"),
			eDVBFrontendParametersTerrestrial.Inversion_Off : _("Off")}[tp["inversion"]]
		ret["system"] = "DVB-T"		
	elif type != "None":
		print "ConvertToHumanReadable: no or unknown type in tpdata dict for type:", type
	for k,v in tp.items():
		if k not in ret:
			ret[k] = v
	return ret
