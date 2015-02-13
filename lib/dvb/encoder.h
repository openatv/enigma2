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

public:
	eEncoder();
	~eEncoder();

	int allocateEncoder(const std::string &serviceref, const int bitrate, const int width, const int height, const int framerate, const int interlaced, const int aspectratio);
	void freeEncoder(int encoderfd);
	int getUsedEncoderCount();

	static eEncoder *getInstance();
};

#endif /* __DVB_ENCODER_H_ */
