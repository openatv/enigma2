#ifndef __avcontrol_h
#define __avcontrol_h

#include <lib/base/object.h>

class eAVControl
{
	static eAVControl *instance;
#ifdef SWIG
	eAVControl();
#endif
public:
#ifndef SWIG
	eAVControl();
#endif
	static eAVControl *getInstance();

	int getFrameRate(int defaultVal=50, bool debug=false);
	bool getProgressive(bool debug=false);
	int getResolutionX(int defaultVal=0, bool debug=false);
	int getResolutionY(int defaultVal=0, bool debug=false);
	std::string getVideoMode(std::string defaultVal="", bool debug=false);

	void setVideoMode(std::string newMode, bool debug=false);

};

#endif
