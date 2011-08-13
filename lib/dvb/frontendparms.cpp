#include <lib/dvb/dvb.h>
#include <lib/dvb/frontendparms.h>
#include <lib/base/eerror.h>
#include <lib/base/nconfig.h> // access to python config
#include <errno.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/ioctl.h>


DEFINE_REF(eDVBFrontendStatus);

eDVBFrontendStatus::eDVBFrontendStatus(ePtr<eDVBFrontend> &fe)
: frontend(fe)
{
}

int eDVBFrontendStatus::getState() const
{
	int result;
	if (!frontend) return -1;
	if (frontend->getState(result) < 0) return -1;
	return result;
};

std::string eDVBFrontendStatus::getStateDescription() const
{
	switch (getState())
	{
	case iDVBFrontend_ENUMS::stateIdle:
		return "IDLE";
	case iDVBFrontend_ENUMS::stateTuning:
		return "TUNING";
	case iDVBFrontend_ENUMS::stateFailed:
		return "FAILED";
	case iDVBFrontend_ENUMS::stateLock:
		return "LOCKED";
	case iDVBFrontend_ENUMS::stateLostLock:
		return "LOSTLOCK";
	default:
		break;
	}
	return "UNKNOWN";
}

int eDVBFrontendStatus::getLocked() const
{
	if (!frontend) return 0;
	return frontend->readFrontendData(iFrontendInformation_ENUMS::lockState);
}

int eDVBFrontendStatus::getSynced() const
{
	if (!frontend) return 0;
	return frontend->readFrontendData(iFrontendInformation_ENUMS::syncState);
}

int eDVBFrontendStatus::getBER() const
{
	if (!frontend || getState() == iDVBFrontend_ENUMS::stateTuning) return 0;
	return frontend->readFrontendData(iFrontendInformation_ENUMS::bitErrorRate);
}

int eDVBFrontendStatus::getSNR() const
{
	if (!frontend || getState() == iDVBFrontend_ENUMS::stateTuning) return 0;
	return frontend->readFrontendData(iFrontendInformation_ENUMS::signalQuality);
}

int eDVBFrontendStatus::getSNRdB() const
{
	int value;
	if (!frontend || getState() == iDVBFrontend_ENUMS::stateTuning) return 0;
	value = frontend->readFrontendData(iFrontendInformation_ENUMS::signalQualitydB);
	if (value == 0x12345678)
	{
		return -1; /* not supported */
	}
	return value;
}

int eDVBFrontendStatus::getSignalPower() const
{
	if (!frontend || getState() == iDVBFrontend_ENUMS::stateTuning) return 0;
	return frontend->readFrontendData(iFrontendInformation_ENUMS::signalPower);
}

eDVBTransponderData::eDVBTransponderData(struct dtv_property *dtvproperties, unsigned int propertycount, bool original)
: originalValues(original)
{
	for (unsigned int i = 0; i < propertycount; i++)
	{
		dtvProperties.push_back(dtvproperties[i]);
	}
}

int eDVBTransponderData::getProperty(unsigned int cmd) const
{
	for (unsigned int i = 0; i < dtvProperties.size(); i++)
	{
		if (dtvProperties[i].cmd == cmd)
		{
			return dtvProperties[i].u.data;
		}
	}
	return -1;
}

int eDVBTransponderData::getInversion() const
{
	return getProperty(DTV_INVERSION);
}

unsigned int eDVBTransponderData::getFrequency() const
{
	return getProperty(DTV_FREQUENCY);
}

unsigned int eDVBTransponderData::getSymbolRate() const
{
	return getProperty(DTV_SYMBOL_RATE);
}

int eDVBTransponderData::getOrbitalPosition() const
{
	return -1;
}

int eDVBTransponderData::getFecInner() const
{
	return getProperty(DTV_INNER_FEC);
}

int eDVBTransponderData::getModulation() const
{
	return getProperty(DTV_MODULATION);
}

int eDVBTransponderData::getPolarization() const
{
	return -1;
}

