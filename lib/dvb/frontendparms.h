#ifndef __lib_dvb_frontendparms_h
#define __lib_dvb_frontendparms_h

class SatelliteDeliverySystemDescriptor;
class CableDeliverySystemDescriptor;
class TerrestrialDeliverySystemDescriptor;

struct eDVBFrontendParametersSatellite
{
	struct Polarisation
	{
		enum {
			Horizontal, Vertical, CircularLeft, CircularRight
		};
	};
	struct Inversion
	{
		enum {
			Off, On, Unknown
		};
	};
	struct FEC
	{
		enum {
			fAuto, f1_2, f2_3, f3_4, f5_6, f7_8, fNone
		};
	};
	unsigned int frequency, symbol_rate;
	int polarisation, fec, inversion, orbital_position;
#ifndef SWIG	
	void set(const SatelliteDeliverySystemDescriptor  &);
#endif
};

struct eDVBFrontendParametersCable
{
	struct Inversion
	{
		enum {
			On, Off, Unknown
		};
	};
	struct FEC
	{
		enum {
			fNone, f1_2, f2_3, f3_4, f4_5, f5_6, f6_7, f7_8, f8_9, fAuto
		};
	};
	struct Modulation {
		enum {
			QAM16, QAM32, QAM64, QAM128, QAM256, Auto
		};
	};
		
	unsigned int frequency, symbol_rate;
	int modulation, inversion, fec_inner;
#ifndef SWIG
	void set(const CableDeliverySystemDescriptor  &);
#endif
};

struct eDVBFrontendParametersTerrestrial
{
	unsigned int frequency;
	struct Bandwidth {
		enum { Bw8MHz, Bw7MHz, Bw6MHz, BwAuto };
	};
	
	struct FEC
	{
		enum {
			fNone, f1_2, f2_3, f3_4, f5_6, f7_8, fAuto
		};
	};
	
	struct TransmissionMode {
		enum {
			TM2k, TM8k, TMAuto
		};
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
			QPSK, QAM16, Auto
		};
	};

	struct Inversion
	{
		enum {
			On, Off, Unknown
		};
	};
	
	int bandwidth;
	int code_rate_HP, code_rate_LP;
	int modulation;
	int transmission_mode;
	int guard_interval;
	int hierarchy;
	int inversion;

#ifndef SWIG	
	void set(const TerrestrialDeliverySystemDescriptor  &);
#endif
};

#endif
