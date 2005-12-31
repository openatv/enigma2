#ifndef __volume_h
#define __volume_h

#include <lib/base/ebase.h>

class eDVBVolumecontrol
{
private:
	static eDVBVolumecontrol *instance;
	eDVBVolumecontrol();
#ifdef SWIG
	~eDVBVolumecontrol();
#endif
	int openMixer();
	void closeMixer(int fd);
	
	bool muted;
	int leftVol, rightVol;
	
	int checkVolume(int vol);
	
public:
	static eDVBVolumecontrol* getInstance();

	void volumeUp(int left = 5, int right = 5);
	void volumeDown(int left = 5, int right = 5);

	void setVolume(int left, int right);

	void volumeMute();
	void volumeUnMute();	
	void volumeToggleMute();
			
	int getVolume();
	bool isMuted();
};

#endif //__volume_h