int eDVBTransponderData::getRolloff() const
{
	return getProperty(DTV_ROLLOFF);
}

int eDVBTransponderData::getPilot() const
{
	return getProperty(DTV_PILOT);
}

int eDVBTransponderData::getSystem() const
{
	return getProperty(DTV_DELIVERY_SYSTEM);
}

int eDVBTransponderData::getBandwidth() const
{
	return getProperty(DTV_BANDWIDTH_HZ);
}

int eDVBTransponderData::getCodeRateLp() const
{
	return getProperty(DTV_CODE_RATE_LP);
}

int eDVBTransponderData::getCodeRateHp() const
{
	return getProperty(DTV_CODE_RATE_HP);
}

int eDVBTransponderData::getConstellation() const
{
	return getProperty(DTV_MODULATION);
}

int eDVBTransponderData::getTransmissionMode() const
{
	return getProperty(DTV_TRANSMISSION_MODE);
}

int eDVBTransponderData::getGuardInterval() const
{
	return getProperty(DTV_GUARD_INTERVAL);
}

int eDVBTransponderData::getHierarchyInformation() const
{
	return getProperty(DTV_HIERARCHY);
}

DEFINE_REF(eDVBSatelliteTransponderData);

eDVBSatelliteTransponderData::eDVBSatelliteTransponderData(struct dtv_property *dtvproperties, unsigned int propertycount, eDVBFrontendParametersSatellite &transponderparms, int frequencyoffset, bool original)
: eDVBTransponderData(dtvproperties, propertycount, original), transponderParameters(transponderparms), frequencyOffset(frequencyoffset)
{
}

std::string eDVBSatelliteTransponderData::getTunerType() const
{
	return "DVB-S";
}

int eDVBSatelliteTransponderData::getInversion() const
{
	if (originalValues) return transponderParameters.inversion;

	switch (eDVBTransponderData::getInversion())
	{
	case INVERSION_OFF: return eDVBFrontendParametersSatellite::Inversion_Off;
	case INVERSION_ON: return eDVBFrontendParametersSatellite::Inversion_On;
	default: eDebug("got unsupported inversion from frontend! report as INVERSION_AUTO!\n");
	case INVERSION_AUTO: return eDVBFrontendParametersSatellite::Inversion_Unknown;
	}
}

unsigned int eDVBSatelliteTransponderData::getFrequency() const
{
	if (originalValues) return transponderParameters.frequency;

	return eDVBTransponderData::getFrequency() + frequencyOffset;
}

unsigned int eDVBSatelliteTransponderData::getSymbolRate() const
{
	if (originalValues) return transponderParameters.symbol_rate;

	return eDVBTransponderData::getSymbolRate();
}

int eDVBSatelliteTransponderData::getOrbitalPosition() const
{
	return transponderParameters.orbital_position;
}

int eDVBSatelliteTransponderData::getFecInner() const
{
	if (originalValues) return transponderParameters.fec;

	switch (eDVBTransponderData::getFecInner())
	{
	case FEC_1_2: return eDVBFrontendParametersSatellite::FEC_1_2;
	case FEC_2_3: return eDVBFrontendParametersSatellite::FEC_2_3;
	case FEC_3_4: return eDVBFrontendParametersSatellite::FEC_3_4;
	case FEC_3_5: return eDVBFrontendParametersSatellite::FEC_3_5;
	case FEC_4_5: return eDVBFrontendParametersSatellite::FEC_4_5;
	case FEC_5_6: return eDVBFrontendParametersSatellite::FEC_5_6;
	case FEC_6_7: return eDVBFrontendParametersSatellite::FEC_6_7;
	case FEC_7_8: return eDVBFrontendParametersSatellite::FEC_7_8;
	case FEC_8_9: return eDVBFrontendParametersSatellite::FEC_8_9;
	case FEC_9_10: return eDVBFrontendParametersSatellite::FEC_9_10;
	case FEC_NONE: return eDVBFrontendParametersSatellite::FEC_None;
	default: eDebug("got unsupported FEC from frontend! report as FEC_AUTO!\n");
	case FEC_AUTO: return eDVBFrontendParametersSatellite::FEC_Auto;
	}
}

