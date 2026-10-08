#include <lib/base/cfile.h>
#include <lib/base/eerror.h>
#include <lib/dvb/volume.h>
#include <stdio.h>
#include <fcntl.h>
#include <math.h>
#include <sys/ioctl.h>
#include <unistd.h>

#include <linux/dvb/version.h>
#if DVB_API_VERSION < 3
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

#ifdef HAVE_ALSA
#ifndef ALSA_VOLUME_MIXER
#define ALSA_VOLUME_MIXER "Master"
#endif
#ifndef ALSA_CARD
#define ALSA_CARD "default"
#endif
#endif

eDVBVolumecontrol *eDVBVolumecontrol::instance = NULL;

#ifdef DREAMNEXTGEN
eDVBVolumecontrol::VolumeChangeCb eDVBVolumecontrol::s_volume_change_cb = nullptr;
void eDVBVolumecontrol::registerVolumeChangeCb(VolumeChangeCb cb)
{
	s_volume_change_cb = cb;
}
#endif

eDVBVolumecontrol *eDVBVolumecontrol::getInstance()
{
	if (instance == NULL)
		instance = new eDVBVolumecontrol;
	return instance;
}

eDVBVolumecontrol::eDVBVolumecontrol()
	: m_volsteps(5)
{
#ifdef HAVE_ALSA
	mainVolume = NULL;
	alsaMixerHandle = NULL;
#ifdef DREAMNEXTGEN
	// AMLogic-specific ALSA mixer init
	alsa_card    = ALSA_CARD;   // default device
	alsa_has_db  = false;
	alsa_min_raw = 0;
	alsa_max_raw = 100;
	alsa_min_db  = 0;
	alsa_max_db  = 0;
	// Mixer is opened lazily in ensureMixer()
#else
	// Other boxes: open eagerly
	openMixer();
#endif // DREAMNEXTGEN
#endif // HAVE_ALSA
	mute_zero = false;
	m_VolumeOffset = 0;
	volumeUnMute();
	setVolume(100, 100);
}

int eDVBVolumecontrol::openMixer()
{
#ifdef HAVE_ALSA
#ifdef DREAMNEXTGEN
	// AMLogic uses the robust lazy mixer init
	return ensureMixer() ? 0 : -1;
#else
	if (!mainVolume)
	{
		int err;
		char *card = ALSA_CARD;

		eDebug("[eDVBVolumecontrol] Setup ALSA Mixer hw:0:0 - Master %s %s.", ALSA_CARD, ALSA_VOLUME_MIXER);
		/* Perform the necessary pre-amble to start up ALSA Mixer */
		err = snd_mixer_open(&alsaMixerHandle, 0);
		if (err < 0)
		{
			eDebug("[eDVBVolumecontrol] Error: Unable to open mixer %s!  (%s)", card, snd_strerror(err));
			return err;
		}
		err = snd_mixer_attach(alsaMixerHandle, card);
		if (err < 0)
		{
			eDebug("[eDVBVolumecontrol] Error: Unable to attach mixer to hw:0:0!  (No such device '%s' - %s)", card, snd_strerror(err));
			snd_mixer_close(alsaMixerHandle);
			alsaMixerHandle = NULL;
			return err;
		}
		err = snd_mixer_selem_register(alsaMixerHandle, NULL, NULL);
		if (err < 0)
		{
			eDebug("[eDVBVolumecontrol] Error: Unable to register mixer!  (%s)", snd_strerror(err));
			snd_mixer_close(alsaMixerHandle);
			alsaMixerHandle = NULL;
			return err;
		}
		err = snd_mixer_load(alsaMixerHandle);
		if (err < 0)
		{
			eDebug("[eDVBVolumecontrol] Error: Unable to load mixer '%s'!  (%s)", card, snd_strerror(err));
			snd_mixer_close(alsaMixerHandle);
			alsaMixerHandle = NULL;
			return err;
		}

		/* Set up Decoder 0 as the main volume control. */
		snd_mixer_selem_id_t *sid;
		snd_mixer_selem_id_alloca(&sid);
		snd_mixer_selem_id_set_name(sid, ALSA_VOLUME_MIXER);
		snd_mixer_selem_id_set_index(sid, 0);
		mainVolume = snd_mixer_find_selem(alsaMixerHandle, sid);
	}
	return mainVolume ? 0 : -1;
#endif // DREAMNEXTGEN
#else
	return open(AUDIO_DEV, O_RDWR);
#endif
}

