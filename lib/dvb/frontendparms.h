#ifndef __lib_dvb_frontendparms_h
#define __lib_dvb_frontendparms_h

#include <vector>

#include <dvbsi++/satellite_delivery_system_descriptor.h>
#include <dvbsi++/cable_delivery_system_descriptor.h>
#include <dvbsi++/terrestrial_delivery_system_descriptor.h>

#include <lib/python/swig.h>
#include <lib/dvb/idvb.h>

#include <linux/dvb/frontend.h>

struct eDVBFrontendParametersSatellite
{
#ifndef SWIG
	void set(const SatelliteDeliverySystemDescriptor  &);
#endif
	enum {
		Polarisation_Horizontal, Polarisation_Vertical, Polarisation_CircularLeft, Polarisation_CircularRight
	};

	enum {
		Inversion_Off, Inversion_On, Inversion_Unknown
	};

	/* WARNING: do not change the order of these values, they are used to parse lamedb and satellites.xml FEC fields */
	enum {
		FEC_Auto=0, FEC_1_2=1, FEC_2_3=2, FEC_3_4=3, FEC_5_6=4, FEC_7_8=5, FEC_8_9=6, FEC_3_5=7, FEC_4_5=8, FEC_9_10=9, FEC_6_7=10, FEC_None=15
	};

	enum {
		System_DVB_S, System_DVB_S2
	};

	enum {
		Modulation_Auto, Modulation_QPSK, Modulation_8PSK, Modulation_QAM16
	};

	// dvb-s2
	enum {
		RollOff_alpha_0_35, RollOff_alpha_0_25, RollOff_alpha_0_20, RollOff_auto
	};

	enum {
		Pilot_Off, Pilot_On, Pilot_Unknown
	};

	bool no_rotor_command_on_tune;
	unsigned int frequency, symbol_rate;
	int polarisation, fec, inversion, orbital_position, system, modulation, rolloff, pilot;
};
SWIG_ALLOW_OUTPUT_SIMPLE(eDVBFrontendParametersSatellite);

struct eDVBFrontendParametersCable
{
#ifndef SWIG
	void set(const CableDeliverySystemDescriptor  &);
#endif
	enum {
		Inversion_Off, Inversion_On, Inversion_Unknown
	};

	/*
	 * WARNING: do not change the order of these values, they are used to parse lamedb and cables.xml FEC fields.
	 * The values are the same as those in eDVBFrontendParametersSatellite.
	 */
	enum {
		FEC_Auto=0, FEC_1_2=1, FEC_2_3=2, FEC_3_4=3, FEC_5_6=4, FEC_7_8=5, FEC_8_9=6, FEC_3_5=7, FEC_4_5=8, FEC_9_10=9, FEC_6_7=10, FEC_None=15
	};

	enum {
		System_DVB_C_ANNEX_A, System_DVB_C_ANNEX_C
	};

	enum {
		Modulation_Auto, Modulation_QAM16, Modulation_QAM32, Modulation_QAM64, Modulation_QAM128, Modulation_QAM256
	};

	unsigned int frequency, symbol_rate;
	int modulation, inversion, fec_inner, system;
};
SWIG_ALLOW_OUTPUT_SIMPLE(eDVBFrontendParametersCable);

struct eDVBFrontendParametersTerrestrial
{
#ifndef SWIG
	void set(const TerrestrialDeliverySystemDescriptor  &);
#endif
	enum {
		Bandwidth_8MHz, Bandwidth_7MHz, Bandwidth_6MHz, Bandwidth_Auto, Bandwidth_5MHz, Bandwidth_1_712MHz, Bandwidth_10MHz
	};

	/*
	 * WARNING: do not change the order of these values, they are used to parse lamedb and terrestrial.xml FEC fields.
	 * The values are NOT the same as those in eDVBFrontendParametersSatellite/eDVBFrontendParametersCable
	 * (and it's too late to fix this now, we would break backward compatibility)
	 */
	enum {
		FEC_1_2=0, FEC_2_3=1, FEC_3_4=2, FEC_5_6=3, FEC_7_8=4, FEC_Auto=5, FEC_6_7=6, FEC_8_9=7
	};

	enum {
		System_DVB_T_T2 = -1, System_DVB_T, System_DVB_T2
	};

	enum {
		TransmissionMode_2k, TransmissionMode_8k, TransmissionMode_Auto, TransmissionMode_4k, TransmissionMode_1k, TransmissionMode_16k, TransmissionMode_32k
	};

	enum {
		GuardInterval_1_32, GuardInterval_1_16, GuardInterval_1_8, GuardInterval_1_4, GuardInterval_Auto, GuardInterval_1_128, GuardInterval_19_128, GuardInterval_19_256
	};

	enum {
		Hierarchy_None, Hierarchy_1, Hierarchy_2, Hierarchy_4, Hierarchy_Auto
	};

	enum {
		Modulation_QPSK, Modulation_QAM16, Modulation_QAM64, Modulation_Auto, Modulation_QAM256
	};

	enum {
		Inversion_Off, Inversion_On, Inversion_Unknown
	};