int eDVBSatelliteTransponderData::getModulation() const
{
	if (originalValues) return transponderParameters.modulation;

	switch (dtvProperties[1].u.data)
	{
	default: eDebug("got unsupported modulation from frontend! report as QPSK!");
	case QPSK: return eDVBFrontendParametersSatellite::Modulation_QPSK;
	case PSK_8: return eDVBFrontendParametersSatellite::Modulation_8PSK;
	}
}

int eDVBSatelliteTransponderData::getPolarization() const
{
	return transponderParameters.polarisation;
}

int eDVBSatelliteTransponderData::getRolloff() const
{
	if (originalValues) return transponderParameters.rolloff;

	switch (eDVBTransponderData::getRolloff())
	{
	case ROLLOFF_20: return eDVBFrontendParametersSatellite::RollOff_alpha_0_20;
	case ROLLOFF_25: return eDVBFrontendParametersSatellite::RollOff_alpha_0_25;
	case ROLLOFF_35: return eDVBFrontendParametersSatellite::RollOff_alpha_0_35;
	default:
	case ROLLOFF_AUTO: return eDVBFrontendParametersSatellite::RollOff_auto;
	}
}

int eDVBSatelliteTransponderData::getPilot() const
{
	if (originalValues) return transponderParameters.pilot;

	switch (eDVBTransponderData::getPilot())
	{
	case PILOT_OFF: return eDVBFrontendParametersSatellite::Pilot_Off;
	case PILOT_ON: return eDVBFrontendParametersSatellite::Pilot_On;
	default:
	case PILOT_AUTO: return eDVBFrontendParametersSatellite::Pilot_Unknown;
	}
}

int eDVBSatelliteTransponderData::getSystem() const
{
	if (originalValues) return transponderParameters.system;

	switch (eDVBTransponderData::getSystem())
	{
	default: eDebug("got unsupported system from frontend! report as DVBS!");
	case SYS_DVBS: return eDVBFrontendParametersSatellite::System_DVB_S;
	case SYS_DVBS2: return eDVBFrontendParametersSatellite::System_DVB_S2;
	}
}

DEFINE_REF(eDVBCableTransponderData);

eDVBCableTransponderData::eDVBCableTransponderData(struct dtv_property *dtvproperties, unsigned int propertycount, eDVBFrontendParametersCable &transponderparms, bool original)
 : eDVBTransponderData(dtvproperties, propertycount, original), transponderParameters(transponderparms)
{
}

std::string eDVBCableTransponderData::getTunerType() const
{
	return "DVB-C";
}

int eDVBCableTransponderData::getInversion() const
{
	if (originalValues) return transponderParameters.inversion;

	switch (eDVBTransponderData::getInversion())
	{
	case INVERSION_OFF: return eDVBFrontendParametersCable::Inversion_Off;
	case INVERSION_ON: return eDVBFrontendParametersCable::Inversion_On;
	default:
	case INVERSION_AUTO: return eDVBFrontendParametersCable::Inversion_Unknown;
	}
}

unsigned int eDVBCableTransponderData::getFrequency() const
{
	if (originalValues) return transponderParameters.frequency;

	return eDVBTransponderData::getFrequency() / 1000;
}

unsigned int eDVBCableTransponderData::getSymbolRate() const
{
	if (originalValues) return transponderParameters.symbol_rate;

	return eDVBTransponderData::getSymbolRate();
}