#ifdef HAVE_ALSA
#ifdef DREAMNEXTGEN

/* Linear-amplitude curve dB = 20·log10(level/100) on the HW Master. */
static void da_set_master(snd_mixer_elem_t *elem, int level,
                          bool has_db, long min_db, long max_db)
{
    if (!elem) return;
    if (has_db) {
        long target_db;
        if (level <= 0)        target_db = min_db;
        else if (level >= 100) target_db = max_db;
        else {
            target_db = (long)(2000.0 * log10((double)level / 100.0));
            if (target_db < min_db) target_db = min_db;
            if (target_db > max_db) target_db = max_db;
        }
        snd_mixer_selem_set_playback_dB_all(elem, target_db, 0);
    } else {
        long rmin = 0, rmax = 100;
        snd_mixer_selem_get_playback_volume_range(elem, &rmin, &rmax);
        snd_mixer_selem_set_playback_volume_all(elem,
            rmin + (rmax - rmin) * level / 100);
    }
}

bool eDVBVolumecontrol::ensureMixer()
{
	if (alsaMixerHandle && mainVolume)
		return true;

	int err;

	if (!alsaMixerHandle)
	{
		if ((err = snd_mixer_open(&alsaMixerHandle, 0)) < 0)
		{
			eDebug("[eDVBVolumecontrol] mixer open failed: %s", snd_strerror(err));
			alsaMixerHandle = NULL;
			return false;
		}
		if ((err = snd_mixer_attach(alsaMixerHandle, alsa_card)) < 0)
		{
			eDebug("[eDVBVolumecontrol] attach '%s' failed: %s", alsa_card, snd_strerror(err));
			snd_mixer_close(alsaMixerHandle);
			alsaMixerHandle = NULL;
			return false;
		}
		if ((err = snd_mixer_selem_register(alsaMixerHandle, NULL, NULL)) < 0)
		{
			eDebug("[eDVBVolumecontrol] selem_register failed: %s", snd_strerror(err));
			snd_mixer_close(alsaMixerHandle);
			alsaMixerHandle = NULL;
			return false;
		}
		if ((err = snd_mixer_load(alsaMixerHandle)) < 0)
		{
			eDebug("[eDVBVolumecontrol] mixer_load failed: %s", snd_strerror(err));
			snd_mixer_close(alsaMixerHandle);
			alsaMixerHandle = NULL;
			return false;
		}
	}

	if (!mainVolume)
	{
		// Try common control names (first match wins)
		const char *candidates[] = {
			"Master",
			"PCM Playback Volume",
			"LPCM Playback Volume",
			"PCM"
		};

		snd_mixer_selem_id_t *sid = 0;
		snd_mixer_selem_id_alloca(&sid);
		snd_mixer_selem_id_set_index(sid, 0);

		for (unsigned i = 0; i < sizeof(candidates)/sizeof(candidates[0]); ++i)
		{
			snd_mixer_selem_id_set_name(sid, candidates[i]);
			snd_mixer_elem_t *e = snd_mixer_find_selem(alsaMixerHandle, sid);
			if (e && snd_mixer_selem_has_playback_volume(e))
			{
				mainVolume = e;
				break;
			}
		}

		if (!mainVolume)
		{
			eDebug("[eDVBVolumecontrol] no suitable mixer element found");
			return false;
		}

		// Decide whether to use dB or raw scaling
		if (snd_mixer_selem_get_playback_dB_range(mainVolume, &alsa_min_db, &alsa_max_db) == 0
		    && alsa_max_db > alsa_min_db)
		{
			alsa_has_db = true;
		}
		else
		{
			alsa_has_db = false;
			long rmin = 0, rmax = 0;
			snd_mixer_selem_get_playback_volume_range(mainVolume, &rmin, &rmax);
			alsa_min_raw = rmin;
			alsa_max_raw = rmax;
		}
	}

	return true;
}