	unsigned int frequency;
	int bandwidth;
	int code_rate_HP, code_rate_LP;
	int modulation;
	int transmission_mode;
	int guard_interval;
	int hierarchy;
	int inversion;
	int system;
	int plpid;
};
SWIG_ALLOW_OUTPUT_SIMPLE(eDVBFrontendParametersTerrestrial);

struct eDVBFrontendParametersATSC
{
	enum {
		Inversion_Off, Inversion_On, Inversion_Unknown
	};

	enum {
		System_ATSC, System_DVB_C_ANNEX_B
	};

	enum {
		Modulation_Auto, Modulation_QAM16, Modulation_QAM32, Modulation_QAM64, Modulation_QAM128, Modulation_QAM256, Modulation_VSB_8, Modulation_VSB_16
	};

	unsigned int frequency;
	int modulation, inversion, system;
};
SWIG_ALLOW_OUTPUT_SIMPLE(eDVBFrontendParametersATSC);

#ifndef SWIG

class eDVBFrontend;

class eDVBFrontendStatus : public iDVBFrontendStatus
{
	DECLARE_REF(eDVBFrontendStatus);

	ePtr<eDVBFrontend> frontend;

public:
	eDVBFrontendStatus(ePtr<eDVBFrontend> &fe);

	int getState() const;
	std::string getStateDescription() const;
	int getLocked() const;
	int getSynced() const;
	int getBER() const;
	int getSNR() const;
	int getSNRdB() const;
	int getSignalPower() const;
};

class eDVBTransponderData : public iDVBTransponderData
{
protected:
	std::vector<struct dtv_property> dtvProperties;
	bool originalValues;
	int getProperty(unsigned int cmd) const;

public:
	eDVBTransponderData(struct dtv_property *dtvproperties, unsigned int propertycount, bool original);

	int getInversion() const;
	unsigned int getFrequency() const;
	unsigned int getSymbolRate() const;
	int getOrbitalPosition() const;
	int getFecInner() const;
	int getModulation() const;
	int getPolarization() const;
	int getRolloff() const;
	int getPilot() const;
	int getSystem() const;
	int getBandwidth() const;
	int getCodeRateLp() const;
	int getCodeRateHp() const;
	int getConstellation() const;
	int getTransmissionMode() const;
	int getGuardInterval() const;
	int getHierarchyInformation() const;
	int getPlpId() const;
};

class eDVBSatelliteTransponderData : public eDVBTransponderData
{
	DECLARE_REF(eDVBSatelliteTransponderData);

	eDVBFrontendParametersSatellite transponderParameters;
	int frequencyOffset;

public:
	eDVBSatelliteTransponderData(struct dtv_property *dtvproperties, unsigned int propertycount, eDVBFrontendParametersSatellite &transponderparms, int frequencyoffset, bool original);

	std::string getTunerType() const;
	int getInversion() const;
	unsigned int getFrequency() const;
	unsigned int getSymbolRate() const;
	int getOrbitalPosition() const;
	int getFecInner() const;
	int getModulation() const;
	int getPolarization() const;
	int getRolloff() const;
	int getPilot() const;
	int getSystem() const;
};

class eDVBCableTransponderData : public eDVBTransponderData
{
	DECLARE_REF(eDVBCableTransponderData);

	eDVBFrontendParametersCable transponderParameters;

public:
	eDVBCableTransponderData(struct dtv_property *dtvproperties, unsigned int propertycount, eDVBFrontendParametersCable &transponderparms, bool original);

	std::string getTunerType() const;
	int getInversion() const;
	unsigned int getFrequency() const;
	unsigned int getSymbolRate() const;
	int getFecInner() const;
	int getModulation() const;
	int getSystem() const;
};

class eDVBTerrestrialTransponderData : public eDVBTransponderData
{
	DECLARE_REF(eDVBTerrestrialTransponderData);

	eDVBFrontendParametersTerrestrial transponderParameters;

public:
	eDVBTerrestrialTransponderData(struct dtv_property *dtvproperties, unsigned int propertycount, eDVBFrontendParametersTerrestrial &transponderparms, bool original);

	std::string getTunerType() const;
	int getInversion() const;
	unsigned int getFrequency() const;
	int getBandwidth() const;
	int getCodeRateLp() const;
	int getCodeRateHp() const;
	int getConstellation() const;
	int getTransmissionMode() const;
	int getGuardInterval() const;
	int getHierarchyInformation() const;
	int getPlpId() const;
	int getSystem() const;
};

class eDVBATSCTransponderData : public eDVBTransponderData
{
	DECLARE_REF(eDVBATSCTransponderData);

	eDVBFrontendParametersATSC transponderParameters;

public:
	eDVBATSCTransponderData(struct dtv_property *dtvproperties, unsigned int propertycount, eDVBFrontendParametersATSC &transponderparms, bool original);

	std::string getTunerType() const;
	int getInversion() const;
	unsigned int getFrequency() const;
	int getModulation() const;
	int getSystem() const;
};

class eDVBFrontendData : public iDVBFrontendData
{
	DECLARE_REF(eDVBFrontendData);

	ePtr<eDVBFrontend> frontend;

public:
	eDVBFrontendData(ePtr<eDVBFrontend> &fe);

	int getNumber() const;
	std::string getTypeDescription() const;
};
#endif

#endif
