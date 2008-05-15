#ifndef __lib_dvb_frontendparms_h
#define __lib_dvb_frontendparms_h

#include <lib/python/swig.h>

class SatelliteDeliverySystemDescriptor;
class CableDeliverySystemDescriptor;
class TerrestrialDeliverySystemDescriptor;

struct eDVBFrontendParametersSatellite
{
#ifndef SWIG
	void set(const SatelliteDeliverySystemDescriptor  &);
#endif
	struct Polarisation {
		enum {
			Horizontal, Vertical, CircularLeft, CircularRight
		};
	};
	struct Inversion {
		enum {
			Off, On, Unknown
		};
	};
	struct FEC {
		enum {
			fAuto, f1_2, f2_3, f3_4, f5_6, f7_8, f8_9, f3_5, f4_5, f9_10, fNone=15
		};
	};
	struct System {
		enum {
			DVB_S, DVB_S2
		};
	};
	struct Modulation {
		enum {
			Auto, QPSK, M8PSK, QAM_16
		};
	};
	// dvb-s2
	struct RollOff {
		enum {
			alpha_0_35, alpha_0_25, alpha_0_20
		};
	};
	// only 8psk
	struct Pilot {  
		enum {
			Off, On, Unknown
		};
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
	struct Inversion {
		enum {
			Off, On, Unknown
		};
	};
	struct FEC {
		enum {
			fAuto, f1_2, f2_3, f3_4, f5_6, f7_8, f8_9, fNone=15
		};
	};
	struct Modulation {
		enum {
			Auto, QAM16, QAM32, QAM64, QAM128, QAM256
		};
	};
	unsigned int frequency, symbol_rate;
	int modulation, inversion, fec_inner;
};
SWIG_ALLOW_OUTPUT_SIMPLE(eDVBFrontendParametersCable);

struct eDVBFrontendParametersTerrestrial
{
#ifndef SWIG
	void set(const TerrestrialDeliverySystemDescriptor  &);
#endif
	struct Bandwidth {
		enum {
			Bw8MHz, Bw7MHz, Bw6MHz, /*Bw5MHz,*/ BwAuto
		}; // Bw5Mhz nyi (compatibilty with enigma1)
	};
	struct FEC {
		enum {
			f1_2, f2_3, f3_4, f5_6, f7_8, fAuto
		};
	};
	struct TransmissionMode {
		enum {
			TM2k, TM8k, /*TM4k,*/ TMAuto
		}; // TM4k nyi (compatibility with enigma1)
	};
	struct GuardInterval {
		enum {
			GI_1_32, GI_1_16, GI_1_8, GI_1_4, GI_Auto
		};
	};
	struct Hierarchy {
		enum {
			HNone, H1, H2, H4, HAuto
		};
	};
	struct Modulation {
		enum {
			QPSK, QAM16, QAM64, Auto
		};
	};
	struct Inversion
	{
		enum {
			Off, On, Unknown
		};
	};
	unsigned int frequency;
	int bandwidth;
	int code_rate_HP, code_rate_LP;
	int modulation;
	int transmission_mode;
	int guard_interval;
	int hierarchy;
	int inversion;
};
SWIG_ALLOW_OUTPUT_SIMPLE(eDVBFrontendParametersTerrestrial);

#endif