long eDVBVolumecontrol::uiToHw(int ui) const
{
	if (ui < 0) ui = 0;
	if (ui > 100) ui = 100;

	if (alsa_has_db)
	{
		// Map 0..100 to millibels [alsa_min_db..alsa_max_db]
		const long span = alsa_max_db - alsa_min_db;
		long val = alsa_min_db + (span * ui + 50) / 100;
		if (val < alsa_min_db) val = alsa_min_db;
		if (val > alsa_max_db) val = alsa_max_db;
		return val;
	}
	else
	{
		// Map 0..100 to raw [alsa_min_raw..alsa_max_raw]
		const long span = alsa_max_raw - alsa_min_raw;
		long val = alsa_min_raw + (span * ui + 50) / 100;
		if (val < alsa_min_raw) val = alsa_min_raw;
		if (val > alsa_max_raw) val = alsa_max_raw;
		return val;
	}
}

int eDVBVolumecontrol::hwToUi(long hw) const
{
	if (alsa_has_db)
	{
		const long span = alsa_max_db - alsa_min_db;
		if (span <= 0) return 0;
		long ui = ((hw - alsa_min_db) * 100 + span / 2) / span;
		if (ui < 0) ui = 0;
		if (ui > 100) ui = 100;
		return (int)ui;
	}
	else
	{
		const long span = alsa_max_raw - alsa_min_raw;
		if (span <= 0) return 0;
		long ui = ((hw - alsa_min_raw) * 100 + span / 2) / span;
		if (ui < 0) ui = 0;
		if (ui > 100) ui = 100;
		return (int)ui;
	}
}

#endif // DREAMNEXTGEN
#endif // HAVE_ALSA


void eDVBVolumecontrol::closeMixer(int fd)
{
#ifdef HAVE_ALSA
	/* we want to keep the alsa mixer */
#else
	if (fd >= 0)
		close(fd);
#endif
}

/**
 * @brief Increases the volume for the left and right channels.
 *
 * This function increases the volume for the left and right audio channels by the specified amounts.
 * If the specified amount is zero, the volume is increased by a default step value.
 *
 * @param left The amount to increase the left channel volume. If zero, the volume is increased by the default step value.
 * @param right The amount to increase the right channel volume. If zero, the volume is increased by the default step value.
 * @return The new volume level for the left channel.
 */
int eDVBVolumecontrol::volumeUp(int left, int right)
{
	setVolume(leftVol + (left ? left : m_volsteps), rightVol + (right ? right : m_volsteps));
	return leftVol;
}

/**
 * Decreases the volume for the left and right channels.
 *
 * @param left The amount to decrease the left channel volume. If zero, the default volume step is used.
 * @param right The amount to decrease the right channel volume. If zero, the default volume step is used.
 * @return The new volume level for the left channel after the decrease.
 */
int eDVBVolumecontrol::volumeDown(int left, int right)
{
	setVolume(leftVol - (left ? left : m_volsteps), rightVol - (right ? right : m_volsteps));
	return leftVol;
}

/**
 * @brief Adjusts the volume to ensure it is within the valid range.
 *
 * This function takes an integer volume value and checks if it is within the
 * acceptable range of 0 to 100. If the volume is less than 0, it sets it to 0.
 * If the volume is greater than 100, it sets it to 100. Otherwise, it returns
 * the original volume value.
 *
 * @param vol The volume value to be checked and adjusted.
 * @return The adjusted volume value, guaranteed to be within the range [0, 100].
 */
int eDVBVolumecontrol::checkVolume(int vol)
{
	if (vol < 0)
		vol = 0;
	else if (vol > 100)
		vol = 100;
	return vol;
}

