#include <sys/select.h>
#include <unistd.h>
#include <string.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>

#include <lib/base/eerror.h>
#include <lib/base/init.h>
#include <lib/base/init_num.h>
#include <lib/base/wrappers.h>
#include <lib/base/cfile.h>
#include <lib/nav/core.h>
#include <lib/dvb/encoder.h>
#include <lib/service/service.h>

DEFINE_REF(eEncoder);

eEncoder *eEncoder::instance = NULL;

eEncoder *eEncoder::getInstance()
{
	return instance;
}

eEncoder::eEncoder()
{
	instance = this;
	ePtr<iServiceHandler> service_center;
	eServiceCenter::getInstance(service_center);
	if (service_center)
	{
		int index = 0;
		while (1)
		{
			int decoderindex;
			char filename[256];
			snprintf(filename, sizeof(filename), "/proc/stb/encoder/%d/decoder", index);
			if (CFile::parseInt(&decoderindex, filename) < 0) break;
			navigationInstances.push_back(new eNavigation(service_center, decoderindex));
			encoderUser.push_back(-1);
			index++;
		}
	}
}

eEncoder::~eEncoder()
{
	instance = NULL;
}

int eEncoder::allocateEncoder(const std::string &serviceref, const int bitrate, const int width, const int height, const int framerate, const int interlaced, const int aspectratio, const std::string &vcodec, const std::string &acodec)
{
	unsigned int i;
	int encoderfd = -1;
	for (i = 0; i < encoderUser.size(); i++)
	{
		if (encoderUser[i] < 0)
		{
			char filename[128];
			snprintf(filename, sizeof(filename), "/proc/stb/encoder/%d/bitrate", i);
			CFile::writeInt(filename, bitrate);
			snprintf(filename, sizeof(filename), "/proc/stb/encoder/%d/width", i);
			CFile::writeInt(filename, width);
			snprintf(filename, sizeof(filename), "/proc/stb/encoder/%d/height", i);
			CFile::writeInt(filename, height);
			snprintf(filename, sizeof(filename), "/proc/stb/encoder/%d/framerate", i);
			CFile::writeInt(filename, framerate);
			snprintf(filename, sizeof(filename), "/proc/stb/encoder/%d/interlaced", i);
			CFile::writeInt(filename, interlaced);
			snprintf(filename, sizeof(filename), "/proc/stb/encoder/%d/aspectratio", i);
			CFile::writeInt(filename, aspectratio);
			if (!vcodec.empty())
			{
				snprintf(filename, sizeof(filename), "/proc/stb/encoder/%d/vcodec_choices", i);
				if (CFile::contains_word(filename, vcodec))
				{
					snprintf(filename, sizeof(filename), "/proc/stb/encoder/%d/vcodec", i);
					CFile::write(filename, vcodec.c_str());
				}
			}
			if (!acodec.empty())
			{
				snprintf(filename, sizeof(filename), "/proc/stb/encoder/%d/acodec_choices", i);
				if (CFile::contains_word(filename, acodec))
				{
					snprintf(filename, sizeof(filename), "/proc/stb/encoder/%d/acodec", i);
					CFile::write(filename, acodec.c_str());
				}
			}
			snprintf(filename, sizeof(filename), "/proc/stb/encoder/%d/apply", i);
			CFile::writeInt(filename, 1);
			if (navigationInstances[i]->playService(serviceref) >= 0)
			{
				snprintf(filename, sizeof(filename), "/dev/encoder%d", i);
				encoderfd = open(filename, O_RDONLY);
				encoderUser[i] = encoderfd;
			}
			break;
		}
	}
	return encoderfd;
}

void eEncoder::freeEncoder(int encoderfd)
{
	unsigned int i;
	for (i = 0; i < encoderUser.size(); i++)
	{
		if (encoderUser[i] == encoderfd)
		{
			encoderUser[i] = -1;
			if (navigationInstances[i])
			{
				navigationInstances[i]->stopService();
			}
			break;
		}
	}
	if (encoderfd >= 0) ::close(encoderfd);
}

int eEncoder::getUsedEncoderCount()
{
	int count = 0;
	unsigned int i;
	for (i = 0; i < encoderUser.size(); i++)
	{
		if (encoderUser[i] >= 0)
		{
			count++;
		}
	}
	return count;
}

eAutoInitPtr<eEncoder> init_eEncoder(eAutoInitNumbers::service + 1, "Encoders");
