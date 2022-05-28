#include <lib/dvb/fccdecoder.h>
#include <lib/base/eerror.h>

#include <fcntl.h>
#include <sys/ioctl.h>
#include <sys/types.h>
#include <sys/stat.h>

bool eFCCDecoder::isDestroyed = false;
eFCCDecoder::eFCCDecoder()
{
	int index = 0;

	eDebug("[eFCCDecoder] Scanning for FCC device files..");
	while(1)
	{
		struct stat s;
		char filename[128];
		sprintf(filename, "/dev/fcc%d", index);
		if (stat(filename, &s))
			break;

		eDebug("[eFCCDecoder] %s found..", filename);
		m_fccs.push_back(-1);
		index++;
	}
}

eFCCDecoder::~eFCCDecoder()
{
	isDestroyed = true;
}

int eFCCDecoder::allocateFcc()
{
	int fccFd = -1;
	for(unsigned int i = 0; i < m_fccs.size(); i++)
	{
		if (m_fccs[i]== -1)
		{
			char filename[128];
			sprintf(filename, "/dev/fcc%d", i);

			fccFd = ::open(filename, O_RDWR);
			if (fccFd < 0)
				eDebug("[eFCCDecoder] Open %s failed!", filename);

			else
				eDebug("[eFCCDecoder] Alloc %s", filename);

			m_fccs[i] = fccFd;
			break;
		}
	}

	return fccFd;
}

void eFCCDecoder::freeFcc(int fccFd)
{
	if (fccFd < 0)
		return;

	for(unsigned int i = 0; i < m_fccs.size(); i++)
	{
		if (m_fccs[i]== fccFd)
		{
			m_fccs[i] = -1;
			eDebug("[eFCCDecoder] Close /dev/fcc%d", i);
			::close(fccFd);
			break;
		}
	}
}