/**
 * @brief Sets the volume for the left and right channels.
 *
 * This function adjusts the volume levels for the left and right audio channels.
 * The input volume levels are expected to be in the range of 0 to 100.
 * Depending on the system configuration, it either uses ALSA or a custom mixer
 * to set the volume.
 *
 * @param left The volume level for the left channel (0 to 100).
 * @param right The volume level for the right channel (0 to 100).
 * @return The adjusted left volume level.
 */
int eDVBVolumecontrol::setVolume(int left, int right)
{
	/* left, right is 0..100 */
	leftVol = checkVolume(left);
	rightVol = checkVolume(right);

	m_BaseVolume = (m_VolumeOffset != 0) ? checkVolume(leftVol - m_VolumeOffset) : leftVol;

#ifdef HAVE_ALSA
	eDebug("[eDVBVolumecontrol] Setvolume: ALSA leftVol=%d", leftVol);
#ifdef DREAMNEXTGEN
	/* HW Master applies to all paths going through default→softvol→dmix. */
	if (ensureMixer() && mainVolume)
	{
		da_set_master(mainVolume, muted ? 0 : leftVol,
		              alsa_has_db, alsa_min_db, alsa_max_db);
		if (snd_mixer_selem_has_playback_switch(mainVolume))
			snd_mixer_selem_set_playback_switch_all(mainVolume, muted ? 0 : 1);
	}
	if (s_volume_change_cb)
		s_volume_change_cb(muted ? 0 : leftVol);
#else
	if (mainVolume)
		snd_mixer_selem_set_playback_volume_all(mainVolume, muted ? 0 : leftVol);
#endif // DREAMNEXTGEN
#else
	/* convert to -1dB steps */

	int minVol = 63;
	left = minVol - leftVol * minVol / 100;
	right = minVol - rightVol * minVol / 100;
	/* now range is 63..0, where 0 is loudest */

	audio_mixer_t mixer;

	mixer.volume_left = left;
	mixer.volume_right = right;

	eDebug("[eDVBVolumecontrol] Set volume raw: L=%d R=%d, -1db: L=%d R=%d.", leftVol, rightVol, left, right);

	int fd = openMixer();
	if (fd >= 0)
	{
#ifdef DVB_API_VERSION
		if (ioctl(fd, AUDIO_SET_MIXER, &mixer) < 0)
		{
			eDebug("[eDVBVolumecontrol] Error: Set volume failed!  (%m)");
		}
		// Force mute if vol = 0 because some boxes will not be complete silent.
		if (leftVol == 0)
		{
			mute_zero = true;
			ioctl(fd, AUDIO_SET_MUTE, true);
		}
		else if (mute_zero)
		{
			mute_zero = false;
			if(!muted)
				ioctl(fd, AUDIO_SET_MUTE, false);
		}
#endif
		closeMixer(fd);
	}
	else
	{
		eTrace("[eDVBVolumecontrol] Error: Unable to open mixer!  (%m)");
		// Workaround because the mixer is opened exclusive in the driver
		CFile::writeInt("/proc/stb/avs/0/volume", left); /* in -1dB */

		// Force mute if vol = 0 because some boxes will not be complete silent.
		if (leftVol == 0)
		{
			mute_zero = true;
			CFile::writeInt("/proc/stb/audio/j1_mute", 1);
		}
		else if (mute_zero)
		{
			mute_zero = false;
			if(!muted)
				CFile::writeInt("/proc/stb/audio/j1_mute", 0);
		}
	}
#endif
	return leftVol;
}

/**
 * @brief Mutes the volume for the DVB (Digital Video Broadcasting) system.
 *
 * This function mutes the volume by setting the playback volume to zero if ALSA (Advanced Linux Sound Architecture) 
 * is available. If ALSA is not available, it uses the DVB API to mute the audio. Additionally, it writes to a 
 * specific file to ensure the mixer is muted due to exclusive access in the driver.
 *
 * @note The function sets the `muted` member variable to true to indicate that the volume is muted.
 */
