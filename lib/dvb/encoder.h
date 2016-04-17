#ifndef __DVB_ENCODER_H_
#define __DVB_ENCODER_H_

#include <vector>

#include <lib/nav/core.h>

class eEncoder
{
	DECLARE_REF(eEncoder);

	std::vector<eNavigation *> navigationInstances;
	std::vector<int> encoderUser;

	static eEncoder *instance;

	enum {
		hdmiPatPid = 0x00, // 0
		hdmiPcrPid = 0x13, // 19
		hdmiPmtPid = 0x55, // 85
		hdmiAudioPid = 0xC0, // 196
		hdmiVideoPid = 0xE0, // 224
	};
public:
	eEncoder();
	~eEncoder();

	int allocateEncoder(const std::string &serviceref, const int bitrate, const int width, const int height, const int framerate, const int interlaced, const int aspectratio);
	void freeEncoder(int encoderfd);
	int getUsedEncoderCount();

	int getPatPid() { return hdmiPatPid; }
	int getPcrPid() { return hdmiPcrPid; }
	int getPmtPid() { return hdmiPmtPid; }
	int getAudioPid() { return hdmiAudioPid; }
	int getVideoPid() { return hdmiVideoPid; }

	static eEncoder *getInstance();
};

#endif /* __DVB_ENCODER_H_ */