int eDVBCableTransponderData::getFecInner() const
{
	if (originalValues) return transponderParameters.fec_inner;

	switch (eDVBTransponderData::getFecInner())
	{
	case FEC_NONE: return eDVBFrontendParametersCable::FEC_None;
	case FEC_1_2: return eDVBFrontendParametersCable::FEC_1_2;
	case FEC_2_3: return eDVBFrontendParametersCable::FEC_2_3;
	case FEC_3_4: return eDVBFrontendParametersCable::FEC_3_4;
	case FEC_5_6: return eDVBFrontendParametersCable::FEC_5_6;
	case FEC_6_7: return eDVBFrontendParametersCable::FEC_6_7;
	case FEC_7_8: return eDVBFrontendParametersCable::FEC_7_8;
	case FEC_8_9: return eDVBFrontendParametersCable::FEC_7_8;
	default:
	case FEC_AUTO: return eDVBFrontendParametersCable::FEC_Auto;
	}
}

int eDVBCableTransponderData::getModulation() const
{
	if (originalValues) return transponderParameters.modulation;

	switch (eDVBTransponderData::getModulation())
	{
	case QAM_16: return eDVBFrontendParametersCable::Modulation_QAM16;
	case QAM_32: return eDVBFrontendParametersCable::Modulation_QAM32;
	case QAM_64: return eDVBFrontendParametersCable::Modulation_QAM64;
	case QAM_128: return eDVBFrontendParametersCable::Modulation_QAM128;
	case QAM_256: return eDVBFrontendParametersCable::Modulation_QAM256;
	default:
	case QAM_AUTO: return eDVBFrontendParametersCable::Modulation_Auto;
	}
}

int eDVBCableTransponderData::getSystem() const
{
	if (originalValues) return transponderParameters.system;

#ifdef SYS_DVBC_ANNEX_C
	switch (eDVBTransponderData::getSystem())
	{
	default:
	case SYS_DVBC_ANNEX_A: return eDVBFrontendParametersCable::System_DVB_C_ANNEX_A;
	case SYS_DVBC_ANNEX_C: return eDVBFrontendParametersCable::System_DVB_C_ANNEX_C;
	}
#else
	return eDVBFrontendParametersCable::System_DVB_C_ANNEX_A;
#endif
}

DEFINE_REF(eDVBTerrestrialTransponderData);

eDVBTerrestrialTransponderData::eDVBTerrestrialTransponderData(struct dtv_property *dtvproperties, unsigned int propertycount, eDVBFrontendParametersTerrestrial &transponderparms, bool original)
 : eDVBTransponderData(dtvproperties, propertycount, original), transponderParameters(transponderparms)
{
}

std::string eDVBTerrestrialTransponderData::getTunerType() const
{
	return "DVB-T";
}

int eDVBTerrestrialTransponderData::getInversion() const
{
	if (originalValues) return transponderParameters.inversion;

	switch (eDVBTransponderData::getInversion())
	{
	case INVERSION_OFF: return eDVBFrontendParametersTerrestrial::Inversion_Off;
	case INVERSION_ON: return eDVBFrontendParametersTerrestrial::Inversion_On;
	default:
	case INVERSION_AUTO: return eDVBFrontendParametersTerrestrial::Inversion_Unknown;
	}
}

unsigned int eDVBTerrestrialTransponderData::getFrequency() const
{
	if (originalValues) return transponderParameters.frequency;

	return eDVBTransponderData::getFrequency();
}

int eDVBTerrestrialTransponderData::getBandwidth() const
{
	if (originalValues) return transponderParameters.bandwidth;

	return eDVBTransponderData::getBandwidth();
}

int eDVBTerrestrialTransponderData::getCodeRateLp() const
{
	if (originalValues) return transponderParameters.code_rate_LP;

	switch (eDVBTransponderData::getCodeRateLp())
	{
	case FEC_1_2: return eDVBFrontendParametersTerrestrial::FEC_1_2;
	case FEC_2_3: return eDVBFrontendParametersTerrestrial::FEC_2_3;
	case FEC_3_4: return eDVBFrontendParametersTerrestrial::FEC_3_4;
	case FEC_5_6: return eDVBFrontendParametersTerrestrial::FEC_5_6;
	case FEC_7_8: return eDVBFrontendParametersTerrestrial::FEC_7_8;
	default:
	case FEC_AUTO: return eDVBFrontendParametersTerrestrial::FEC_Auto;
	}
}

