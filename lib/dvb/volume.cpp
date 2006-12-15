#include <lib/base/eerror.h>
#include <lib/dvb/volume.h>
#include <stdio.h>
#include <fcntl.h>
#include <sys/ioctl.h>
#include <unistd.h>

#if HAVE_DVB_API_VERSION < 3
#define VIDEO_DEV "/dev/dvb/card0/video0"
#define AUDIO_DEV "/dev/dvb/card0/audio0"
#include <ost/audio.h>
#include <ost/video.h>
#else
#define VIDEO_DEV "/dev/dvb/adapter0/video0"
#define AUDIO_DEV "/dev/dvb/adapter0/audio0"
#include <linux/dvb/audio.h>
#include <linux/dvb/video.h>
#endif

eDVBVolumecontrol* eDVBVolumecontrol::instance = NULL;

eDVBVolumecontrol* eDVBVolumecontrol::getInstance()
{
	if (instance == NULL)
		instance = new eDVBVolumecontrol;
	return instance;
}

eDVBVolumecontrol::eDVBVolumecontrol()
{
	volumeUnMute();
	setVolume(100, 100);
}

int eDVBVolumecontrol::openMixer()
{
	return open( AUDIO_DEV, O_RDWR );
}

void eDVBVolumecontrol::closeMixer(int fd)
{
	close(fd);
}

void eDVBVolumecontrol::volumeUp(int left, int right)
{
	setVolume(leftVol + left, rightVol + right);
}

void eDVBVolumecontrol::volumeDown(int left, int right)
{
	setVolume(leftVol - left, rightVol - right);
}

int eDVBVolumecontrol::checkVolume(int vol)
{
	if (vol < 0)
		vol = 0;
	else if (vol > 100)
		vol = 100;
	return vol;
}

void eDVBVolumecontrol::setVolume(int left, int right)
{
		/* left, right is 0..100 */
	leftVol = checkVolume(left);
	rightVol = checkVolume(right);
	
		/* convert to -1dB steps */
	left = 63 - leftVol * 63 / 100;
	right = 63 - rightVol * 63 / 100;
		/* now range is 63..0, where 0 is loudest */

#if HAVE_DVB_API_VERSION < 3
	audioMixer_t mixer;
#else
	audio_mixer_t mixer;
#endif

#if HAVE_DVB_API_VERSION < 3
		/* convert to linear scale. 0 = loudest, ..63 */
	mixer.volume_left = 63.0-pow(1.068241, 63-left);
	mixer.volume_right = 63.0-pow(1.068241, 63-right);
#else
	mixer.volume_left = left;
	mixer.volume_right = right;
#endif

	eDebug("Setvolume: %d %d (raw)", leftVol, rightVol);
	eDebug("Setvolume: %d %d (-1db)", left, right);
#if HAVE_DVB_API_VERSION < 3
	eDebug("Setvolume: %d %d (lin)", mixer.volume_left, mixer.volume_right);
#endif

	int fd = openMixer();
	if (fd >= 0)
	{
#ifdef HAVE_DVB_API_VERSION
		ioctl(fd, AUDIO_SET_MIXER, &mixer);
#endif
		closeMixer(fd);
		return;
	}

	//HACK?
	FILE *f;
	if((f = fopen("/proc/stb/avs/0/volume", "wb")) == NULL) {
		eDebug("cannot open /proc/stb/avs/0/volume(%m)");
		return;
	}

	fprintf(f, "%d", left); /* in -1dB */

	fclose(f);
}

int eDVBVolumecontrol::getVolume()
{
	return leftVol;
}

bool eDVBVolumecontrol::isMuted()
{
	return muted;
}


void eDVBVolumecontrol::volumeMute()
{
	int fd = openMixer();
#ifdef HAVE_DVB_API_VERSION	
	ioctl(fd, AUDIO_SET_MUTE, true);
#endif
	closeMixer(fd);
	muted = true;

	//HACK?
	FILE *f;
	if((f = fopen("/proc/stb/audio/j1_mute", "wb")) == NULL) {
		eDebug("cannot open /proc/stb/audio/j1_mute(%m)");
		return;
	}
	
	fprintf(f, "%d", 1);

	fclose(f);
}

void eDVBVolumecontrol::volumeUnMute()
{
	int fd = openMixer();
#ifdef HAVE_DVB_API_VERSION
	ioctl(fd, AUDIO_SET_MUTE, false);
#endif
	closeMixer(fd);
	muted = false;

	//HACK?
	FILE *f;
	if((f = fopen("/proc/stb/audio/j1_mute", "wb")) == NULL) {
		eDebug("cannot open /proc/stb/audio/j1_mute(%m)");
		return;
	}
	
	fprintf(f, "%d", 0);

	fclose(f);
}

void eDVBVolumecontrol::volumeToggleMute()
{
	if (isMuted())
		volumeUnMute();
	else
		volumeMute();
}
