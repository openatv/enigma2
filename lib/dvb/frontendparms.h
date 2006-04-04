#ifndef __lib_dvb_frontendparms_h
#define __lib_dvb_frontendparms_h

class SatelliteDeliverySystemDescriptor;
class CableDeliverySystemDescriptor;
class TerrestrialDeliverySystemDescriptor;

struct eDVBFrontendParametersSatellite
{
#ifndef SWIG
	void set(const SatelliteDeliverySystemDescriptor  &);
#endif
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
			fAuto, f1_2, f2_3, f3_4, f5_6, f7_8, f8_9, fNone
		};
	};
	bool no_rotor_command_on_tune;
	unsigned int frequency, symbol_rate;
	int polarisation, fec, inversion, orbital_position;
};

struct eDVBFrontendParametersCable
{
#ifndef SWIG
	void set(const CableDeliverySystemDescriptor  &);
#endif
	struct Inversion
	{
		enum {
			Off, On, Unknown
		};
	};
	struct FEC
	{
		enum {
			fAuto, f1_2, f2_3, f3_4, f5_6, f7_8, f8_9, fNone
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

struct eDVBFrontendParametersTerrestrial
{
#ifndef SWIG
 void set(const TerrestrialDeliverySystemDescriptor  &);
#endif
	struct Bandwidth {
		enum { Bw8MHz, Bw7MHz, Bw6MHz, Bw5MHz, BwAuto };
	};
	struct FEC
	{
		enum {
			f1_2, f2_3, f3_4, f5_6, f7_8, fAuto
		};
	};
	struct TransmissionMode {
		enum {
			TM2k, TM8k, TM4k, TMAuto
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

#endif