int eDVBTerrestrialTransponderData::getCodeRateHp() const
{
	if (originalValues) return transponderParameters.code_rate_HP;

	switch (eDVBTransponderData::getCodeRateHp())
	{
	case FEC_1_2: return eDVBFrontendParametersTerrestrial::FEC_1_2;
	case FEC_2_3: return eDVBFrontendParametersTerrestrial::FEC_2_3;
	case FEC_3_4: return eDVBFrontendParametersTerrestrial::FEC_3_4;
	case FEC_5_6: return eDVBFrontendParametersTerrestrial::FEC_5_6;
	case FEC_7_8: return eDVBFrontendParametersTerrestrial::FEC_7_8;
	default:
	case FEC_AUTO: return eDVBFrontendParametersTerrestrial::FEC_Auto;
	}
}

int eDVBTerrestrialTransponderData::getConstellation() const
{
	if (originalValues) return transponderParameters.modulation;

	switch (eDVBTransponderData::getConstellation())
	{
	case QPSK: return eDVBFrontendParametersTerrestrial::Modulation_QPSK;
	case QAM_16: return eDVBFrontendParametersTerrestrial::Modulation_QAM16;
	case QAM_64: return eDVBFrontendParametersTerrestrial::Modulation_QAM64;
	case QAM_256: return eDVBFrontendParametersTerrestrial::Modulation_QAM256;
	default:
	case QAM_AUTO: return eDVBFrontendParametersTerrestrial::Modulation_Auto;
	}
}

int eDVBTerrestrialTransponderData::getTransmissionMode() const
{
	if (originalValues) return transponderParameters.transmission_mode;

	switch (eDVBTransponderData::getTransmissionMode())
	{
	case TRANSMISSION_MODE_2K: return eDVBFrontendParametersTerrestrial::TransmissionMode_2k;
	case TRANSMISSION_MODE_8K: return eDVBFrontendParametersTerrestrial::TransmissionMode_8k;
	default:
	case TRANSMISSION_MODE_AUTO: return eDVBFrontendParametersTerrestrial::TransmissionMode_Auto;
	}
}

int eDVBTerrestrialTransponderData::getGuardInterval() const
{
	if (originalValues) return transponderParameters.guard_interval;

	switch (eDVBTransponderData::getGuardInterval())
	{
	case GUARD_INTERVAL_1_32: return eDVBFrontendParametersTerrestrial::GuardInterval_1_32;
	case GUARD_INTERVAL_1_16: return eDVBFrontendParametersTerrestrial::GuardInterval_1_16;
	case GUARD_INTERVAL_1_8: return eDVBFrontendParametersTerrestrial::GuardInterval_1_8;
	case GUARD_INTERVAL_1_4: return eDVBFrontendParametersTerrestrial::GuardInterval_1_4;
	default:
	case GUARD_INTERVAL_AUTO: return eDVBFrontendParametersTerrestrial::GuardInterval_Auto;
	}
}

int eDVBTerrestrialTransponderData::getHierarchyInformation() const
{
	if (originalValues) return transponderParameters.hierarchy;

	switch (eDVBTransponderData::getHierarchyInformation())
	{
	case HIERARCHY_NONE: return eDVBFrontendParametersTerrestrial::Hierarchy_None;
	case HIERARCHY_1: return eDVBFrontendParametersTerrestrial::Hierarchy_1;
	case HIERARCHY_2: return eDVBFrontendParametersTerrestrial::Hierarchy_2;
	case HIERARCHY_4: return eDVBFrontendParametersTerrestrial::Hierarchy_4;
	default:
	case HIERARCHY_AUTO: return eDVBFrontendParametersTerrestrial::Hierarchy_Auto;
	}
}

int eDVBTerrestrialTransponderData::getSystem() const
{
	if (originalValues) return transponderParameters.system;

	switch (eDVBTransponderData::getSystem())
	{
	default:
	case SYS_DVBT: return eDVBFrontendParametersTerrestrial::System_DVB_T;
	case SYS_DVBT2: return eDVBFrontendParametersTerrestrial::System_DVB_T2;
	}
}

