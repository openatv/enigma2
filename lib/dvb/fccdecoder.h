#ifndef __dvb_fcc_decoder_h
#define __dvb_fcc_decoder_h

#include <vector>

class eFCCDecoder
{
	std::vector<int> m_fccs;
	static eFCCDecoder *instance;
	static bool isDestroyed;

public:
	eFCCDecoder();
	~eFCCDecoder();
	int allocateFcc();
	void freeFcc(int fccFd);

	static eFCCDecoder* getInstance()
	{
		if (isDestroyed)
			return NULL;

		static eFCCDecoder instance;
		return &instance;
	}
};

#endif /* __dvb_fcc_decoder_h */
