#ifndef __avcontrol_h
#define __avcontrol_h

#include <lib/base/object.h>

class eAVControl
{

public:
	eAVControl() = default;
	static eAVControl &getInstance()
	{
		static eAVControl m_instance;
		return m_instance;
	}

	int getFrameRate(int defaultVal = 50, int flags = 0);
	bool getProgressive(int flags = 0);
	int getResolutionX(int defaultVal = 0, int flags = 0);
	int getResolutionY(int defaultVal = 0, int flags = 0);
	std::string getVideoMode(const std::string &defaultVal = "", int flags = 0);

	void setVideoMode(const std::string &newMode, int flags = 0);
	bool setHDMIInFull(int flags = 0);
	bool setHDMIInPiP(int flags = 0);
	void disableHDMIIn(int flags = 0);

private:
	std::string m_video_mode;
	std::string m_video_mode_50;
	std::string m_video_mode_60;

	enum {
		FLAGS_DEBUG = 1,
		FLAGS_SUPPRESS_NOT_EXISTS = 2,
		FLAGS_SUPPRESS_READWRITE_ERROR = 4
	};

};

#endif