DEFINE_REF(eDVBATSCTransponderData);

eDVBATSCTransponderData::eDVBATSCTransponderData(struct dtv_property *dtvproperties, unsigned int propertycount, eDVBFrontendParametersATSC &transponderparms, bool original)
 : eDVBTransponderData(dtvproperties, propertycount, original), transponderParameters(transponderparms)
{
}

std::string eDVBATSCTransponderData::getTunerType() const
{
	return "ATSC";
}

int eDVBATSCTransponderData::getInversion() const
{
	if (originalValues) return transponderParameters.inversion;

	switch (eDVBTransponderData::getInversion())
	{
	case INVERSION_OFF: return eDVBFrontendParametersATSC::Inversion_Off;
	case INVERSION_ON: return eDVBFrontendParametersATSC::Inversion_On;
	default:
	case INVERSION_AUTO: return eDVBFrontendParametersATSC::Inversion_Unknown;
	}
}

unsigned int eDVBATSCTransponderData::getFrequency() const
{
	if (originalValues) return transponderParameters.frequency;

	return eDVBTransponderData::getFrequency() / 1000;
}

int eDVBATSCTransponderData::getModulation() const
{
	if (originalValues) return transponderParameters.modulation;

	switch (eDVBTransponderData::getModulation())
	{
	case QAM_16: return eDVBFrontendParametersATSC::Modulation_QAM16;
	case QAM_32: return eDVBFrontendParametersATSC::Modulation_QAM32;
	case QAM_64: return eDVBFrontendParametersATSC::Modulation_QAM64;
	case QAM_128: return eDVBFrontendParametersATSC::Modulation_QAM128;
	case QAM_256: return eDVBFrontendParametersATSC::Modulation_QAM256;
	default:
	case QAM_AUTO: return eDVBFrontendParametersATSC::Modulation_Auto;
	case VSB_8: return eDVBFrontendParametersATSC::Modulation_VSB_8;
	case VSB_16: return eDVBFrontendParametersATSC::Modulation_VSB_16;
	}
}

int eDVBATSCTransponderData::getSystem() const
{
	if (originalValues) return transponderParameters.system;

	switch (eDVBTransponderData::getSystem())
	{
	default:
	case SYS_ATSC: return eDVBFrontendParametersATSC::System_ATSC;
	case SYS_DVBC_ANNEX_B: return eDVBFrontendParametersATSC::System_DVB_C_ANNEX_B;
	}
}

DEFINE_REF(eDVBFrontendData);

eDVBFrontendData::eDVBFrontendData(ePtr<eDVBFrontend> &fe)
: frontend(fe)
{
}

int eDVBFrontendData::getNumber() const
{
	if (!frontend) return -1;
	return frontend->readFrontendData(iFrontendInformation_ENUMS::frontendNumber);
}

std::string eDVBFrontendData::getTypeDescription() const
{
	std::string result = "UNKNOWN";
	if (frontend)
	{
		if (frontend->supportsDeliverySystem(SYS_DVBS, true) || frontend->supportsDeliverySystem(SYS_DVBS2, true))
		{
			result = "DVB-S";
		}
#ifdef SYS_DVBC_ANNEX_A
		else if (frontend->supportsDeliverySystem(SYS_DVBC_ANNEX_A, true) || frontend->supportsDeliverySystem(SYS_DVBC_ANNEX_C, true))
#else
		else if (frontend->supportsDeliverySystem(SYS_DVBC_ANNEX_AC, true))
#endif
		{
			result = "DVB-C";
		}
		else if (frontend->supportsDeliverySystem(SYS_DVBT, true) || frontend->supportsDeliverySystem(SYS_DVBT2, true))
		{
			result = "DVB-T";
		}
		else if (frontend->supportsDeliverySystem(SYS_ATSC, true) || frontend->supportsDeliverySystem(SYS_DVBC_ANNEX_B, true))
		{
			result = "ATSC";
		}
	}
	return result;
}