void eDVBVolumecontrol::volumeMute()
{
#ifdef HAVE_ALSA
	eDebug("[eDVBVolumecontrol] Set volume ALSA Mute.");
#ifdef DREAMNEXTGEN
	muted = true;
	if (ensureMixer() && mainVolume)
	{
		da_set_master(mainVolume, 0,
		              alsa_has_db, alsa_min_db, alsa_max_db);
		if (snd_mixer_selem_has_playback_switch(mainVolume))
			snd_mixer_selem_set_playback_switch_all(mainVolume, 0);
	}
	if (s_volume_change_cb)
		s_volume_change_cb(0);
#else
	if (mainVolume)
		snd_mixer_selem_set_playback_volume_all(mainVolume, 0);
	muted = true;
#endif
#else
	int fd = openMixer();
	if (fd >= 0)
	{
#ifdef DVB_API_VERSION
		ioctl(fd, AUDIO_SET_MUTE, true);
#endif
		closeMixer(fd);
	}
	muted = true;

	// Workaround because the mixer is opened exclusive in the driver
	CFile::writeInt("/proc/stb/audio/j1_mute", 1);
#endif
}

/**
 * @brief Unmutes the volume control.
 *
 * This function unmutes the volume control by setting the appropriate
 * volume levels and flags. It handles both ALSA and non-ALSA systems.
 *
 * For ALSA systems, it sets the playback volume to the stored left volume
 * level and updates the muted flag.
 *
 * For non-ALSA systems, it opens the mixer device, sends an ioctl command
 * to unmute the audio, and closes the mixer device. Additionally, it writes
 * to a specific file to handle a workaround for exclusive mixer access in
 * the driver.
 *
 * @note This function modifies the `muted` member variable.
 */
void eDVBVolumecontrol::volumeUnMute()
{
#ifdef HAVE_ALSA
	eDebug("[eDVBVolumecontrol] Set volume ALSA unMute to L=%d.", leftVol);
#ifdef DREAMNEXTGEN
	muted = false;
	if (ensureMixer() && mainVolume)
	{
		da_set_master(mainVolume, leftVol,
		              alsa_has_db, alsa_min_db, alsa_max_db);
		if (snd_mixer_selem_has_playback_switch(mainVolume))
			snd_mixer_selem_set_playback_switch_all(mainVolume, 1);
	}
	if (s_volume_change_cb)
		s_volume_change_cb(leftVol);
#else
	if (mainVolume)
		snd_mixer_selem_set_playback_volume_all(mainVolume, leftVol);
	muted = false;
#endif
#else
	int fd = openMixer();
	if (fd >= 0)
	{
#ifdef DVB_API_VERSION
		ioctl(fd, AUDIO_SET_MUTE, false);
#endif
		closeMixer(fd);
	}
	muted = false;

	// Workaround because the mixer is opened exclusive in the driver
	CFile::writeInt("/proc/stb/audio/j1_mute", 0);
#endif
}

/**
 * @brief Toggles the mute state of the volume.
 *
 * This function checks the current mute state of the volume. If the volume is
 * currently muted, it will unmute the volume. If the volume is not muted, it
 * will mute the volume.
 *
 * @return The new mute state after toggling.
 */
bool eDVBVolumecontrol::volumeToggleMute()
{
	if (isMuted())
		volumeUnMute();
	else
		volumeMute();
	return muted;
}

/**
 * @brief Sets the volume offset within the range of -100 to 100.
 *
 * This function adjusts the volume offset to ensure it is within the
 * acceptable range of -100 to 100. It then calculates the new volume
 * based on the base volume and the provided offset, sets the volume,
 * and updates the internal volume offset state.
 *
 * @param offset The desired volume offset, which will be clamped
 *               between -100 and 100 if it falls outside this range.
 * @return The clamped volume offset.
 */
int eDVBVolumecontrol::setVolumeOffset(int offset)
{
	if (offset < -100)
		offset = -100;
	else if (offset > 100)
		offset = 100;

	int newVol = checkVolume(m_BaseVolume + offset);
	setVolume(newVol, newVol);
	m_VolumeOffset = offset;
	return offset;
}
