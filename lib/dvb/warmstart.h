#ifndef __dvb_warmstart_h
#define __dvb_warmstart_h

#include <string>

class eDVBFrontend;

// Only pre-power a previously working Unicable input. Tuner allocation,
// DiSEqC commands and service/CI startup remain owned by the normal DVB path.
class eDVBWarmStart
{
public:
	static bool load(std::string &device, int &voltage);
	static void powered(eDVBFrontend &frontend);
	static void voltageOff(eDVBFrontend &frontend);
	static bool deferClose(eDVBFrontend &frontend);
	static int remaining(eDVBFrontend &frontend, int bootTime);
	static void prepare(eDVBFrontend &frontend, eDVBFrontend &secFrontend, bool eligible, int voltage, int bootTime);
	static void tuned(eDVBFrontend &frontend, const std::string &service);
	static void save(int exitCode);
};

#endif
