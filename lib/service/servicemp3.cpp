/*
Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License

Copyright (c) 2025 jbleyel and others

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:
1. Non-Commercial Use: You may not use the Software or any derivative works
   for commercial purposes without obtaining explicit permission from the
   copyright holder.
2. Share Alike: If you distribute or publicly perform the Software or any
   derivative works, you must do so under the same license terms, and you
   must make the source code of any derivative works available to the
   public.
3. Attribution: You must give appropriate credit to the original author(s)
   of the Software by including a prominent notice in your derivative works.
THE SOFTWARE IS PROVIDED "AS IS," WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE, AND NONINFRINGEMENT. IN NO EVENT SHALL
THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES, OR
OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT, OR OTHERWISE,
ARISING FROM, OUT OF, OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
OTHER DEALINGS IN THE SOFTWARE.

For more details about the CC BY-NC-SA 4.0 License, please visit:
https://creativecommons.org/licenses/by-nc-sa/4.0/
*/


/* note: this requires gstreamer 0.10.x and a big list of plugins. */
/* it's currently hardcoded to use a big-endian alsasink as sink. */
#include <inttypes.h>
#include <lib/base/ebase.h>
#include <lib/base/eerror.h>
#include <lib/base/esettings.h>
#include <lib/base/esimpleconfig.h>
#include <lib/base/estring.h>
#include <lib/base/init.h>
#include <lib/base/init_num.h>
#include <lib/base/nconfig.h>
#include <lib/base/object.h>
#include <lib/components/file_eraser.h>
#include <lib/dvb/db.h>
#include <lib/dvb/decoder.h>
#include <lib/dvb/epgcache.h>
#include <lib/dvb/subtitle.h>
#include <lib/gdi/gpixmap.h>
#include <lib/gui/esubtitle.h>
#include <lib/service/service.h>
#include <lib/service/servicemp3.h>
#include <lib/service/servicemp3record.h>

#include <lib/base/cfile.h>

#include <cstdint>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

#include <gst/gst.h>
#include <gst/pbutils/missing-plugins.h>
#include <sys/stat.h>

#include <sys/time.h>

#define HTTP_TIMEOUT 60

/*
 * UNUSED variable from service reference is now used as buffer flag for gstreamer
 * REFTYPE:FLAGS:STYPE:SID:TSID:ONID:NS:PARENT_SID:PARENT_TSID:UNUSED
 *   D  D X X X X X X X X
 * 4097:0:1:0:0:0:0:0:0:0:URL:NAME (no buffering)
 * 4097:0:1:0:0:0:0:0:0:1:URL:NAME (buffering enabled)
 * 4097:0:1:0:0:0:0:0:0:3:URL:NAME (progressive download and buffering enabled)
 *
 * Progressive download requires buffering enabled, so it's mandatory to use flag 3 not 2
 */
typedef enum { BUFFERING_ENABLED = 0x00000001, PROGRESSIVE_DOWNLOAD = 0x00000002 } eServiceMP3Flags;

/*
 * GstPlayFlags flags from playbin2. It is the policy of GStreamer to
 * not publicly expose element-specific enums. That's why this
 * GstPlayFlags enum has been copied here.
 */
typedef enum {
	GST_PLAY_FLAG_VIDEO = (1 << 0),
	GST_PLAY_FLAG_AUDIO = (1 << 1),
	GST_PLAY_FLAG_TEXT = (1 << 2),
	GST_PLAY_FLAG_VIS = (1 << 3),
	GST_PLAY_FLAG_SOFT_VOLUME = (1 << 4),
	GST_PLAY_FLAG_NATIVE_AUDIO = (1 << 5),
	GST_PLAY_FLAG_NATIVE_VIDEO = (1 << 6),
	GST_PLAY_FLAG_DOWNLOAD = (1 << 7),
	GST_PLAY_FLAG_BUFFERING = (1 << 8),
	GST_PLAY_FLAG_DEINTERLACE = (1 << 9),
	GST_PLAY_FLAG_SOFT_COLORBALANCE = (1 << 10),
	GST_PLAY_FLAG_FORCE_FILTERS = (1 << 11),
} GstPlayFlags;

/* static declarations */
static bool first_play_eServicemp3 = false;
static GstElement *dvb_audiosink, *dvb_videosink, *dvb_subsink;
static bool dvb_audiosink_ok, dvb_videosink_ok, dvb_subsink_ok;

/*static functions */

/* Handy asyncrone timers for developpers */
/* It could be used for a hack to set somewhere a timeout which does not interupt or blocks signals */
static void gst_sleepms(uint32_t msec) {
	// does not interfere with signals like sleep and usleep do
	struct timespec req_ts = {};
	req_ts.tv_sec = msec / 1000;
	req_ts.tv_nsec = (msec % 1000) * 1000000L;
	int32_t olderrno = errno; // Some OS seem to set errno to ETIMEDOUT when sleeping
	while (1) {
		/* Sleep for the time specified in req_ts. If interrupted by a
		signal, place the remaining time left to sleep back into req_ts. */
		int rval = nanosleep(&req_ts, &req_ts);
		if (rval == 0)
			break; // Completed the entire sleep time; all done.
		else if (errno == EINTR)
			continue; // Interrupted by a signal. Try again.
		else
			break; // Some other error; bail out.
	}
	errno = olderrno;
}

/**
 * @brief Retrieves the current system time in milliseconds.
 *
 * This function obtains the current time using gettimeofday and returns
 * the number of milliseconds elapsed since the Unix epoch (January 1, 1970).
 *
 * @return int64_t The current time in milliseconds.
 */
static int64_t getCurrentTimeMs() {
	struct timeval tv;
	gettimeofday(&tv, 0);
	return (int64_t)tv.tv_sec * 1000 + tv.tv_usec / 1000;
}

/**
 * @struct audioMeta
 * @brief Represents metadata information for an audio stream.
 *
 * This structure holds information about an audio track, including its index,
 * language code, and title. It is typically used to describe audio streams
 * in multimedia applications.
 *
 * @var audioMeta::index
 *   The index of the audio stream (e.g., track number).
 * @var audioMeta::lang
 *   The language code of the audio stream (e.g., "eng" for English).
 * @var audioMeta::title
 *   The title or description of the audio stream.
 */
struct audioMeta {
	int index;
	std::string lang;
	std::string title;
};

/**
 * @brief Parses HLS audio metadata from a file.
 *
 * This function reads a file containing audio track metadata in a simple key-value format,
 * where each track is separated by a line containing "---". Each track's metadata may include
 * fields such as "index", "lang", and "title". The function constructs a vector of audioMeta
 * objects, each representing a parsed audio track.
 *
 * @param filename The path to the metadata file to parse.
 * @return std::vector<audioMeta> A vector containing the parsed audioMeta objects.
 *
 * The expected file format is:
 * @code
 * index=0
 * lang=eng
 * title=English
 * ---
 * index=1
 * lang=deu
 * title=German
 * ---
 * @endcode
 *
 * @note If the file cannot be opened or is empty, an empty vector is returned.
 */
std::vector<audioMeta> parse_hls_audio_meta(const std::string& filename) {
	std::ifstream file(filename);
	std::vector<audioMeta> tracks;
	std::string line;
	audioMeta current;

	if (!file.good())
		return tracks;

	while (std::getline(file, line)) {
		if (line == "---") {
			tracks.push_back(current);
			current = audioMeta(); // reset
		} else {
			size_t eq_pos = line.find('=');
			if (eq_pos != std::string::npos) {
				std::string key = line.substr(0, eq_pos);
				std::string value = line.substr(eq_pos + 1);
				if (key == "index")
					current.index = std::stoi(value);
				else if (key == "lang")
					current.lang = value;
				else if (key == "title")
					current.title = value;
			}
		}
	}

	if (!current.title.empty())
		tracks.push_back(current);

	return tracks;
}

/**
 * @struct SubtitleEntry
 * @brief Represents a single subtitle entry with timing and text information.
 *
 * This structure holds the timing information (start and end times in milliseconds),
 * a base timestamp for MPEG-TS to WebVTT conversion, and the subtitle text itself.
 *
 * Members:
 * - start_time_ms:      Start time of the subtitle in milliseconds.
 * - end_time_ms:        End time of the subtitle in milliseconds.
 * - vtt_mpegts_base:    Base timestamp used for MPEG-TS to WebVTT conversion.
 * - text:               The subtitle text to be displayed.
 */
struct SubtitleEntry {
	uint64_t start_time_ms;
	uint64_t end_time_ms;
	uint64_t vtt_mpegts_base;
	std::string text;
};

/**
 * @brief Parses a timecode string in the format "HH:MM:SS.mmm" into milliseconds.
 *
 * This function attempts to parse a timecode string (e.g., "01:23:45.678") and convert it
 * into the total number of milliseconds. The expected format is hours, minutes, seconds,
 * and milliseconds separated by colons and a dot.
 *
 * @param[in]  s      The input timecode string to parse.
 * @param[out] ms_out The output variable that will contain the parsed time in milliseconds if parsing succeeds.
 * @return     true if the string was successfully parsed and ms_out is set; false otherwise.
 *
 * @note The function expects the input string to strictly match the "HH:MM:SS.mmm" format.
 */
static bool parse_timecode(const std::string& s, uint64_t& ms_out) {
	unsigned h = 0, m = 0, sec = 0, ms = 0;
	if (sscanf(s.c_str(), "%u:%u:%u.%u", &h, &m, &sec, &ms) == 4) {
		ms_out = ((h * 3600 + m * 60 + sec) * 1000 + ms);
		return true;
	}
	return false;
}

/**
 * @brief Parses WebVTT subtitle data and extracts subtitle entries.
 *
 * This function processes a string containing WebVTT subtitle data, extracting
 * individual subtitle entries with their timing and text. It supports parsing
 * the X-TIMESTAMP-MAP header for MPEGTS to LOCAL time mapping, and handles
 * multi-line subtitle text blocks. The parsed subtitle entries are appended to
 * the provided output vector.
 *
 * @param vtt_data      The input string containing the WebVTT subtitle data.
 * @param subs_out      Output vector to which parsed SubtitleEntry objects will be appended.
 * @return true if at least one subtitle entry was successfully parsed, false otherwise.
 *
 * @note The function expects the existence of a parse_timecode helper function and
 *       a SubtitleEntry struct/class with at least the following members:
 *       - uint64_t start_time_ms
 *       - uint64_t end_time_ms
 *       - uint64_t vtt_mpegts_base
 *       - std::string text
 *
 * @details
 * - Ignores empty lines and lines containing only numbers (cue identifiers).
 * - Handles carriage return at the end of lines.
 * - Parses and applies X-TIMESTAMP-MAP if present, but the adjustment is currently commented out.
 * - Supports multi-line subtitle text.
 */
bool parseWebVTT(const std::string& vtt_data, std::vector<SubtitleEntry>& subs_out) {
	std::istringstream stream(vtt_data);
	std::string line;

	std::string current_text;
	uint64_t start_ms = 0, end_ms = 0, vtt_mpegts_base = 0, local_offset_ms = 0;
	bool expecting_text = false;

	while (std::getline(stream, line)) {
		if (!line.empty() && line.back() == '\r')
			line.pop_back();
		if (line.empty())
			continue;

		if (line.rfind("X-TIMESTAMP-MAP=", 0) == 0) {
			size_t mpegts_pos = line.find("MPEGTS:");
			size_t local_pos = line.find("LOCAL:");

			if (mpegts_pos != std::string::npos && local_pos != std::string::npos) {
				mpegts_pos += 7;
				local_pos += 6;

				size_t comma_pos = line.find(',', mpegts_pos);
				std::string mpegts_str = line.substr(mpegts_pos, comma_pos - mpegts_pos);
				std::string local_str = line.substr(local_pos);

				vtt_mpegts_base = std::stoull(mpegts_str);
				if (vtt_mpegts_base < 1000000) // Ignore less than 1000000
					vtt_mpegts_base = 0;
				parse_timecode(local_str, local_offset_ms);
			}
			continue;
		}

		if (line.find("-->") != std::string::npos) {
			if (!current_text.empty()) {
				SubtitleEntry entry;
				entry.start_time_ms = start_ms;
				entry.end_time_ms = end_ms;
				entry.vtt_mpegts_base = vtt_mpegts_base;
				entry.text = current_text;
				subs_out.push_back(entry);
				current_text.clear();
			}

			size_t arrow = line.find("-->");
			std::string start_str = line.substr(0, arrow);
			std::string end_str = line.substr(arrow + 3);
			if (!parse_timecode(start_str, start_ms))
				continue;
			if (!parse_timecode(end_str, end_ms))
				continue;

			// Apply timestamp mapping adjustment
			// ignore for now
			/*
			if (vtt_mpegts_base > 0)
			{
				const uint64_t local_mpegts_ms = vtt_mpegts_base / 90; // MPEGTS-Ticks (90 kHz) → ms
				const int64_t delta = static_cast<int64_t>(local_mpegts_ms) - static_cast<int64_t>(local_offset_ms);

				start_ms += delta;
				end_ms += delta;
			}
			*/
			expecting_text = true;
			continue;
		}

		if (!expecting_text || line.find_first_not_of("0123456789") == std::string::npos)
			continue;

		if (expecting_text) {
			if (!current_text.empty())
				current_text += "\n";
			current_text += line;
		}
	}

	if (!current_text.empty()) {
		SubtitleEntry entry;
		entry.start_time_ms = start_ms;
		entry.end_time_ms = end_ms;
		entry.vtt_mpegts_base = vtt_mpegts_base;
		entry.text = current_text;
		subs_out.push_back(entry);
	}

	return !subs_out.empty();
}

// eServiceFactoryMP3

/*
 * gstreamer suffers from a bug causing sparse streams to loose sync, after pause/resume / skip
 * see: https://bugzilla.gnome.org/show_bug.cgi?id=619434
 * As a workaround, we run the subsink in sync=false mode
 */
#undef GSTREAMER_SUBTITLE_SYNC_MODE_BUG
/**/

eServiceFactoryMP3::eServiceFactoryMP3() {
	ePtr<eServiceCenter> sc;

	eServiceCenter::getPrivInstance(sc);
	if (sc) {
		std::list<std::string> extensions;
		extensions.push_back("dts");
		extensions.push_back("mp2");
		extensions.push_back("mp3");
		extensions.push_back("ogg");
		extensions.push_back("ogm");
		extensions.push_back("ogv");
		extensions.push_back("mpg");
		extensions.push_back("vob");
		extensions.push_back("wav");
		extensions.push_back("wave");
		extensions.push_back("m4v");
		extensions.push_back("mkv");
		extensions.push_back("avi");
		extensions.push_back("divx");
		extensions.push_back("dat");
		extensions.push_back("flac");
		extensions.push_back("flv");
		extensions.push_back("mp4");
		extensions.push_back("mov");
		extensions.push_back("m4a");
		extensions.push_back("3gp");
		extensions.push_back("3g2");
		extensions.push_back("asf");
		extensions.push_back("wmv");
		extensions.push_back("wma");
		extensions.push_back("webm");
		extensions.push_back("m3u8");
		extensions.push_back("stream");
		sc->addServiceFactory(eServiceFactoryMP3::id, this, extensions);
	}

	m_service_info = new eStaticServiceMP3Info();
}

eServiceFactoryMP3::~eServiceFactoryMP3() {
	ePtr<eServiceCenter> sc;

	eServiceCenter::getPrivInstance(sc);
	if (sc)
		sc->removeServiceFactory(eServiceFactoryMP3::id);
}

DEFINE_REF(eServiceFactoryMP3)

/**
 * @brief Initializes and creates GStreamer sink elements for audio, video, and subtitles.
 *
 * This static function attempts to create and initialize the following GStreamer sink elements:
 * - Audio sink ("dvbaudiosink")
 * - Video sink ("dvbvideosink")
 * - Subtitle sink ("subsink")
 *
 * For each sink, it tries to create the element using gst_element_factory_make. If creation is successful,
 * the element is referenced and a debug message is logged. If creation fails (e.g., the required plugin is missing),
 * an error message is logged. The function also sets corresponding boolean flags to indicate the success or failure
 * of each sink's creation.
 *
 * Global variables affected:
 * - dvb_audiosink, dvb_videosink, dvb_subsink: Pointers to the created GStreamer elements.
 * - dvb_audiosink_ok, dvb_videosink_ok, dvb_subsink_ok: Flags indicating successful creation of each sink.
 *
 * No parameters or return value.
 */
static void create_gstreamer_sinks() {
	dvb_subsink = dvb_audiosink = dvb_videosink = NULL;
	dvb_subsink_ok = dvb_audiosink_ok = dvb_videosink_ok = false;
	dvb_audiosink = gst_element_factory_make("dvbaudiosink", NULL);
	if (dvb_audiosink) {
		gst_object_ref_sink(dvb_audiosink);
		eDebug("[eServiceFactoryMP3] **** dvb_audiosink created ***");
		dvb_audiosink_ok = true;
	} else
		eDebug("[eServiceFactoryMP3] **** audio_sink NOT created missing plugin dvbaudiosink ****");
	dvb_videosink = gst_element_factory_make("dvbvideosink", NULL);
	if (dvb_videosink) {
		gst_object_ref_sink(dvb_videosink);
		eDebug("[eServiceFactoryMP3] **** dvb_videosink created ***");
		dvb_videosink_ok = true;
	} else
		eDebug("[eServiceFactoryMP3] **** dvb_videosink NOT created missing plugin dvbvideosink ****");
	dvb_subsink = gst_element_factory_make("subsink", NULL);
	if (dvb_subsink) {
		gst_object_ref_sink(dvb_subsink);
		eDebug("[eServiceFactoryMP3] **** dvb_subsink created ***");
		dvb_subsink_ok = true;
	} else
		eDebug("[eServiceFactoryMP3] **** dvb_subsink NOT created missing plugin subsink ****");
}

/**
 * @brief Starts playback of a media service referenced by the given service reference.
 *
 * This method checks and manages resources required for playback. On the very first play,
 * it initializes GStreamer sinks and sets up internal counters. For subsequent plays,
 * it increments the service counter. It then creates a new MP3 service instance and assigns
 * it to the provided pointer.
 *
 * @param ref The service reference identifying the media to play.
 * @param ptr Reference to a smart pointer where the newly created playable service will be stored.
 * @return RESULT Returns 0 on success, or an error code otherwise.
 *
 * @note This function manages the initialization of GStreamer sinks only on the first play.
 * @note The total number of services played is tracked and logged for debugging purposes.
 */
RESULT eServiceFactoryMP3::play(const eServiceReference& ref, ePtr<iPlayableService>& ptr) {
	// check resources...
	// creating gstreamer sinks for the very fisrt media
	if (first_play_eServicemp3)
		m_eServicemp3_counter++;
	else {
		first_play_eServicemp3 = true;
		m_eServicemp3_counter = 1;
		create_gstreamer_sinks();
	}
	eDebug("[eServiceFactoryMP3] ****new play service total services played is %d****", m_eServicemp3_counter);
	ptr = new eServiceMP3(ref);
	return 0;
}

/**
 * @brief Attempts to create a recordable MP3 service from the given service reference.
 *
 * This function checks if the provided service reference contains a path with a protocol (i.e., "://").
 * If so, it creates a new eServiceMP3Record instance and assigns it to the output pointer.
 * Otherwise, it sets the pointer to nullptr and returns an error code.
 *
 * @param ref The service reference to attempt to record from.
 * @param ptr Output pointer that will be set to the created recordable service, or nullptr on failure.
 * @return RESULT 0 on success, -1 on failure.
 */
RESULT eServiceFactoryMP3::record(const eServiceReference& ref, ePtr<iRecordableService>& ptr) {
	if (ref.path.find("://") != std::string::npos) {
		ptr = new eServiceMP3Record((eServiceReference&)ref);
		return 0;
	}
	ptr = nullptr;
	return -1;
}

/**
 * @brief Lists available MP3 services for a given service reference.
 *
 * This method attempts to populate the provided pointer with a list of
 * MP3 services corresponding to the specified service reference.
 *
 * @param ref The service reference for which to list available MP3 services.
 * @param ptr Reference to a pointer that will be set to the list of services if available,
 *            or set to nullptr if no services are found.
 * @return RESULT Returns 0 on success, or -1 if no services are available or an error occurs.
 */
RESULT eServiceFactoryMP3::list(const eServiceReference&, ePtr<iListableService>& ptr) {
	ptr = nullptr;
	return -1;
}

/**
 * @brief Provides static service information for a given service reference.
 *
 * This method retrieves static service information for the specified service reference
 * and assigns it to the provided pointer. The information is typically used to display
 * metadata about the service without opening it.
 *
 * @param ref The service reference for which to retrieve information.
 * @param ptr Reference to a pointer that will be set to the static service information.
 * @return RESULT Returns 0 on success, or an error code if the operation fails.
 */
RESULT eServiceFactoryMP3::info(const eServiceReference& ref, ePtr<iStaticServiceInformation>& ptr) {
	ptr = m_service_info;
	return 0;
}

/**
 * @brief Provides offline operations for a given service reference.
 *
 * This method creates an instance of eMP3ServiceOfflineOperations for the specified service reference
 * and assigns it to the provided pointer. This allows for operations such as deleting files or reindexing.
 *
 * @param ref The service reference for which to perform offline operations.
 * @param ptr Reference to a pointer that will be set to the offline operations instance.
 * @return RESULT Returns 0 on success, or an error code if the operation fails.
 */
class eMP3ServiceOfflineOperations : public iServiceOfflineOperations {
	DECLARE_REF(eMP3ServiceOfflineOperations);
	eServiceReference m_ref;

public:
	eMP3ServiceOfflineOperations(const eServiceReference& ref);

	RESULT deleteFromDisk(int simulate);
	RESULT getListOfFilenames(std::list<std::string>&);
	RESULT reindex();
};

DEFINE_REF(eMP3ServiceOfflineOperations);

eMP3ServiceOfflineOperations::eMP3ServiceOfflineOperations(const eServiceReference& ref)
	: m_ref((const eServiceReference&)ref) {}

/**
 * @brief Deletes the files associated with the service reference from disk.
 *
 * This method removes the main file, its metadata, and any associated cut files from disk.
 * If the simulate parameter is set to 0, it performs the deletion; otherwise, it only simulates it.
 *
 * @param simulate If set to 0, actual deletion is performed; if non-zero, only simulation occurs.
 * @return RESULT Returns 0 on success, or -1 if an error occurs.
 */
RESULT eMP3ServiceOfflineOperations::deleteFromDisk(int simulate) {
	if (!simulate) {
		std::list<std::string> res;
		if (getListOfFilenames(res))
			return -1;

		eBackgroundFileEraser* eraser = eBackgroundFileEraser::getInstance();
		if (!eraser)
			eDebug("[eMP3ServiceOfflineOperations] FATAL !! can't get background file eraser");

		for (std::list<std::string>::iterator i(res.begin()); i != res.end(); ++i) {
			// eDebug("[eMP3ServiceOfflineOperations] Removing %s...", i->c_str());
			if (eraser)
				eraser->erase(i->c_str());
			else
				::unlink(i->c_str());
		}
	}
	return 0;
}

/**
 * @brief Retrieves a list of filenames associated with the service reference.
 *
 * This method populates the provided list with the main file, its metadata file,
 * cut files, and EIT files (if applicable). The filenames are derived from the
 * service reference's path.
 *
 * @param res Output list that will be filled with the filenames.
 * @return RESULT Returns 0 on success, or an error code if the operation fails.
 */
RESULT eMP3ServiceOfflineOperations::getListOfFilenames(std::list<std::string>& res) {
	res.clear();
	res.push_back(m_ref.path);
	res.push_back(m_ref.path + ".meta");
	res.push_back(m_ref.path + ".cuts");
	std::string filename = m_ref.path;
	size_t pos;
	if ((pos = filename.rfind('.')) != std::string::npos) {
		filename.erase(pos + 1);
		res.push_back(filename + ".eit");
	}
	return 0;
}

RESULT eMP3ServiceOfflineOperations::reindex() {
	return -1;
}

RESULT eServiceFactoryMP3::offlineOperations(const eServiceReference& ref, ePtr<iServiceOfflineOperations>& ptr) {
	ptr = new eMP3ServiceOfflineOperations(ref);
	return 0;
}

// eStaticServiceMP3Info

// eStaticServiceMP3Info is seperated from eServiceMP3 to give information
// about unopened files.

// probably eServiceMP3 should use this class as well, and eStaticServiceMP3Info
// should have a database backend where ID3-files etc. are cached.
// this would allow listing the mp3 database based on certain filters.

DEFINE_REF(eStaticServiceMP3Info)

eStaticServiceMP3Info::eStaticServiceMP3Info() {}

/**
 * @brief Retrieves the name of the service referenced by the given service reference.
 *
 * This method attempts to extract the name from the service reference. If the name is already set,
 * it uses that; otherwise, it tries to parse metadata from a stream file or extracts the last part
 * of the path as the name.
 *
 * @param ref The service reference for which to retrieve the name.
 * @param name Output string that will be set to the service name.
 * @return RESULT Returns 0 on success, or an error code if the operation fails.
 */
RESULT eStaticServiceMP3Info::getName(const eServiceReference& ref, std::string& name) {
	if (ref.name.length())
		name = ref.name;
	else {
		if (endsWith(ref.path, ".stream") && !m_parser.parseMeta(ref.path)) {
			name = m_parser.m_name;
			return 0;
		}
		size_t last = ref.path.rfind('/');
		if (last != std::string::npos)
			name = ref.path.substr(last + 1);
		else
			name = ref.path;
	}
	return 0;
}

int eStaticServiceMP3Info::getLength(const eServiceReference& ref) {
	return -1;
}

/**
 * @brief Retrieves specific information about the service referenced by the given service reference.
 *
 * This method checks the requested information type (w) and retrieves the corresponding data
 * from the file system, such as creation time or file size. If the requested information is not
 * available, it returns a predefined constant indicating that the information is not applicable.
 *
 * @param ref The service reference for which to retrieve information.
 * @param w The type of information requested (e.g., creation time, file size).
 * @return int Returns the requested information or iServiceInformation::resNA if not available.
 */
int eStaticServiceMP3Info::getInfo(const eServiceReference& ref, int w) {
	switch (w) {
		case iServiceInformation::sTimeCreate: {
			struct stat s = {};
			if (stat(ref.path.c_str(), &s) == 0) {
				return s.st_mtime;
			}
		} break;
		case iServiceInformation::sFileSize: {
			struct stat s = {};
			if (stat(ref.path.c_str(), &s) == 0) {
				return s.st_size;
			}
		} break;
	}
	return iServiceInformation::resNA;
}

/**
 * @brief Retrieves the file size of the service referenced by the given service reference.
 *
 * This method checks the file system for the size of the file associated with the service reference.
 * If the file exists, it returns its size; otherwise, it returns 0.
 *
 * @param ref The service reference for which to retrieve the file size.
 * @return long long Returns the file size in bytes, or 0 if the file does not exist.
 */
long long eStaticServiceMP3Info::getFileSize(const eServiceReference& ref) {
	struct stat s = {};
	if (stat(ref.path.c_str(), &s) == 0) {
		return s.st_size;
	}
	return 0;
}

/**
 * @brief Retrieves the event associated with the service reference at a specific start time.
 *
 * This method attempts to find an event for the given service reference at the specified start time.
 * If the service reference contains a protocol (e.g., "://"), it looks up the event in the EPG cache.
 * If not, it tries to read an EIT file corresponding to the service reference's path.
 *
 * @param ref The service reference for which to retrieve the event.
 * @param evt Output pointer that will be set to the found event, or nullptr if not found.
 * @param start_time The start time for which to look up the event.
 * @return RESULT Returns 0 on success, or -1 if no event is found or an error occurs.
 */
RESULT eStaticServiceMP3Info::getEvent(const eServiceReference& ref, ePtr<eServiceEvent>& evt, time_t start_time) {
	if (ref.path.find("://") != std::string::npos) {
		eServiceReference equivalentref(ref);
		equivalentref.type = eServiceFactoryMP3::id;
		equivalentref.path.clear();
		return eEPGCache::getInstance()->lookupEventTime(equivalentref, start_time, evt);
	} else // try to read .eit file
	{
		size_t pos;
		ePtr<eServiceEvent> event = new eServiceEvent;
		std::string filename = ref.path;
		if ((pos = filename.rfind('.')) != std::string::npos) {
			filename.erase(pos + 1);
			filename += "eit";
			if (!event->parseFrom(filename, 0)) {
				evt = event;
				return 0;
			}
		}
	}
	evt = 0;
	return -1;
}

DEFINE_REF(eStreamBufferInfo)

eStreamBufferInfo::eStreamBufferInfo(int percentage, int inputrate, int outputrate, int space, int size)
	: bufferPercentage(percentage), inputRate(inputrate), outputRate(outputrate), bufferSpace(space), bufferSize(size) {
}

int eStreamBufferInfo::getBufferPercentage() const {
	return bufferPercentage;
}

int eStreamBufferInfo::getAverageInputRate() const {
	return inputRate;
}

int eStreamBufferInfo::getAverageOutputRate() const {
	return outputRate;
}

int eStreamBufferInfo::getBufferSpace() const {
	return bufferSpace;
}

int eStreamBufferInfo::getBufferSize() const {
	return bufferSize;
}

DEFINE_REF(eServiceMP3InfoContainer);

eServiceMP3InfoContainer::eServiceMP3InfoContainer()
	: doubleValue(0.0), bufferValue(NULL), bufferData(NULL), bufferSize(0) {}

eServiceMP3InfoContainer::~eServiceMP3InfoContainer() {
	if (bufferValue) {
		gst_buffer_unmap(bufferValue, &map);
		gst_buffer_unref(bufferValue);
		bufferValue = NULL;
		bufferData = NULL;
		bufferSize = 0;
	}
}

double eServiceMP3InfoContainer::getDouble(unsigned int index) const {
	return doubleValue;
}

unsigned char* eServiceMP3InfoContainer::getBuffer(unsigned int& size) const {
	size = bufferSize;
	return bufferData;
}

void eServiceMP3InfoContainer::setDouble(double value) {
	doubleValue = value;
}

/**
 * @brief Sets the buffer for the container and maps it for reading.
 *
 * This method takes a GstBuffer pointer, references it, and maps it for reading.
 * It stores the mapped data and size in the container for later access.
 *
 * @param buffer The GstBuffer to set in the container.
 */
void eServiceMP3InfoContainer::setBuffer(GstBuffer* buffer) {
	bufferValue = buffer;
	gst_buffer_ref(bufferValue);
	gst_buffer_map(bufferValue, &map, GST_MAP_READ);
	bufferData = map.data;
	bufferSize = map.size;
}

// eServiceMP3
int eServiceMP3::ac3_delay = 0, eServiceMP3::pcm_delay = 0;

/**
 * @brief Constructs an eServiceMP3 object with the given service reference.
 *
 * This constructor initializes various timers, subtitle parsers, and other member variables
 * required for handling MP3 services. It also sets up connections for handling subtitle synchronization,
 * DVB subtitle parsing, and other service-related events.
 *
 * @param ref The service reference for the MP3 service to be created.
 */
eServiceMP3::eServiceMP3(eServiceReference ref)
	: m_nownext_timer(eTimer::create(eApp)), m_cuesheet_changed(0), m_cutlist_enabled(1), m_ref(ref),
	  m_pump(eApp, 1, "eServiceMP3") {
	m_subtitle_sync_timer = eTimer::create(eApp);
	m_dvb_subtitle_sync_timer = eTimer::create(eApp);
	m_dvb_subtitle_parser = new eDVBSubtitleParser();
	m_dvb_subtitle_parser->connectNewPage(sigc::mem_fun(*this, &eServiceMP3::newDVBSubtitlePage),
										  m_new_dvb_subtitle_page_connection);
#ifdef PASSTHROUGH_FIX
	m_passthrough_fix_timer = eTimer::create(eApp);
#endif
	m_stream_tags = 0;
	m_currentAudioStream = -1;
	m_currentSubtitleStream = -1;
	m_cachedSubtitleStream = -2; /* report the first subtitle stream to be 'cached'. TODO: use an actual cache. */
	m_subtitle_widget = 0;
	m_currentTrickRatio = 1.0;
	m_buffer_size = 5LL * 1024LL * 1024LL;
	m_ignore_buffering_messages = 0;
	m_is_live = false;
	m_use_prefillbuffer = false;
	m_paused = false;
	m_clear_buffers = true;
	m_initial_start = false;
	m_send_ev_start = true;
	m_first_paused = false;
	m_cuesheet_loaded = false; /* cuesheet CVR */
	m_audiosink_not_running = false;
	m_use_chapter_entries = false; /* TOC chapter support CVR */
	m_play_position_timer = eTimer::create(eApp);
	CONNECT(m_play_position_timer->timeout, eServiceMP3::playPositionTiming);
	m_last_seek_count = -10;
	m_seeking_or_paused = false;
	m_to_paused = false;
	m_last_seek_pos = 0;
	m_media_lenght = 0;
	m_useragent = "HbbTV/1.1.1 (+PVR+RTSP+DL; Sonic; TV44; 1.32.455; 2.002) Bee/3.5";
	m_extra_headers = "";
	m_download_buffer_path = "";
	m_prev_decoder_time = -1;
	m_decoder_time_valid_state = 0;
	m_initial_vtt_mpegts = 0; // Initialize base MPEGTS for WebVTT sync
	m_vtt_live_base_time = -1;
	m_vtt_live = false;
	m_errorInfo.missing_codec = "";
	m_decoder = NULL;
	m_subs_to_pull_handler_id = m_notify_source_handler_id = m_notify_element_added_handler_id = 0;

	std::string sref = ref.toString();
	if (!sref.empty()) {
		sref = replace_all(sref, ",", "_");
		std::vector<ePtr<eDVBService>>& iptv_services = eDVBDB::getInstance()->iptv_services;
		for (std::vector<ePtr<eDVBService>>::iterator it = iptv_services.begin(); it != iptv_services.end(); ++it) {
			// eDebug("[eServiceMP3] iptv_services m_reference_str : %s", (*it)->m_reference_str.c_str());
			if (sref.find((*it)->m_reference_str) != std::string::npos) {
				m_currentAudioStream = (*it)->getCacheEntry(eDVBService::cMPEGAPID);
				m_currentSubtitleStream = (*it)->getCacheEntry(eDVBService::cSUBTITLE);
				m_cachedSubtitleStream = m_currentSubtitleStream;
				break;
			}
		}
	}
	CONNECT(m_subtitle_sync_timer->timeout, eServiceMP3::pushSubtitles);
	CONNECT(m_dvb_subtitle_sync_timer->timeout, eServiceMP3::pushDVBSubtitles);
	CONNECT(m_pump.recv_msg, eServiceMP3::gstPoll);
	CONNECT(m_nownext_timer->timeout, eServiceMP3::updateEpgCacheNowNext);
#ifdef PASSTHROUGH_FIX
	CONNECT(m_passthrough_fix_timer->timeout, eServiceMP3::forcePassthrough);
#endif
	m_aspect = m_width = m_height = m_framerate = m_progressive = m_gamma = -1;

	m_state = stIdle;
	m_gstdot = eSimpleConfig::getBool("config.crash.gstdot", false);
	m_coverart = false;
	m_subtitles_paused = false;
	// eDebug("[eServiceMP3] construct!");

	const char* filename;
	std::string filename_str;
	size_t pos = m_ref.path.find('#');
	if (pos != std::string::npos && (m_ref.path.compare(0, 4, "http") == 0 || m_ref.path.compare(0, 4, "rtsp") == 0)) {
		filename_str = m_ref.path.substr(0, pos);
		filename = filename_str.c_str();
		m_extra_headers = m_ref.path.substr(pos + 1);

		pos = m_extra_headers.find("User-Agent=");
		if (pos != std::string::npos) {
			size_t hpos_start = pos + 11;
			size_t hpos_end = m_extra_headers.find('&', hpos_start);
			if (hpos_end != std::string::npos)
				m_useragent = m_extra_headers.substr(hpos_start, hpos_end - hpos_start);
			else
				m_useragent = m_extra_headers.substr(hpos_start);
		}
	} else
		filename = m_ref.path.c_str();

	if (!m_ref.alternativeurl.empty())
		filename = m_ref.alternativeurl.c_str();

	gchar* suburi = NULL;

	m_external_subtitle_path = "";
	m_external_subtitle_language = "";
	m_external_subtitle_extension = "";

	pos = m_ref.path.find("&suburi=");
	if (pos != std::string::npos) {
		filename_str = filename;

		std::string suburi_str = filename_str.substr(pos + 8);
		filename = suburi_str.c_str();
		m_external_subtitle_path = suburi_str;
		suburi = g_strdup_printf("%s", filename);

		filename_str = filename_str.substr(0, pos);
		filename = filename_str.c_str();
	} else {
		if (!m_ref.suburi.empty()) {
			m_external_subtitle_path = m_ref.suburi;
		}
	}

	if (!m_external_subtitle_path.empty()) {
		std::string suburi_str = m_external_subtitle_path;
		pos = suburi_str.find_last_of(".");
		if (pos != std::string::npos) {
			m_external_subtitle_extension = suburi_str.substr(pos + 1);
			suburi_str = suburi_str.substr(0, pos);
		}

		pos = suburi_str.find_last_of(".");
		if (pos != std::string::npos) {
			m_external_subtitle_language = suburi_str.substr(pos + 1);
			if (m_external_subtitle_language.size() > 3)
				m_external_subtitle_language = "";
		}
		eDebug("[eServiceMP3] m_external_subtitle_path: %s m_external_subtitle_extension: %s "
			   "m_external_subtitle_language: %s",
			   m_external_subtitle_path.c_str(), m_external_subtitle_extension.c_str(),
			   m_external_subtitle_language.c_str());
	}

	const char* ext = strrchr(filename, '.');
	if (!ext)
		ext = filename + strlen(filename);

	m_sourceinfo.is_video = FALSE;
	m_sourceinfo.audiotype = atUnknown;
	if ((strcasecmp(ext, ".mpeg") && strcasecmp(ext, ".mpg") && strcasecmp(ext, ".vob") && strcasecmp(ext, ".bin") &&
		 strcasecmp(ext, ".dat")) == 0) {
		m_sourceinfo.containertype = ctMPEGPS;
		m_sourceinfo.is_video = TRUE;
	} else if (strcasecmp(ext, ".ts") == 0) {
		m_sourceinfo.containertype = ctMPEGTS;
		m_sourceinfo.is_video = TRUE;
	} else if (strcasecmp(ext, ".mkv") == 0) {
		m_sourceinfo.containertype = ctMKV;
		m_sourceinfo.is_video = TRUE;
	} else if (strcasecmp(ext, ".ogm") == 0 || strcasecmp(ext, ".ogv") == 0) {
		m_sourceinfo.containertype = ctOGG;
		m_sourceinfo.is_video = TRUE;
	} else if (strcasecmp(ext, ".avi") == 0 || strcasecmp(ext, ".divx") == 0) {
		m_sourceinfo.containertype = ctAVI;
		m_sourceinfo.is_video = TRUE;
	} else if (strcasecmp(ext, ".mp4") == 0 || strcasecmp(ext, ".mov") == 0 || strcasecmp(ext, ".m4v") == 0 ||
			   strcasecmp(ext, ".3gp") == 0 || strcasecmp(ext, ".3g2") == 0) {
		m_sourceinfo.containertype = ctMP4;
		m_sourceinfo.is_video = TRUE;
	} else if (strcasecmp(ext, ".asf") == 0 || strcasecmp(ext, ".wmv") == 0) {
		m_sourceinfo.containertype = ctASF;
		m_sourceinfo.is_video = TRUE;
	} else if (strcasecmp(ext, ".webm") == 0) {
		m_sourceinfo.containertype = ctMKV;
		m_sourceinfo.is_video = TRUE;
	} else if (strcasecmp(ext, ".m4a") == 0) {
		m_sourceinfo.containertype = ctMP4;
		m_sourceinfo.audiotype = atAAC;
	} else if (strcasecmp(ext, ".dra") == 0) {
		m_sourceinfo.containertype = ctDRA;
		m_sourceinfo.audiotype = atDRA;
	} else if (strcasecmp(ext, ".m3u8") == 0)
		m_sourceinfo.is_hls = TRUE;
	else if (strcasecmp(ext, ".mp3") == 0) {
		m_sourceinfo.audiotype = atMP3;
		m_sourceinfo.is_audio = TRUE;
	} else if (strcasecmp(ext, ".wma") == 0) {
		m_sourceinfo.audiotype = atWMA;
		m_sourceinfo.is_audio = TRUE;
	} else if (strcasecmp(ext, ".wav") == 0) {
		m_sourceinfo.audiotype = atPCM;
		m_sourceinfo.is_audio = TRUE;
	} else if (strcasecmp(ext, ".dts") == 0) {
		m_sourceinfo.audiotype = atDTS;
		m_sourceinfo.is_audio = TRUE;
	} else if (strcasecmp(ext, ".flac") == 0) {
		m_sourceinfo.audiotype = atFLAC;
		m_sourceinfo.is_audio = TRUE;
	} else if (strcasecmp(ext, ".cda") == 0)
		m_sourceinfo.containertype = ctCDA;
	if (strcasecmp(ext, ".dat") == 0) {
		m_sourceinfo.containertype = ctVCD;
		m_sourceinfo.is_video = TRUE;
	}
	if (strstr(filename, "://"))
		m_sourceinfo.is_streaming = TRUE;

	gchar* uri;

	if (m_sourceinfo.is_streaming) {
		if (eConfigManager::getConfigBoolValue("config.mediaplayer.useAlternateUserAgent"))
			m_useragent = eConfigManager::getConfigValue("config.mediaplayer.alternateUserAgent");

		uri = g_strdup_printf("%s", filename);

		if (m_ref.getData(7) & BUFFERING_ENABLED) {
			m_use_prefillbuffer = true;
			if (m_ref.getData(7) & PROGRESSIVE_DOWNLOAD) {
				/* progressive download buffering */
				if (::access("/hdd/movie", X_OK) >= 0) {
					/* It looks like /hdd points to a valid mount, so we can store a download buffer on it */
					m_download_buffer_path = "/hdd/gstreamer_XXXXXXXXXX";
				}
			}
		}
	} else if (m_sourceinfo.containertype == ctCDA) {
		int i_track = atoi(filename + (strlen(filename) - 6));
		uri = g_strdup_printf("cdda://%i", i_track);
	} else if (m_sourceinfo.containertype == ctVCD) {
		int ret = -1;
		int fd = open(filename, O_RDONLY);
		if (fd >= 0) {
			char* tmp = new char[128 * 1024];
			ret = read(fd, tmp, 128 * 1024);
			close(fd);
			delete[] tmp;
		}
		if (ret == -1) // this is a "REAL" VCD
			uri = g_strdup_printf("vcd://");
		else
			uri = g_filename_to_uri(filename, NULL, NULL);
	} else
		uri = g_filename_to_uri(filename, NULL, NULL);

	eDebug("[eServiceMP3] playbin uri=%s", uri);
	if (suburi != NULL)
		eDebug("[eServiceMP3] playbin suburi=%s", suburi);
	bool useplaybin3 = eSimpleConfig::getBool("config.misc.usegstplaybin3", false);
	if (useplaybin3)
		m_gst_playbin = gst_element_factory_make("playbin3", "playbin3");
	else
		m_gst_playbin = gst_element_factory_make("playbin", "playbin");
	if (m_gst_playbin) {
		if (dvb_audiosink) {
			if (m_sourceinfo.is_audio) {
				g_object_set(dvb_audiosink, "e2-sync", TRUE, NULL);
				g_object_set(dvb_audiosink, "e2-async", TRUE, NULL);
			} else {
				g_object_set(dvb_audiosink, "e2-sync", FALSE, NULL);
				g_object_set(dvb_audiosink, "e2-async", FALSE, NULL);
			}
			g_object_set(m_gst_playbin, "audio-sink", dvb_audiosink, NULL);
		}
		if (dvb_videosink && !m_sourceinfo.is_audio) {
			g_object_set(dvb_videosink, "e2-sync", FALSE, NULL);
			g_object_set(dvb_videosink, "e2-async", FALSE, NULL);
			g_object_set(m_gst_playbin, "video-sink", dvb_videosink, NULL);
		}

		/*
		 * avoid video conversion, let the dvbmediasink handle that using native video flag
		 * volume control is done by hardware, do not use soft volume flag
		 */
		guint flags = GST_PLAY_FLAG_AUDIO | GST_PLAY_FLAG_VIDEO | GST_PLAY_FLAG_TEXT | GST_PLAY_FLAG_NATIVE_VIDEO;

		if (m_sourceinfo.is_streaming) {
			m_notify_source_handler_id =
				g_signal_connect(m_gst_playbin, "notify::source", G_CALLBACK(playbinNotifySource), this);
			if (m_download_buffer_path != "") {
				/* use progressive download buffering */
				flags |= GST_PLAY_FLAG_DOWNLOAD;
				m_notify_element_added_handler_id =
					g_signal_connect(m_gst_playbin, "element-added", G_CALLBACK(handleElementAdded), this);
				/* limit file size */
				g_object_set(m_gst_playbin, "ring-buffer-max-size", (guint64)(8LL * 1024LL * 1024LL), NULL);
			}
			/*
			 * regardless whether or not we configured a progressive download file, use a buffer as well
			 * (progressive download might not work for all formats)
			 */
			flags |= GST_PLAY_FLAG_BUFFERING;
			/* increase the default 2 second / 2 MB buffer limitations to 10s / 10MB */
			g_object_set(m_gst_playbin, "buffer-duration", (gint64)(5LL * GST_SECOND), NULL);
			g_object_set(m_gst_playbin, "buffer-size", m_buffer_size, NULL);
			if (m_sourceinfo.is_hls)
				g_object_set(m_gst_playbin, "connection-speed", (guint64)(4495000LL), NULL);
		}
		g_object_set(m_gst_playbin, "flags", flags, NULL);
		g_object_set(m_gst_playbin, "uri", uri, NULL);
		if (dvb_subsink) {
			m_subs_to_pull_handler_id =
				g_signal_connect(dvb_subsink, "new-buffer", G_CALLBACK(gstCBsubtitleAvail), this);
			GstCaps* caps = gst_caps_from_string("text/plain; "
												 "text/x-plain; "
												 "text/x-raw; "
												 "text/x-pango-markup; "
												 "subpicture/x-dvd; "
												 "subpicture/x-dvb; "
												 "subpicture/x-pgs; "
												 "text/vtt; "
												 "text/x-webvtt; "
												 "text/x-ssa; " // SubStation Alpha
												 "text/x-ass; " // Advanced SubStation Alpha
												 "application/x-ass; " // Alternative ASS format
												 "application/x-ssa; " // Alternative SSA format
												 "application/x-subtitle-vtt; "
												 "video/x-dvd-subpicture; "
												 "subpicture/x-xsub");
			g_object_set(dvb_subsink, "caps", caps, NULL);
			gst_caps_unref(caps);

			g_object_set(m_gst_playbin, "text-sink", dvb_subsink, NULL);
			g_object_set(m_gst_playbin, "current-text", m_currentSubtitleStream, NULL);
		}
		GstBus* bus = gst_pipeline_get_bus(GST_PIPELINE(m_gst_playbin));
		gst_bus_set_sync_handler(bus, gstBusSyncHandler, this, NULL);
		gst_object_unref(bus);

		if (suburi != NULL)
			g_object_set(m_gst_playbin, "suburi", suburi, NULL);
		else {
			if (m_external_subtitle_path.empty()) {
				char srt_filename[ext - filename + 5];
				strncpy(srt_filename, filename, ext - filename);
				srt_filename[ext - filename] = '\0';
				strcat(srt_filename, ".srt");
				if (::access(srt_filename, R_OK) >= 0) {
					gchar* luri = g_filename_to_uri(srt_filename, NULL, NULL);
					eDebug("[eServiceMP3] subtitle uri: %s", luri);
					g_object_set(m_gst_playbin, "suburi", luri, NULL);
					g_free(luri);
				}

			} else {
				if (::access(m_external_subtitle_path.c_str(), R_OK) >= 0) {
					gchar* luri = g_filename_to_uri(m_external_subtitle_path.c_str(), NULL, NULL);
					eDebug("[eServiceMP3] m_external_subtitle uri: %s", luri);
					g_object_set(m_gst_playbin, "suburi", luri, NULL);
					g_free(luri);
				} else {
					m_external_subtitle_extension = "";
				}
			}
		}

	} else {
		m_event((iPlayableService*)this, evUser + 12);
		m_gst_playbin = NULL;
		m_errorInfo.error_message = "failed to create GStreamer pipeline!\n";
		eDebug("[eServiceMP3] sorry, can't play: %s", m_errorInfo.error_message.c_str());
	}
	g_free(uri);
	if (suburi != NULL)
		g_free(suburi);
}

/**
 * @brief Destructor for eServiceMP3.
 *
 * This destructor cleans up resources, disconnects signals, and stops the service.
 * It ensures that all GStreamer elements are properly released and any active timers
 * are stopped to prevent memory leaks or dangling pointers.
 */
eServiceMP3::~eServiceMP3() {
	// disconnect subtitle callback

	if (dvb_subsink) {
		g_signal_handler_disconnect(dvb_subsink, m_subs_to_pull_handler_id);
		if (m_subtitle_widget) {
			int oldsubs = m_currentSubtitleStream; // remember the last subtitle stream
			disableSubtitles();
			setCacheEntry(false, oldsubs);
		}
	}

	if (m_gst_playbin) {
		if (m_notify_source_handler_id) {
			g_signal_handler_disconnect(m_gst_playbin, m_notify_source_handler_id);
			m_notify_source_handler_id = 0;
		}
		if (m_notify_element_added_handler_id) {
			g_signal_handler_disconnect(m_gst_playbin, m_notify_element_added_handler_id);
			m_notify_element_added_handler_id = 0;
		}
		// disconnect sync handler callback
		GstBus* bus = gst_pipeline_get_bus(GST_PIPELINE(m_gst_playbin));
		gst_bus_set_sync_handler(bus, NULL, NULL, NULL);
		gst_object_unref(bus);
	}

	stop();

	if (m_decoder) {
		m_decoder = NULL;
	}

	if (m_stream_tags)
		gst_tag_list_free(m_stream_tags);

	if (m_gst_playbin) {
		gst_object_unref(GST_OBJECT(m_gst_playbin));
		m_ref.path.clear();
		m_ref.name.clear();
		m_media_lenght = 0;
		m_play_position_timer->stop();
		m_last_seek_pos = 0;
		m_last_seek_count = -10;
		m_seeking_or_paused = false;
		m_to_paused = false;
		eDebug("[eServiceMP3] **** PIPELINE DESTRUCTED ****");
	}

	m_new_dvb_subtitle_page_connection = 0;
}

#ifdef PASSTHROUGH_FIX
void eServiceMP3::forcePassthrough() {
	eTrace("[eServiceMP3] Setting 'passthrough' to force correct operation");
	CFile::writeStr("/proc/stb/audio/ac3", "passthrough");
	m_clear_buffers = true;
	clearBuffers();
}
#endif

/**
 * @brief Updates the EPG cache for the current and next events.
 *
 * This function updates the EPG cache for the current and next events, using
 * information from the `eEPGCache` singleton instance. It checks if there are any
 * changes to the event listings for this service, and if so, it updates the
 * corresponding class fields (`m_event_now`, `m_event_next`) and notifies the
 * observers of changes to the event information.
 *
 * @param[in] update Whether an update is required.
 */
void eServiceMP3::updateEpgCacheNowNext() {
	bool update = false;
	ePtr<eServiceEvent> next = 0;
	ePtr<eServiceEvent> ptr = 0;
	eServiceReference ref(m_ref);
	ref.type = eServiceFactoryMP3::id;
	ref.path.clear();
	if (eEPGCache::getInstance() && eEPGCache::getInstance()->lookupEventTime(ref, -1, ptr) >= 0) {
		ePtr<eServiceEvent> current = m_event_now;
		if (!current || !ptr || current->getEventId() != ptr->getEventId()) {
			update = true;
			m_event_now = ptr;
			time_t next_time = ptr->getBeginTime() + ptr->getDuration();
			if (eEPGCache::getInstance()->lookupEventTime(ref, next_time, ptr) >= 0) {
				next = ptr;
				m_event_next = ptr;
			}
		}
	}

	int refreshtime = 60;
	if (!next) {
		next = m_event_next;
	}
	if (next) {
		time_t now = eDVBLocalTimeHandler::getInstance()->nowTime();
		refreshtime = (int)(next->getBeginTime() - now) + 3;
		if (refreshtime <= 0 || refreshtime > 60) {
			refreshtime = 60;
		}
	}
	m_nownext_timer->startLongTimer(refreshtime);
	if (update) {
		m_event((iPlayableService*)this, evUpdatedEventInfo);
	}
}

DEFINE_REF(eServiceMP3);

DEFINE_REF(GstMessageContainer);

/**
 * @brief Sets a cache entry for this service.
 *
 * This function sets a cache entry for this service, which can be used to store
 * information about the service's streams and other relevant details. The cache
 * entry is identified by the `ref` parameter, which should contain a string that
 * uniquely identifies the service.
 *
 * @param[in] ref A reference string for this service.
 * @param[in] isAudio Whether the stream is an audio stream or not.
 * @param[in] pid The PID of the audio or subtitle stream.
 */
void eServiceMP3::setCacheEntry(bool isAudio, int pid) {
	// eDebug("[eServiceMP3] setCacheEntry %d %d / %s", isAudio, pid, m_ref.toString().c_str());
	std::string ref = replace_all(m_ref.toString(), ",", "_");
	bool hasFoundItem = false;
	std::vector<ePtr<eDVBService>>& iptv_services = eDVBDB::getInstance()->iptv_services;
	for (std::vector<ePtr<eDVBService>>::iterator it = iptv_services.begin(); it != iptv_services.end(); ++it) {
		if (ref.find((*it)->m_reference_str) != std::string::npos) {
			hasFoundItem = true;
			(*it)->setCacheEntry(isAudio ? eDVBService::cMPEGAPID : eDVBService::cSUBTITLE, pid);
			break;
		}
	}
	if (!hasFoundItem) {
		ePtr<eDVBService> s = new eDVBService;
		s->m_reference_str = ref;
		s->setCacheEntry(isAudio ? eDVBService::cMPEGAPID : eDVBService::cSUBTITLE, pid);
		iptv_services.push_back(s);
	}
}

/**
 * @brief Connects an event to the service.
 *
 * This function connects a signal slot to the service's event system, allowing
 * external components to listen for specific events related to the service.
 *
 * @param[in] event The signal slot to connect.
 * @param[out] connection An output pointer that will hold the connection reference.
 * @return RESULT Returns 0 on success, or an error code if the connection fails.
 */
RESULT eServiceMP3::connectEvent(const sigc::slot<void(iPlayableService*, int)>& event, ePtr<eConnection>& connection) {
	connection = new eConnection((iPlayableService*)this, m_event.connect(event));
	return 0;
}

/**
 * @brief Starts the MP3 service.
 *
 * This function initializes the GStreamer playbin element, sets its state to
 * READY or PLAYING, and prepares the service for playback. It also attempts to
 * read event information from an associated .eit file if available.
 *
 * @return RESULT Returns 0 on success, or an error code if the service fails to start.
 */
RESULT eServiceMP3::start() {
	ASSERT(m_state == stIdle);

	m_subtitles_paused = false;
	if (m_gst_playbin) {
		eDebug("[eServiceMP3] *** starting pipeline ****");
		GstStateChangeReturn ret;
		ret = gst_element_set_state(m_gst_playbin, GST_STATE_READY);

		switch (ret) {
			case GST_STATE_CHANGE_FAILURE:
				eDebug("[eServiceMP3] failed to start pipeline");
				stop();
				return -1;
			case GST_STATE_CHANGE_SUCCESS:
				m_is_live = false;
				break;
			case GST_STATE_CHANGE_NO_PREROLL:
				gst_element_set_state(m_gst_playbin, GST_STATE_PLAYING);
				m_is_live = true;
				break;
			default:
				break;
		}
	}

	if (m_ref.path.find("://") == std::string::npos) {
		/* read event from .eit file */
		size_t pos;
		ePtr<eServiceEvent> event = new eServiceEvent;
		std::string filename = m_ref.path;
		if ((pos = filename.rfind('.')) != std::string::npos) {
			filename.erase(pos + 1);
			filename += "eit";
			if (!event->parseFrom(filename, 0)) {
				ePtr<eServiceEvent> empty;
				m_event_now = event;
				m_event_next = empty;
			}
		}
	}

	return 0;
}

/**
 * @brief Stops the MP3 service.
 *
 * This function stops the GStreamer playbin element, sets its state to NULL,
 * and cleans up any resources associated with the service. It also saves the
 * cuesheet if it was loaded and resets various member variables related to
 * playback state.
 *
 * @return RESULT Returns 0 on success, or an error code if the service fails to stop.
 */
RESULT eServiceMP3::stop() {
	if (!m_gst_playbin || m_state == stStopped)
		return -1;

	eDebug("[eServiceMP3] stop %s", m_ref.path.c_str());
	m_state = stStopped;

	GstStateChangeReturn ret;
	GstState state, pending;
	/* make sure that last state change was successfull */
	ret = gst_element_get_state(m_gst_playbin, &state, &pending, 5 * GST_SECOND);
	eDebug("[eServiceMP3] stop state:%s pending:%s ret:%s", gst_element_state_get_name(state),
		   gst_element_state_get_name(pending), gst_element_state_change_return_get_name(ret));
	ret = gst_element_set_state(m_gst_playbin, GST_STATE_NULL);
	if (ret != GST_STATE_CHANGE_SUCCESS)
		eDebug("[eServiceMP3] stop GST_STATE_NULL failure");
	if (!m_sourceinfo.is_streaming && m_cuesheet_loaded)
		saveCuesheet();
	m_subtitles_paused = false;
	m_nownext_timer->stop();
	/* make sure that media is stopped before proceeding further */
	ret = gst_element_get_state(m_gst_playbin, &state, &pending, 5 * GST_SECOND);
	eDebug("[eServiceMP3] **** TO NULL state:%s pending:%s ret:%s ****", gst_element_state_get_name(state),
		   gst_element_state_get_name(pending), gst_element_state_change_return_get_name(ret));

	return 0;
}

/**
 * @brief Handles the timing for playback position updates.
 *
 * This function is called periodically to update the playback position of the
 * media being played. It increments the last seek count and triggers an event
 * to update the service's information.
 */
void eServiceMP3::playPositionTiming() {
	// eDebug("[eServiceMP3] ***** USE IOCTL POSITION ******");
	if (m_last_seek_count >= 1) {
		if (m_last_seek_count == 19)
			m_last_seek_count = 0;
		else
			m_last_seek_count++;
	}
}

/**
 * @brief Pauses the MP3 service.
 *
 * This function pauses the playback of the media being played by the service.
 * It sets the state to PAUSED and starts a timer to synchronize subtitles if
 * applicable. If the service is already paused, it does nothing.
 *
 * @param[out] ptr A pointer to an iPauseableService interface that can be used to pause the service.
 * @return RESULT Returns 0 on success, or an error code if the service fails to pause.
 */
RESULT eServiceMP3::pause(ePtr<iPauseableService>& ptr) {
	ptr = this;
	eDebug("[eServiceMP3] pause(ePtr<iPauseableService> &ptr)");
	return 0;
}

/**
 * @brief Sets the slow motion playback ratio.
 *
 * This function sets the playback speed to a slow motion ratio. If the ratio is
 * zero, it returns immediately without changing the playback speed. Otherwise,
 * it calls `trickSeek` with the inverse of the ratio to achieve slow motion.
 *
 * @param[in] ratio The slow motion ratio (1.0 for normal speed, >1.0 for slow motion).
 * @return RESULT Returns 0 on success, or an error code if the service fails to set slow motion.
 */
RESULT eServiceMP3::setSlowMotion(int ratio) {
	if (!ratio)
		return 0;
	eDebug("[eServiceMP3] setSlowMotion ratio=%.1f", 1.0 / (gdouble)ratio);
	return trickSeek(1.0 / (gdouble)ratio);
}

/**
 * @brief Sets the fast forward playback ratio.
 *
 * This function sets the playback speed to a fast forward ratio. If the ratio is
 * zero, it returns immediately without changing the playback speed. Otherwise,
 * it calls `trickSeek` with the specified ratio to achieve fast forward.
 *
 * @param[in] ratio The fast forward ratio (1.0 for normal speed, >1.0 for fast forward).
 * @return RESULT Returns 0 on success, or an error code if the service fails to set fast forward.
 */
RESULT eServiceMP3::setFastForward(int ratio) {
	eDebug("[eServiceMP3] setFastForward ratio=%.1f", (gdouble)ratio);
	return trickSeek(ratio);
}

// iPausableService

/**
 * @brief Pauses the MP3 service.
 *
 * This function pauses the playback of the media being played by the service.
 * It sets the state to PAUSED and starts a timer to synchronize subtitles if
 * applicable. If the service is already paused, it does nothing.
 *
 * @return RESULT Returns 0 on success, or an error code if the service fails to pause.
 */
RESULT eServiceMP3::pause() {
	if (!m_gst_playbin || m_state != stRunning)
		return -1;

	m_subtitles_paused = true;
	m_subtitle_sync_timer->start(1, true);
	eDebug("[eServiceMP3] pause");
	if (!m_paused)
		trickSeek(0.0);
	else
		eDebug("[eServiceMP3] Already Paused no need to pause");

	return 0;
}

/**
 * @brief Unpauses the MP3 service.
 *
 * This function resumes playback of the media being played by the service.
 * It sets the state to RUNNING and starts a timer to synchronize subtitles if
 * applicable. If the service is not paused, it does nothing.
 *
 * @return RESULT Returns 0 on success, or an error code if the service fails to unpause.
 */
RESULT eServiceMP3::unpause() {
	if (!m_gst_playbin || m_state != stRunning)
		return -1;

	m_subtitles_paused = false;
	m_decoder_time_valid_state = 0;
	m_subtitle_sync_timer->start(1, true);
	/* no need to unpase if we are not paused already */
	if (m_currentTrickRatio == 1.0 && !m_paused) {
		eDebug("[eServiceMP3] trickSeek no need to unpause!");
		return 0;
	}

	eDebug("[eServiceMP3] unpause");
	trickSeek(1.0);

	return 0;
}

// iSeekableService

/**
 * @brief Seeks to a specific position in the media.
 *
 * This function seeks to a specific position in the media being played by the
 * service. It updates the last seek position and calls `seekToImpl` to perform
 * the actual seek operation.
 *
 * @param[out] ptr A pointer to an iSeekableService interface that can be used to seek in the service.
 * @return RESULT Returns 0 on success, or an error code if the service fails to seek.
 */
RESULT eServiceMP3::seek(ePtr<iSeekableService>& ptr) {
	ptr = this;
	return 0;
}

/**
 * @brief Gets the current playback position in the media.
 *
 * This function retrieves the current playback position in the media being played
 * by the service. It queries the GStreamer playbin for the current position and
 * returns it in PTS format.
 *
 * @param[out] pts The current playback position in PTS format.
 * @return RESULT Returns 0 on success, or an error code if the service fails to get the position.
 */
RESULT eServiceMP3::getLength(pts_t& pts) {
	if (!m_gst_playbin || m_state != stRunning)
		return -1;

	GstFormat fmt = GST_FORMAT_TIME;
	gint64 len;
	if (!gst_element_query_duration(m_gst_playbin, fmt, &len))
		return -1;
	/* len is in nanoseconds. we have 90 000 pts per second. */

	pts = len / 11111LL;
	m_media_lenght = pts;
	return 0;
}

/**
 * @brief Seeks to a specific position in the media.
 *
 * This function seeks to a specific position in the media being played by the
 * service. It converts the PTS to nanoseconds and calls `gst_element_seek` to
 * perform the seek operation. If the seek is successful, it updates the last
 * seek position and triggers an event to update the service's information.
 *
 * @param[in] to The position to seek to in PTS format.
 * @return RESULT Returns 0 on success, or an error code if the service fails to seek.
 */
RESULT eServiceMP3::seekToImpl(pts_t to) {
	// eDebug("[eServiceMP3] seekToImpl pts_t to %" G_GINT64_FORMAT, (gint64)to);
	/* convert pts to nanoseconds */
	m_last_seek_pos = to;
	if (!gst_element_seek(m_gst_playbin, m_currentTrickRatio, GST_FORMAT_TIME,
						  (GstSeekFlags)(GST_SEEK_FLAG_FLUSH | GST_SEEK_FLAG_KEY_UNIT), GST_SEEK_TYPE_SET,
						  (gint64)(m_last_seek_pos * 11111LL), GST_SEEK_TYPE_NONE, GST_CLOCK_TIME_NONE)) {
		eDebug("[eServiceMP3] seekTo failed");
		return -1;
	}
	if (m_paused || m_to_paused) {
		m_last_seek_count = 0;
		m_event((iPlayableService*)this, evUpdatedInfo);
	}
	// eDebug("[eServiceMP3] seekToImpl DONE position %" G_GINT64_FORMAT, (gint64)m_last_seek_pos);
	if (!m_paused) {
		if (!m_to_paused) {
			m_seeking_or_paused = false;
			m_last_seek_count = 1;
		}
	}
	return 0;
}

/**
 * @brief Seeks to a specific position in the media.
 *
 * This function seeks to a specific position in the media being played by the
 * service. It updates the last seek position and calls `seekToImpl` to perform
 * the actual seek operation. If the service is not running, it returns an error.
 *
 * @param[in] to The position to seek to in PTS format.
 * @return RESULT Returns 0 on success, or an error code if the service fails to seek.
 */
RESULT eServiceMP3::seekTo(pts_t to) {
	RESULT ret = -1;
	// eDebug("[eServiceMP3] seekTo(pts_t to)");
	if (m_gst_playbin) {
		m_prev_decoder_time = -1;
		m_decoder_time_valid_state = 0;
		m_seeking_or_paused = true;
		ret = seekToImpl(to);
	}

	return ret;
}

/**
 * @brief Performs a trick seek operation.
 *
 * This function performs a trick seek operation, which can be used to change
 * the playback speed or pause the playback. It handles different cases based on
 * the provided ratio and updates the playback state accordingly.
 *
 * @param[in] ratio The trick seek ratio (1.0 for normal speed, >1.0 for fast forward, <1.0 for slow motion).
 * @return RESULT Returns 0 on success, or an error code if the service fails to perform the trick seek.
 */
RESULT eServiceMP3::trickSeek(gdouble ratio) {
	if (!m_gst_playbin)
		return -1;
	// eDebug("[eServiceMP3] trickSeek %.1f", ratio);
	GstState state, pending;
	GstStateChangeReturn ret;
	int pos_ret = -1;
	pts_t pts;

	if (ratio > -0.01 && ratio < 0.01) {
		// m_last_seek_count = 0;
		pos_ret = getPlayPosition(pts);
		m_to_paused = true;
		gst_element_set_state(m_gst_playbin, GST_STATE_PAUSED);
		// m_paused = true;
		if (pos_ret >= 0)
			seekTo(pts);
		/* pipeline sometimes block due to audio track issue off gstreamer.
		If the pipeline is blocked up on pending state change to paused ,
		this issue is solved by seek to playposition*/
		ret = gst_element_get_state(m_gst_playbin, &state, &pending, 3LL * GST_SECOND);
		if (state == GST_STATE_PLAYING && pending == GST_STATE_PAUSED) {
			m_clear_buffers = true;
			if (m_currentAudioStream >= 0)
				selectAudioStream(m_currentAudioStream, true);
			else
				selectAudioStream(0, true);
			m_clear_buffers = false;

			if (pos_ret >= 0) {
				eDebug("[eServiceMP3] blocked pipeline we need to flush playposition in pts at last pos before paused "
					   "is %" G_GINT64_FORMAT,
					   (gint64)pts);
				seekTo(pts);

			} else if (getPlayPosition(pts) >= 0) {
				eDebug("[eServiceMP3] blocked pipeline we need to flush playposition in pts at paused is "
					   "%" G_GINT64_FORMAT,
					   (gint64)pts);
				seekTo(pts);
			}
		}
		// m_last_seek_count = 0;
		return 0;
	}

	bool unpause = (m_currentTrickRatio == 1.0 && ratio == 1.0);
	if (unpause) {
		GstElement* source = NULL;
		GstElementFactory* factory = NULL;
		const gchar* name = NULL;
		g_object_get(m_gst_playbin, "source", &source, NULL);
		if (!source) {
			eDebugNoNewLineStart("[eServiceMP3] trickSeek - cannot get source");
			goto seek_unpause;
		}
		factory = gst_element_get_factory(source);
		g_object_unref(source);
		if (!factory) {
			eDebugNoNewLineStart("[eServiceMP3] trickSeek - cannot get source factory");
			goto seek_unpause;
		}
		name = gst_plugin_feature_get_name(GST_PLUGIN_FEATURE(factory));
		if (!name) {
			eDebugNoNewLineStart("[eServiceMP3] trickSeek - cannot get source name");
			goto seek_unpause;
		}
		/*
		 * We know that filesrc and souphttpsrc will not timeout after long pause
		 * If there are other sources which will not timeout, add them here
		 */
		if (!strcmp(name, "filesrc") || !strcmp(name, "souphttpsrc")) {
			/* previous state was already ok if we come here just give all elements time to unpause */
			m_to_paused = false;
			gst_element_set_state(m_gst_playbin, GST_STATE_PLAYING);
			ret = gst_element_get_state(m_gst_playbin, &state, &pending, 2 * GST_SECOND);
			m_seeking_or_paused = false;
			m_last_seek_count = 0;
			eDebug("[eServiceMP3] unpause state:%s pending:%s ret:%s", gst_element_state_get_name(state),
				   gst_element_state_get_name(pending), gst_element_state_change_return_get_name(ret));
			return 0;
		} else {
			eDebugNoNewLineStart("[eServiceMP3] trickSeek - source '%s' is not supported", name);
		}
	seek_unpause:
		eDebug(", doing seeking unpause\n");
	}

	m_currentTrickRatio = ratio;

	bool validposition = false;
	gint64 pos = 0;
	if (m_last_seek_pos > 0) {
		validposition = true;
		pos = m_last_seek_pos * 11111LL;
	} else if (getPlayPosition(pts) >= 0) {
		validposition = true;
		pos = pts * 11111LL;
	}

	ret = gst_element_get_state(m_gst_playbin, &state, &pending, 2 * GST_SECOND);
	if (state != GST_STATE_PLAYING) {
		eDebug("[eServiceMP3] set unpause or change playrate when gst was state %s pending %s change return %s",
			   gst_element_state_get_name(state), gst_element_state_get_name(pending),
			   gst_element_state_change_return_get_name(ret));
		gst_element_set_state(m_gst_playbin, GST_STATE_PLAYING);
		m_seeking_or_paused = false;
		m_last_seek_count = 0;
		m_to_paused = false;
	}

	if (validposition) {
		if (ratio >= 0.0) {
			gst_element_seek(
				m_gst_playbin, ratio, GST_FORMAT_TIME,
				(GstSeekFlags)(GST_SEEK_FLAG_FLUSH | GST_SEEK_FLAG_TRICKMODE | GST_SEEK_FLAG_TRICKMODE_NO_AUDIO),
				GST_SEEK_TYPE_SET, pos, GST_SEEK_TYPE_SET, -1);
		} else {
			/* note that most elements will not support negative speed */
			gst_element_seek(
				m_gst_playbin, ratio, GST_FORMAT_TIME,
				(GstSeekFlags)(GST_SEEK_FLAG_FLUSH | GST_SEEK_FLAG_TRICKMODE | GST_SEEK_FLAG_TRICKMODE_NO_AUDIO),
				GST_SEEK_TYPE_SET, 0, GST_SEEK_TYPE_SET, pos);
		}
	}

	m_prev_decoder_time = -1;
	m_decoder_time_valid_state = 0;
	return 0;
}

/**
 * @brief Seeks relative to the current playback position.
 *
 * This function seeks relative to the current playback position in the media
 * being played by the service. It updates the last seek position and calls
 * `seekTo` to perform the actual seek operation.
 *
 * @param[in] direction The direction to seek (positive for forward, negative for backward).
 * @param[in] to The amount to seek in PTS format.
 * @return RESULT Returns 0 on success, or an error code if the service fails to seek.
 */
RESULT eServiceMP3::seekRelative(int direction, pts_t to) {
	if (!m_gst_playbin)
		return -1;

	// eDebug("[eServiceMP3]  seekRelative direction %d, pts_t to %" G_GINT64_FORMAT, direction, (gint64)to);
	pts_t ppos = 0;
	// m_seeking_or_paused = true;
	if (direction > 0) {
		if (getPlayPosition(ppos) < 0)
			return -1;
		ppos += to;
		m_seeking_or_paused = true;
		return seekTo(ppos);
	} else {
		if (getPlayPosition(ppos) < 0)
			return -1;
		ppos -= to;
		if (ppos < 0)
			ppos = 0;
		m_seeking_or_paused = true;
		return seekTo(ppos);
	}
}

/**
 * @brief Matches the sink type of a GStreamer element.
 *
 * This function checks if the type of a GStreamer element matches a specified
 * type string. It is used to determine if the element is compatible with the
 * expected sink type for audio or video playback.
 *
 * @param[in] velement A GValue containing the GStreamer element to check.
 * @param[in] type The expected type string to match against.
 * @return gint Returns 0 if the types match, or a non-zero value if they do not match.
 */
gint eServiceMP3::match_sinktype(const GValue* velement, const gchar* type) {
	GstElement* element = GST_ELEMENT_CAST(g_value_get_object(velement));
	return strcmp(g_type_name(G_OBJECT_TYPE(element)), type);
}

/**
 * @brief Gets the current playback position in the media.
 *
 * This function retrieves the current playback position in the media being played
 * by the service. It queries the GStreamer playbin for the current position and
 * returns it in PTS format. It also handles special cases for live streams and
 * paused states.
 *
 * @param[out] pts The current playback position in PTS format.
 * @return RESULT Returns 0 on success, or an error code if the service fails to get the position.
 */
RESULT eServiceMP3::getPlayPosition(pts_t& pts) {
	gint64 pos = 0;

	if (!m_gst_playbin || m_state != stRunning)
		return -1;
	// allow only one ioctl call per second
	// in case of seek procedure , the position
	// is updated by the seektoImpl function.
	// eDebug("[eServiceMP3] getPlayPosition m_last_seek_count = %d", m_last_seek_count);
	if (m_last_seek_count <= 0) {
		// eDebug("[eServiceMP3] ** START USE LAST SEEK TIMER");
		if (m_last_seek_count == -10) {
			eDebug("[eServiceMP3] ** START USE LAST SEEK TIMER");
			m_play_position_timer->start(50, false);
			m_last_seek_count = 0;
		} else {
			if (m_paused) {
				pts = m_last_seek_pos;
				m_last_seek_count = 0;
				return 0;
			} else
				m_last_seek_count = 1;
		}
	} else {
		if (m_paused || m_seeking_or_paused) {
			m_last_seek_count = 0;
			pts = m_last_seek_pos;
		} else {
			if (m_last_seek_count >= 1)
				pts = m_last_seek_pos + ((m_last_seek_count - 1) * 4500);
			else
				pts = m_last_seek_pos;
		}
		return 0;
	}
	// todo :Check if amlogic stb's are always using gstreamer < 1
	// if not this procedure needs to be altered.
	// if ((dvb_audiosink || dvb_videosink) && !m_paused && !m_seeking_or_paused && !m_sourceinfo.is_hls)
	if ((dvb_audiosink || dvb_videosink) && !m_paused && !m_seeking_or_paused) {
		// eDebug("[eServiceMP3] getPlayPosition Check dvb_audiosink or dvb_videosink");
		if (m_sourceinfo.is_audio) {
			g_signal_emit_by_name(dvb_audiosink, "get-decoder-time", &pos);
			if (!GST_CLOCK_TIME_IS_VALID(pos))
				return -1;
		} else {
			/* most stb's work better when pts is taken by audio by some video must be taken cause
			 * audio is 0 or invalid */
			/* avoid taking the audio play position if audio sink is in state NULL */
			if (!m_audiosink_not_running) {
				g_signal_emit_by_name(dvb_audiosink, "get-decoder-time", &pos);
				if (!GST_CLOCK_TIME_IS_VALID(pos) || 0)
					g_signal_emit_by_name(dvb_videosink, "get-decoder-time", &pos);
				if (!GST_CLOCK_TIME_IS_VALID(pos))
					return -1;
			} else {
				g_signal_emit_by_name(dvb_videosink, "get-decoder-time", &pos);
				if (!GST_CLOCK_TIME_IS_VALID(pos))
					return -1;
			}
		}
	} else {
		GstFormat fmt = GST_FORMAT_TIME;
		if (!gst_element_query_position(m_gst_playbin, fmt, &pos)) {
			// eDebug("[eServiceMP3] gst_element_query_position failed in getPlayPosition");
			if (m_last_seek_pos > 0) {
				pts = m_last_seek_pos;
				m_last_seek_count = 0;
				return 0;
			} else
				return -1;
		}
	}

	/* pos is in nanoseconds. we have 90 000 pts per second. */
	m_last_seek_pos = pos / 11111LL;
	pts = m_last_seek_pos;
	// eDebug("[eServiceMP3] current play pts = %" G_GINT64_FORMAT, pts);
	return 0;
}

/**
 * @brief Gets the current decoder time for live streams.
 *
 * This function retrieves the current decoder time for live streams. It emits
 * a signal to the dvb_videosink to get the decoder time and converts it from
 * nanoseconds to 90kHz PTS format.
 *
 * @return int64_t Returns the current decoder time in 90kHz PTS format, or -1 if not valid.
 */
int64_t eServiceMP3::getLiveDecoderTime() {
	gint64 pos = 0;
	if (dvb_videosink) {
		g_signal_emit_by_name(dvb_videosink, "get-decoder-time", &pos);
		if (GST_CLOCK_TIME_IS_VALID(pos) && pos > 0) {
			// Convert from nanoseconds back to 90kHz
			return pos / 11111;
		}
	}
	return -1;
}

/**
 * @brief Sets the trick mode for the service.
 *
 * This function sets the trick mode for the service, which can be used to
 * change the playback speed or pause the playback. It currently does not support
 * trick modes and returns an error.
 *
 * @param[in] trick The trick mode to set (not supported).
 * @return RESULT Returns -1 indicating that trick modes are not supported.
 */
RESULT eServiceMP3::setTrickmode(int trick) {
	/* trickmode is not yet supported by our dvbmediasinks. */
	return -1;
}

/**
 * @brief Checks if the service is currently seekable.
 *
 * This function checks if the service is currently seekable. It returns 0 if
 * the service is not seekable, or a positive value if it is seekable. If the
 * service is live, it is assumed to be not seekable.
 *
 * @return RESULT Returns 0 if not seekable, or a positive value if seekable.
 */
RESULT eServiceMP3::isCurrentlySeekable() {
	int ret = 3; /* just assume that seeking and fast/slow winding are possible */

	if (!m_gst_playbin)
		return 0;

	return ret;
}

/**
 * @brief Provides information about the service.
 *
 * This function provides information about the service, including its type,
 * name, and other metadata. It sets the provided pointer to the current service
 * instance.
 *
 * @param[out] i A pointer to an iServiceInformation interface that will hold the service information.
 * @return RESULT Returns 0 on success, or an error code if the service fails to provide information.
 */
RESULT eServiceMP3::info(ePtr<iServiceInformation>& i) {
	i = this;
	return 0;
}

/**
 * @brief Gets the name of the service.
 *
 * This function retrieves the name of the service. If the service has a title
 * tag, it uses that; otherwise, it extracts the name from the service reference
 * path. It returns 0 on success.
 *
 * @param[out] name A reference to a string that will hold the service name.
 * @return RESULT Returns 0 on success, or an error code if the service fails to get the name.
 */
RESULT eServiceMP3::getName(std::string& name) {
	std::string title = m_ref.getName();
	if (title.empty()) {
		name = m_ref.path;
		size_t n = name.rfind('/');
		if (n != std::string::npos)
			name = name.substr(n + 1);
	} else
		name = title;
	return 0;
}

/**
 * @brief Gets the current event associated with the service.
 *
 * This function retrieves the current event associated with the service. It
 * checks if the event is available and returns it through the provided pointer.
 * If no event is available, it returns an error code.
 *
 * @param[out] evt A pointer to an eServiceEvent that will hold the current event.
 * @param[in] nownext If true, retrieves the next event; otherwise, retrieves the current event.
 * @return RESULT Returns 0 on success, or -1 if no event is available.
 */
RESULT eServiceMP3::getEvent(ePtr<eServiceEvent>& evt, int nownext) {
	evt = nownext ? m_event_next : m_event_now;
	if (!evt)
		return -1;
	return 0;
}

/**
 * @brief Gets information about the service.
 *
 * This function retrieves various pieces of information about the service,
 * such as video height, width, frame rate, aspect ratio, and more. It returns
 * the requested information based on the provided parameter.
 *
 * @param[in] w The type of information to retrieve.
 * @return int Returns the requested information or a specific result code.
 */
int eServiceMP3::getInfo(int w) {
	const gchar* tag = 0;

	switch (w) {
		case sVideoHeight:
			return m_height;
		case sVideoWidth:
			return m_width;
		case sFrameRate:
			return m_framerate;
		case sProgressive:
			return m_progressive;
		case sGamma:
			return m_gamma;
		case sAspect:
			return m_aspect;
		case sServiceref:
		case sTagTitle:
		case sTagArtist:
		case sTagAlbum:
		case sTagTitleSortname:
		case sTagArtistSortname:
		case sTagAlbumSortname:
		case sTagDate:
		case sTagComposer:
		case sTagGenre:
		case sTagComment:
		case sTagExtendedComment:
		case sTagLocation:
		case sTagHomepage:
		case sTagDescription:
		case sTagVersion:
		case sTagISRC:
		case sTagOrganization:
		case sTagCopyright:
		case sTagCopyrightURI:
		case sTagContact:
		case sTagLicense:
		case sTagLicenseURI:
		case sTagCodec:
		case sTagAudioCodec:
		case sTagVideoCodec:
		case sTagEncoder:
		case sTagLanguageCode:
		case sTagKeywords:
		case sTagChannelMode:
		case sUser + 12:
			return resIsString;
		case sTagTrackGain:
		case sTagTrackPeak:
		case sTagAlbumGain:
		case sTagAlbumPeak:
		case sTagReferenceLevel:
		case sTagBeatsPerMinute:
		case sTagImage:
		case sTagPreviewImage:
		case sTagAttachment:
			return resIsPyObject;
		case sTagTrackNumber:
			tag = GST_TAG_TRACK_NUMBER;
			break;
		case sTagTrackCount:
			tag = GST_TAG_TRACK_COUNT;
			break;
		case sTagAlbumVolumeNumber:
			tag = GST_TAG_ALBUM_VOLUME_NUMBER;
			break;
		case sTagAlbumVolumeCount:
			tag = GST_TAG_ALBUM_VOLUME_COUNT;
			break;
		case sTagBitrate:
			tag = GST_TAG_BITRATE;
			break;
		case sTagNominalBitrate:
			tag = GST_TAG_NOMINAL_BITRATE;
			break;
		case sTagMinimumBitrate:
			tag = GST_TAG_MINIMUM_BITRATE;
			break;
		case sTagMaximumBitrate:
			tag = GST_TAG_MAXIMUM_BITRATE;
			break;
		case sTagSerial:
			tag = GST_TAG_SERIAL;
			break;
		case sTagEncoderVersion:
			tag = GST_TAG_ENCODER_VERSION;
			break;
		case sTagCRC:
			tag = "has-crc";
			break;
		case sBuffer:
			return m_bufferInfo.bufferPercent;
		case sVideoType: {
			if (!dvb_videosink)
				return -1;
			guint64 v = -1;
			g_signal_emit_by_name(dvb_videosink, "get-video-codec", &v);
			return (int)v;
		}
		case sSID:
			return m_ref.getData(1);
		default:
			return resNA;
	}

	if (!m_stream_tags || !tag)
		return 0;

	guint value;
	if (gst_tag_list_get_uint(m_stream_tags, tag, &value))
		return (int)value;

	return 0;
}

/**
 * @brief Gets a string representation of the service information.
 *
 * This function retrieves a string representation of the service information
 * based on the provided parameter. It handles various cases, including streaming
 * services, video information, and metadata tags.
 *
 * @param[in] w The type of information to retrieve as a string.
 * @return std::string Returns the requested information as a string.
 */
std::string eServiceMP3::getInfoString(int w) {
	if (m_sourceinfo.is_streaming) {
		switch (w) {
			case sProvider:
				return "IPTV";
			case sServiceref: {
				return m_ref.toString();
			}
			default:
				break;
		}
	}

	if (w == sVideoInfo) {
		char buff[100];
		snprintf(buff, sizeof(buff), "%d|%d|%d|%d|%d|%d", m_width, m_height, m_framerate, m_progressive, m_aspect,
				 m_gamma);
		std::string videoInfo = buff;
		return videoInfo;
	}

	if (!m_stream_tags && w < sUser && w > 26)
		return "";
	const gchar* tag = 0;
	switch (w) {
		case sTagTitle:
			tag = GST_TAG_TITLE;
			break;
		case sTagArtist:
			tag = GST_TAG_ARTIST;
			break;
		case sTagAlbum:
			tag = GST_TAG_ALBUM;
			break;
		case sTagTitleSortname:
			tag = GST_TAG_TITLE_SORTNAME;
			break;
		case sTagArtistSortname:
			tag = GST_TAG_ARTIST_SORTNAME;
			break;
		case sTagAlbumSortname:
			tag = GST_TAG_ALBUM_SORTNAME;
			break;
		case sTagDate:
			GDate* date;
			GstDateTime* date_time;
			if (gst_tag_list_get_date(m_stream_tags, GST_TAG_DATE, &date)) {
#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wformat-truncation"
				gchar res[5];
				snprintf(res, sizeof(res), "%04d", g_date_get_year(date));
#pragma GCC diagnostic pop
				g_date_free(date);
				return (std::string)res;
			} else if (gst_tag_list_get_date_time(m_stream_tags, GST_TAG_DATE_TIME, &date_time)) {
				if (gst_date_time_has_year(date_time)) {
					gchar res[5];
					snprintf(res, sizeof(res), "%04d", gst_date_time_get_year(date_time));
					gst_date_time_unref(date_time);
					return (std::string)res;
				}
				gst_date_time_unref(date_time);
			}
			break;
		case sTagComposer:
			tag = GST_TAG_COMPOSER;
			break;
		case sTagGenre:
			tag = GST_TAG_GENRE;
			break;
		case sTagComment:
			tag = GST_TAG_COMMENT;
			break;
		case sTagExtendedComment:
			tag = GST_TAG_EXTENDED_COMMENT;
			break;
		case sTagLocation:
			tag = GST_TAG_LOCATION;
			break;
		case sTagHomepage:
			tag = GST_TAG_HOMEPAGE;
			break;
		case sTagDescription:
			tag = GST_TAG_DESCRIPTION;
			break;
		case sTagVersion:
			tag = GST_TAG_VERSION;
			break;
		case sTagISRC:
			tag = GST_TAG_ISRC;
			break;
		case sTagOrganization:
			tag = GST_TAG_ORGANIZATION;
			break;
		case sTagCopyright:
			tag = GST_TAG_COPYRIGHT;
			break;
		case sTagCopyrightURI:
			tag = GST_TAG_COPYRIGHT_URI;
			break;
		case sTagContact:
			tag = GST_TAG_CONTACT;
			break;
		case sTagLicense:
			tag = GST_TAG_LICENSE;
			break;
		case sTagLicenseURI:
			tag = GST_TAG_LICENSE_URI;
			break;
		case sTagCodec:
			tag = GST_TAG_CODEC;
			break;
		case sTagAudioCodec:
			tag = GST_TAG_AUDIO_CODEC;
			break;
		case sTagVideoCodec:
			tag = GST_TAG_VIDEO_CODEC;
			break;
		case sTagEncoder:
			tag = GST_TAG_ENCODER;
			break;
		case sTagLanguageCode:
			tag = GST_TAG_LANGUAGE_CODE;
			break;
		case sTagKeywords:
			tag = GST_TAG_KEYWORDS;
			break;
		case sTagChannelMode:
			tag = "channel-mode";
			break;
		case sUser + 12:
			return m_errorInfo.error_message;
		default:
			return "";
	}
	if (!tag)
		return "";
	gchar* value = NULL;
	if (m_stream_tags && gst_tag_list_get_string(m_stream_tags, tag, &value)) {
		std::string res = value;
		g_free(value);
		return res;
	}
	return "";
}

/**
 * @brief Gets an information object for the specified tag.
 *
 * This function retrieves an information object for the specified tag. It creates
 * an instance of eServiceMP3InfoContainer and populates it with the relevant data
 * from the stream tags. The type of data retrieved depends on the specified tag.
 *
 * @param[in] w The tag for which to retrieve the information object.
 * @return ePtr<iServiceInfoContainer> Returns a pointer to the information container.
 */
ePtr<iServiceInfoContainer> eServiceMP3::getInfoObject(int w) {
	eServiceMP3InfoContainer* container = new eServiceMP3InfoContainer;
	ePtr<iServiceInfoContainer> retval = container;
	const gchar* tag = 0;
	bool isBuffer = false;
	switch (w) {
		case sTagTrackGain:
			tag = GST_TAG_TRACK_GAIN;
			break;
		case sTagTrackPeak:
			tag = GST_TAG_TRACK_PEAK;
			break;
		case sTagAlbumGain:
			tag = GST_TAG_ALBUM_GAIN;
			break;
		case sTagAlbumPeak:
			tag = GST_TAG_ALBUM_PEAK;
			break;
		case sTagReferenceLevel:
			tag = GST_TAG_REFERENCE_LEVEL;
			break;
		case sTagBeatsPerMinute:
			tag = GST_TAG_BEATS_PER_MINUTE;
			break;
		case sTagImage:
			tag = GST_TAG_IMAGE;
			isBuffer = true;
			break;
		case sTagPreviewImage:
			tag = GST_TAG_PREVIEW_IMAGE;
			isBuffer = true;
			break;
		case sTagAttachment:
			tag = GST_TAG_ATTACHMENT;
			isBuffer = true;
			break;
		default:
			break;
	}

	if (m_stream_tags && tag) {
		if (isBuffer) {
			const GValue* gv_buffer = gst_tag_list_get_value_index(m_stream_tags, tag, 0);
			if (gv_buffer) {
				GstBuffer* buffer;
				buffer = gst_value_get_buffer(gv_buffer);
				container->setBuffer(buffer);
			}
		} else {
			gdouble value = 0.0;
			gst_tag_list_get_double(m_stream_tags, tag, &value);
			container->setDouble(value);
		}
	}
	return retval;
}

RESULT eServiceMP3::audioChannel(ePtr<iAudioChannelSelection>& ptr) {
	ptr = this;
	return 0;
}

RESULT eServiceMP3::audioTracks(ePtr<iAudioTrackSelection>& ptr) {
	ptr = this;
	return 0;
}

RESULT eServiceMP3::cueSheet(ePtr<iCueSheet>& ptr) {
	ptr = this;
	return 0;
}

RESULT eServiceMP3::subtitle(ePtr<iSubtitleOutput>& ptr) {
	ptr = this;
	return 0;
}

RESULT eServiceMP3::audioDelay(ePtr<iAudioDelay>& ptr) {
	ptr = this;
	return 0;
}

/**
 * @brief Gets the number of audio tracks available in the service.
 *
 * This function retrieves the number of audio tracks available in the service.
 * It checks the size of the `m_audioStreams` vector, which holds information about
 * the audio streams, and returns the count.
 *
 * @return int Returns the number of audio tracks available in the service.
 */
int eServiceMP3::getNumberOfTracks() {
	return m_audioStreams.size();
}

/**
 * @brief Gets the current audio track index.
 *
 * This function retrieves the current audio track index from the GStreamer playbin.
 * If the current audio stream is not set, it queries the playbin for the current audio stream.
 *
 * @return int Returns the index of the current audio track, or -1 if no audio stream is set.
 */
int eServiceMP3::getCurrentTrack() {
	if (m_currentAudioStream == -1)
		g_object_get(m_gst_playbin, "current-audio", &m_currentAudioStream, NULL);
	return m_currentAudioStream;
}

/**
 * @brief Selects the specified audio track.
 *
 * This function selects the specified audio track by its index. It checks if the
 * current audio stream is already set to the specified index and returns early if so.
 * Otherwise, it clears the buffers and calls `selectAudioStream` to perform the selection.
 *
 * @param[in] i The index of the audio track to select.
 * @return RESULT Returns 0 on success, or an error code if the selection fails.
 */
RESULT eServiceMP3::selectTrack(unsigned int i) {
	m_currentAudioStream = getCurrentTrack();
	if (m_currentAudioStream == (int)i)
		return m_currentAudioStream;
	eDebug("[eServiceMP3 selectTrack %d", i);

	m_clear_buffers = true;
	int result = selectAudioStream(i);
	return result;
}

/**
 * @brief Clears the audio and video buffers.
 *
 * This function clears the audio and video buffers by seeking to a position
 * that is slightly before the current playback position. It is called when
 * the service is started or when the buffers need to be cleared.
 *
 * @param[in] force If true, forces the clearing of buffers even if not initially started.
 */
void eServiceMP3::clearBuffers(bool force) {
	if ((!m_initial_start || !m_clear_buffers) && !force)
		return;

	bool validposition = false;
	pts_t ppos = 0;
	if (getPlayPosition(ppos) >= 0) {
		validposition = true;
		ppos -= 90000;
		if (ppos < 0)
			ppos = 0;
	}
	if (validposition) {
		/* flush */
		int res = seekTo(ppos);
		if (res == -1) {
			m_clear_buffers = false;
			m_send_ev_start = false;
			stop();
			m_state = stIdle;
			start();
		}
	}
}

/**
 * @brief Selects the specified audio stream.
 *
 * This function selects the specified audio stream by its index. It checks if the
 * current audio stream is already set to the specified index and returns early if so.
 * If the selection is successful, it clears the buffers and sets the cache entry.
 *
 * @param[in] i The index of the audio stream to select.
 * @param[in] skipAudioFix If true, skips the audio fix logic.
 * @return int Returns 0 on success, or -1 if the selection fails.
 */
int eServiceMP3::selectAudioStream(int i, bool skipAudioFix) {
	int current_audio, current_audio_orig;
	g_object_get(m_gst_playbin, "current-audio", &current_audio_orig, NULL);
	g_object_set(m_gst_playbin, "current-audio", i, NULL);
	g_object_get(m_gst_playbin, "current-audio", &current_audio, NULL);
	if (current_audio == i) {
		if (!skipAudioFix) {
			eDebug("[eServiceMP3] switched to audio stream %d", current_audio);
			m_currentAudioStream = i;

#ifdef PASSTHROUGH_FIX
			GstPad* pad = 0;
			g_signal_emit_by_name(m_gst_playbin, "get-audio-pad", i, &pad);
			GstCaps* caps = gst_pad_get_current_caps(pad);
			gst_object_unref(pad);
			if (caps) {
				GstStructure* str = gst_caps_get_structure(caps, 0);
				const gchar* g_type = gst_structure_get_name(str);
				audiotype_t apidtype = gstCheckAudioPad(str);
				gst_caps_unref(caps);
				if (apidtype == atAC3 || apidtype == atEAC3 || apidtype == atAAC || apidtype == atUnknown ||
					apidtype == atPCM) {
					std::string pass = CFile::read("/proc/stb/audio/ac3");
					if (pass.find("passthrough") != std::string::npos) {
						int longAudioDelay = eSimpleConfig::getInt("config.av.passthrough_fix_long", 1200);
						int shortAudioDelay = eSimpleConfig::getInt("config.av.passthrough_fix_short", 100);
						if (m_clear_buffers) {
							m_passthrough_fix_timer->stop();
							m_passthrough_fix_timer->start(apidtype == atEAC3 && i > 0 && current_audio_orig > -1
															   ? longAudioDelay
															   : shortAudioDelay,
														   true);
						}

					} else {
						clearBuffers();
					}
				} else {
					clearBuffers();
				}
			}
#else
			clearBuffers();
#endif
			setCacheEntry(true, i);
		}
		return 0;
	}
	return -1;
}

int eServiceMP3::getCurrentChannel() {
	return STEREO;
}

RESULT eServiceMP3::selectChannel(int i) {
	eDebug("[eServiceMP3] selectChannel(%i)", i);
	return 0;
}

/**
 * @brief Gets information about the specified audio track.
 *
 * This function retrieves information about the specified audio track, including
 * its description and language. It uses a map of replacements to format the
 * codec description and sets the language code accordingly.
 *
 * @param[out] info A reference to an iAudioTrackInfo structure that will hold the track information.
 * @param[in] i The index of the audio track to retrieve information for.
 * @return RESULT Returns 0 on success, or -2 if the index is out of bounds.
 */
RESULT eServiceMP3::getTrackInfo(struct iAudioTrackInfo& info, unsigned int i) {
	if (i >= m_audioStreams.size()) {
		return -2;
	}

	std::string desc = m_audioStreams[i].codec;

	std::map<std::string, std::string> audioReplacements = {
		{"AC-3", "AC3"},	 {"EAC3", "AC3+"},	  {"EAC-3", "AC3+"},	{"E-AC3", "AC3+"},
		{"E-AC-3", "AC3+"},	 {"-1 ", ""},		  {"-2 AAC", "AAC"},	{"-4 AAC", "AAC"},
		{"4-AAC", "HE-AAC"}, {"(ATSC A/52)", ""}, {"(ATSC A/52B)", ""}, {"MPEG", ""},
		{"Layer", ""},		 {" 2 ", ""},		  {"(MP2)", "AAC"},		{"audio", ""}};

	if (!desc.empty()) {
		for (auto const& x : audioReplacements) {
			std::string s = x.first;
			if (desc.length() >= s.length()) {
				size_t loc = desc.find(s);
				if (loc != std::string::npos) {
					desc.replace(loc, s.length(), x.second);
				}
			}
		}
	}

	info.m_description = desc;

	info.m_language = m_audioStreams[i].language_code;

	if (!info.m_language.empty())
		info.m_language += "/";

	if (!m_audioStreams[i].title.empty())
		info.m_language += m_audioStreams[i].title;

	// eDebug("[eServiceMP3] getTrackInfo (%d) - m_description=%s m_language=%s", i, info.m_description.c_str(),
	// info.m_language.c_str());

	return 0;
}

/**
 * @brief Gets the subtitle type based on the pad and codec.
 *
 * This function determines the subtitle type based on the GStreamer pad and
 * an optional codec string. It checks the current or allowed caps of the pad
 * and matches them against known subtitle types.
 *
 * @param[in] pad The GStreamer pad to check for subtitle type.
 * @param[in] g_codec An optional codec string to match against known subtitle types.
 * @return subtype_t Returns the identified subtitle type, or stUnknown if not identified.
 */
subtype_t getSubtitleType(GstPad* pad, gchar* g_codec = NULL) {
	subtype_t type = stUnknown;
	GstCaps* caps = gst_pad_get_current_caps(pad);
	if (!caps && !g_codec) {
		caps = gst_pad_get_allowed_caps(pad);
	}

	if (caps && !gst_caps_is_empty(caps)) {
		GstStructure* str = gst_caps_get_structure(caps, 0);
		if (str) {
			const gchar* g_type = gst_structure_get_name(str);
			// eDebug("[eServiceMP3] getSubtitleType::subtitle probe caps type=%s", g_type ? g_type : "(null)");
			if (g_type) {
				if (!strcmp(g_type, "subpicture/x-dvd"))
					type = stVOB;
				else if (!strcmp(g_type, "subpicture/x-dvb"))
					type = stDVB;
				else if (!strcmp(g_type, "text/x-pango-markup"))
					type = stSRT;
				else if (!strcmp(g_type, "text/plain") || !strcmp(g_type, "text/x-plain") ||
						 !strcmp(g_type, "text/x-raw"))
					type = stPlainText;
				else if (!strcmp(g_type, "subpicture/x-pgs"))
					type = stPGS;
				else if (!strcmp(g_type, "text/vtt") || !strcmp(g_type, "text/x-webvtt") ||
						 !strcmp(g_type, "application/x-subtitle-vtt"))
					type = stWebVTT;
				else
					eDebug("[eServiceMP3] getSubtitleType::unsupported subtitle caps %s (%s)", g_type,
						   g_codec ? g_codec : "(null)");
			}
		}
	} else if (g_codec) {
		// eDebug("[eServiceMP3] getSubtitleType::subtitle probe codec tag=%s", g_codec);
		if (!strcmp(g_codec, "VOB"))
			type = stVOB;
		else if (!strcmp(g_codec, "SubStation Alpha") || !strcmp(g_codec, "SSA"))
			type = stSSA;
		else if (!strcmp(g_codec, "ASS"))
			type = stASS;
		else if (!strcmp(g_codec, "SRT"))
			type = stSRT;
		else if (!strcmp(g_codec, "UTF-8 plain text"))
			type = stPlainText;
		else
			eDebug("[eServiceMP3] getSubtitleType::unsupported subtitle codec %s", g_codec);
	} else
		eDebug("[eServiceMP3] getSubtitleType::unidentifiable subtitle stream!");

	return type;
}

/**
 * @brief Handles GStreamer bus messages.
 *
 * This function processes GStreamer bus messages and handles various message types,
 * such as end-of-stream (EOS), state changes, and errors. It also manages the state
 * transitions of the playbin and emits events based on the received messages.
 *
 * @param[in] msg The GStreamer message to process.
 */
void eServiceMP3::gstBusCall(GstMessage* msg) {
	if (!msg)
		return;
	gchar* sourceName;
	GstObject* source;
	source = GST_MESSAGE_SRC(msg);
	if (!GST_IS_OBJECT(source))
		return;
	sourceName = gst_object_get_name(source);
	GstState state, pending, old_state, new_state;
	GstStateChangeReturn ret;
	GstStateChange transition;
#if 0
	gchar *string = NULL;
	if (gst_message_get_structure(msg))
		string = gst_structure_to_string(gst_message_get_structure(msg));
	else
		string = g_strdup(GST_MESSAGE_TYPE_NAME(msg));
	if (string)
	{
		eDebug("[eServiceMP3] eTsRemoteSource::gst_message from %s: %s", sourceName, string);
		g_free(string);
	}
#endif
	switch (GST_MESSAGE_TYPE(msg)) {
		case GST_MESSAGE_EOS:
			eDebug("[eServiceMP3] ** EOS RECEIVED **");
			m_event((iPlayableService*)this, evEOF);
			break;
		case GST_MESSAGE_STATE_CHANGED: {
			if (GST_MESSAGE_SRC(msg) != GST_OBJECT(m_gst_playbin))
				break;

			gst_message_parse_state_changed(msg, &old_state, &new_state, NULL);

			if (old_state == new_state)
				break;

			std::string s_old_state(gst_element_state_get_name(old_state));
			std::string s_new_state(gst_element_state_get_name(new_state));
			eDebug("[eServiceMP3] ****STATE TRANSITION %s -> %s ****", s_old_state.c_str(), s_new_state.c_str());

			if (m_gstdot) {
				std::string s_graph_filename = "GStreamer-enigma2." + s_old_state + "_" + s_new_state;
				GST_DEBUG_BIN_TO_DOT_FILE_WITH_TS(GST_BIN_CAST(m_gst_playbin), GST_DEBUG_GRAPH_SHOW_ALL,
												  s_graph_filename.c_str());
			}

			transition = (GstStateChange)GST_STATE_TRANSITION(old_state, new_state);

			switch (transition) {
				case GST_STATE_CHANGE_NULL_TO_READY: {
					m_first_paused = true;
					m_event(this, evGstreamerStart);
					if (m_send_ev_start)
						m_event(this, evStart);
					if (!m_is_live)
						gst_element_set_state(m_gst_playbin, GST_STATE_PAUSED);
					ret = gst_element_get_state(m_gst_playbin, &state, &pending, 5LL * GST_SECOND);
					eDebug("[eServiceMP3] PLAYBIN WITH BLOCK READY TO PAUSED state:%s pending:%s ret:%s",
						   gst_element_state_get_name(state), gst_element_state_get_name(pending),
						   gst_element_state_change_return_get_name(ret));
					if (ret == GST_STATE_CHANGE_NO_PREROLL) {
						gst_element_set_state(m_gst_playbin, GST_STATE_PLAYING);
						m_is_live = true;
					}
				} break;
				case GST_STATE_CHANGE_READY_TO_PAUSED: {
					m_state = stRunning;
					if (dvb_subsink) {
						/*
						 * FIX: Seems that subtitle sink have a delay of receiving subtitles buffer.
						 * So we move ahead the PTS of the subtitle sink by 2 seconds.
						 * Then we do aditional sync of subtitles if they arrive ahead of PTS
						 */
						g_object_set(dvb_subsink, "ts-offset", -2LL * GST_SECOND, NULL);

#ifdef GSTREAMER_SUBTITLE_SYNC_MODE_BUG
						/*
						 * HACK: disable sync mode for now, gstreamer suffers from a bug causing sparse streams to loose
						 * sync, after pause/resume / skip see: https://bugzilla.gnome.org/show_bug.cgi?id=619434
						 * Sideeffect of using sync=false is that we receive subtitle buffers (far) ahead of their
						 * display time.
						 * Not too far ahead for subtitles contained in the media container.
						 * But for external srt files, we could receive all subtitles at once.
						 * And not just once, but after each pause/resume / skip.
						 * So as soon as gstreamer has been fixed to keep sync in sparse streams, sync needs to be
						 * re-enabled.
						 */
						g_object_set(dvb_subsink, "sync", FALSE, NULL);
#endif

#if 0
						/* we should not use ts-offset to sync with the decoder time, we have to do our own decoder timekeeping */
						g_object_set (G_OBJECT (subsink), "ts-offset", -2LL * GST_SECOND, NULL);
						/* late buffers probably will not occur very often */
						g_object_set (G_OBJECT (subsink), "max-lateness", 0LL, NULL);
						/* avoid prerolling (it might not be a good idea to preroll a sparse stream) */
						g_object_set (G_OBJECT (subsink), "async", TRUE, NULL);
#endif
						// eDebug("[eServiceMP3] subsink properties set!");
					}

					setAC3Delay(ac3_delay);
					setPCMDelay(pcm_delay);
					if (!m_sourceinfo.is_streaming && !m_cuesheet_loaded) /* cuesheet CVR */
						loadCuesheet();
					/* avoid position taking on audiosink when audiosink is not running */
					ret = gst_element_get_state(dvb_audiosink, &state, &pending, 3 * GST_SECOND);
					if (state == GST_STATE_NULL)
						m_audiosink_not_running = true;
					if (!m_is_live)
						gst_element_set_state(m_gst_playbin, GST_STATE_PLAYING);
					/* tempo debug */
					/* wait on async state change complete for max 5 seconds */
					ret = gst_element_get_state(m_gst_playbin, &state, &pending, 3 * GST_SECOND);
					eDebug("[eServiceMP3] PLAYBIN WITH BLOCK PLAYSTART state:%s pending:%s ret:%s",
						   gst_element_state_get_name(state), gst_element_state_get_name(pending),
						   gst_element_state_change_return_get_name(ret));
					if (!m_is_live && ret == GST_STATE_CHANGE_NO_PREROLL)
						m_is_live = true;
					m_event((iPlayableService*)this, evGstreamerPlayStarted);
					updateEpgCacheNowNext();

					if (!dvb_videosink || m_ref.getData(0) == 2) // show radio pic
					{
						bool showRadioBackground = eSimpleConfig::getBool("config.misc.showradiopic", true);
						std::string radio_pic = eConfigManager::getConfigValue(
							showRadioBackground ? "config.misc.radiopic" : "config.misc.blackradiopic");
						m_decoder = new eTSMPEGDecoder(NULL, 0);
						m_decoder->showSinglePic(radio_pic.c_str());
					}

				} break;
				case GST_STATE_CHANGE_PAUSED_TO_PLAYING: {
					m_paused = false;
					if (m_currentAudioStream < 0) {
						unsigned int autoaudio = 0;
						int autoaudio_level = 5;
						std::string configvalue;
						std::vector<std::string> autoaudio_languages;
						configvalue = eSettings::audio_autoselect1;
						if (configvalue != "")
							autoaudio_languages.push_back(configvalue);
						configvalue = eSettings::audio_autoselect2;
						if (configvalue != "")
							autoaudio_languages.push_back(configvalue);
						configvalue = eSettings::audio_autoselect3;
						if (configvalue != "")
							autoaudio_languages.push_back(configvalue);
						configvalue = eSettings::audio_autoselect4;
						if (configvalue != "")
							autoaudio_languages.push_back(configvalue);

						for (unsigned int i = 0; i < m_audioStreams.size(); i++) {
							if (!m_audioStreams[i].language_code.empty()) {
								int x = 1;
								for (std::vector<std::string>::iterator it = autoaudio_languages.begin();
									 x < autoaudio_level && it != autoaudio_languages.end(); x++, it++) {
									if ((*it).find(m_audioStreams[i].language_code) != std::string::npos) {
										autoaudio = i;
										autoaudio_level = x;
										break;
									}
								}
							}
						}

						if (autoaudio)
							selectAudioStream(autoaudio);
					} else {
						selectAudioStream(m_currentAudioStream);
					}
					m_clear_buffers = false;
					if (!m_initial_start) {
						if (!m_sourceinfo.is_streaming)
							seekTo(0);
						m_initial_start = true;
					}
					if (!m_first_paused)
						m_event((iPlayableService*)this, evGstreamerPlayStarted);
					m_first_paused = false;
				} break;
				case GST_STATE_CHANGE_PLAYING_TO_PAUSED: {
					m_paused = true;
				} break;
				case GST_STATE_CHANGE_PAUSED_TO_READY:
				case GST_STATE_CHANGE_READY_TO_NULL:
				case GST_STATE_CHANGE_NULL_TO_NULL:
				case GST_STATE_CHANGE_READY_TO_READY:
				case GST_STATE_CHANGE_PAUSED_TO_PAUSED:
				case GST_STATE_CHANGE_PLAYING_TO_PLAYING:
					break;
			}
			break;
		}
		case GST_MESSAGE_ERROR: {
			gchar* debug;
			GError* err;
			gst_message_parse_error(msg, &err, &debug);
			g_free(debug);
			eWarning("Gstreamer error: %s (%i, %i) from %s", err->message, err->code, err->domain, sourceName);
			if (err->domain == GST_STREAM_ERROR) {
				if (err->code == GST_STREAM_ERROR_CODEC_NOT_FOUND) {
					if (g_strrstr(sourceName, "videosink"))
						m_event((iPlayableService*)this, evUser + 11);
					else if (g_strrstr(sourceName, "audiosink"))
						m_event((iPlayableService*)this, evUser + 10);
				}
			} else if (err->domain == GST_RESOURCE_ERROR) {
				if (err->code == GST_RESOURCE_ERROR_OPEN_READ || err->code == GST_RESOURCE_ERROR_READ) {
					stop();
				}
			}
			g_error_free(err);
			break;
		}
		case GST_MESSAGE_WARNING: {
			gchar* debug_warn = NULL;
			GError* warn = NULL;
			gst_message_parse_warning(msg, &warn, &debug_warn);
			/* CVR this Warning occurs from time to time with external srt files
			When a new seek is done the problem off to long wait times before subtitles appears,
			after movie was restarted with a resume position is solved. */
			if (!strncmp(warn->message, "Internal data flow problem", 26) &&
				!strncmp(sourceName, "subtitle_sink", 13)) {
				eWarning("[eServiceMP3] Gstreamer warning : %s (%i) from %s", warn->message, warn->code, sourceName);
				if (dvb_subsink) {
					if (!gst_element_seek(dvb_subsink, m_currentTrickRatio, GST_FORMAT_TIME,
										  (GstSeekFlags)(GST_SEEK_FLAG_FLUSH | GST_SEEK_FLAG_ACCURATE),
										  GST_SEEK_TYPE_SET, (gint64)(m_last_seek_pos * 11111LL), GST_SEEK_TYPE_NONE,
										  GST_CLOCK_TIME_NONE)) {
						eDebug("[eServiceMP3] seekToImpl subsink failed");
					}
				}
			}
			g_free(debug_warn);
			g_error_free(warn);
			break;
		}
		case GST_MESSAGE_INFO: {
			gchar* debug;
			GError* inf;

			gst_message_parse_info(msg, &inf, &debug);
			g_free(debug);
			if (inf->domain == GST_STREAM_ERROR && inf->code == GST_STREAM_ERROR_DECODE) {
				if (g_strrstr(sourceName, "videosink"))
					m_event((iPlayableService*)this, evUser + 14);
			}
			g_error_free(inf);
			break;
		}
		case GST_MESSAGE_TAG: {
			GstTagList *tags, *result;
			gst_message_parse_tag(msg, &tags);

			result = gst_tag_list_merge(m_stream_tags, tags, GST_TAG_MERGE_REPLACE);
			if (result) {
				if (m_stream_tags && gst_tag_list_is_equal(m_stream_tags, result)) {
					gst_tag_list_free(tags);
					gst_tag_list_free(result);
					break;
				}
				if (m_stream_tags)
					gst_tag_list_free(m_stream_tags);
				m_stream_tags = result;
			}

			if (!m_coverart) {
				const GValue* gv_image = gst_tag_list_get_value_index(tags, GST_TAG_IMAGE, 0);
				if (gv_image) {
					GstBuffer* buf_image;
					GstSample* sample;
					sample = (GstSample*)g_value_get_boxed(gv_image);
					buf_image = gst_sample_get_buffer(sample);
					int fd = open("/tmp/.id3coverart", O_CREAT | O_WRONLY | O_TRUNC, 0644);
					if (fd >= 0) {
						guint8* data;
						gsize size;
						GstMapInfo map;
						gst_buffer_map(buf_image, &map, GST_MAP_READ);
						data = map.data;
						size = map.size;
						int ret = write(fd, data, size);
						gst_buffer_unmap(buf_image, &map);
						close(fd);
						m_coverart = true;
						m_event((iPlayableService*)this, evUpdateIDv3Cover);
						eDebug("[eServiceMP3] /tmp/.id3coverart %d bytes written ", ret);
					}
				}
			}
			gst_tag_list_free(tags);
			m_event((iPlayableService*)this, evUpdateTags);
			break;
		}
		/* TOC entry intercept used for chapter support CVR */
		case GST_MESSAGE_TOC: {
			if (!m_sourceinfo.is_audio && !m_sourceinfo.is_streaming)
				HandleTocEntry(msg);
			break;
		}
		case GST_MESSAGE_ASYNC_DONE: {
			if (GST_MESSAGE_SRC(msg) != GST_OBJECT(m_gst_playbin))
				break;

			if (m_send_ev_start) {
				gint i, n_video = 0, n_audio = 0, n_text = 0;
				// bool codec_tofix = false;

				g_object_get(m_gst_playbin, "n-video", &n_video, NULL);
				g_object_get(m_gst_playbin, "n-audio", &n_audio, NULL);
				g_object_get(m_gst_playbin, "n-text", &n_text, NULL);

				// eDebug("[eServiceMP3] async-done - %d video, %d audio, %d subtitle", n_video, n_audio, n_text);

				if (n_video + n_audio <= 0)
					stop();

				std::vector<audioStream> audioStreams_temp;
				std::vector<subtitleStream> subtitleStreams_temp;

				std::vector<audioMeta> audiometa;
				if (m_sourceinfo.is_hls)
					audiometa = parse_hls_audio_meta("/tmp/gsthlsaudiometa.info");

				for (i = 0; i < n_audio; i++) {
					audioStream audio = {};
					gchar *g_codec, *g_lang;
					GstTagList* tags = NULL;
					GstPad* pad = 0;
					g_signal_emit_by_name(m_gst_playbin, "get-audio-pad", i, &pad);
					GstCaps* caps = gst_pad_get_current_caps(pad);
					gst_object_unref(pad);
					if (!caps)
						continue;
					GstStructure* str = gst_caps_get_structure(caps, 0);
					const gchar* g_type = gst_structure_get_name(str);
					// eDebug("[eServiceMP3] AUDIO STRUCT=%s", g_type);
					audio.type = gstCheckAudioPad(str);
					audio.language_code = "und";
					audio.codec = g_type;
					g_codec = NULL;
					g_lang = NULL;
					g_signal_emit_by_name(m_gst_playbin, "get-audio-tags", i, &tags);
					if (tags && GST_IS_TAG_LIST(tags)) {
						if (gst_tag_list_get_string(tags, GST_TAG_AUDIO_CODEC, &g_codec)) {
							audio.codec = std::string(g_codec);
							g_free(g_codec);
						}
						if (gst_tag_list_get_string(tags, GST_TAG_LANGUAGE_CODE, &g_lang)) {
							audio.language_code = std::string(g_lang);
							g_free(g_lang);
						}
						gst_tag_list_free(tags);
					}
					if ((int)audiometa.size() > i) {
						if (!audiometa[i].lang.empty())
							audio.language_code = audiometa[i].lang;
						if (!audiometa[i].title.empty())
							audio.title = audiometa[i].title;
					}
					// eDebug("[eServiceMP3] audio stream=%i codec=%s language=%s", i, audio.codec.c_str(),
					// audio.language_code.c_str()); codec_tofix = (audio.codec.find("MPEG-1 Layer 3 (MP3)") == 0 ||
					// audio.codec.find("MPEG-2 AAC") == 0) && n_audio - n_video == 1;
					audioStreams_temp.push_back(audio);
					gst_caps_unref(caps);
				}

				for (i = 0; i < n_text; i++) {
					gchar *g_codec = NULL, *g_lang = NULL, *g_lang_title = NULL;
					GstTagList* tags = NULL;
					g_signal_emit_by_name(m_gst_playbin, "get-text-tags", i, &tags);
					subtitleStream subs;
					subs.language_code = "und";
					subs.title = "";
					if (tags && GST_IS_TAG_LIST(tags)) {
						if (gst_tag_list_get_string(tags, GST_TAG_LANGUAGE_CODE, &g_lang)) {
							subs.language_code = g_lang;
							g_free(g_lang);
						}
						if (gst_tag_list_get_string(tags, GST_TAG_TITLE, &g_lang_title)) {
							subs.title = g_lang_title;
							g_free(g_lang_title);
						}
						gst_tag_list_get_string(tags, GST_TAG_SUBTITLE_CODEC, &g_codec);
						gst_tag_list_free(tags);
					}

					// eDebug("[eServiceMP3] subtitle stream=%i language=%s codec=%s", i, subs.language_code.c_str(),
					// g_codec ? g_codec : "(null)");

					GstPad* pad = 0;
					g_signal_emit_by_name(m_gst_playbin, "get-text-pad", i, &pad);
					if (pad) {
						g_signal_connect(G_OBJECT(pad), "notify::caps", G_CALLBACK(gstTextpadHasCAPS), this);
						GstCaps* caps = gst_pad_get_current_caps(pad);
						// eDebug("[eServiceMP3] subtitle Text pad %d caps: %s", i, gst_caps_to_string (caps));
						gst_caps_unref(caps);

						subs.type = getSubtitleType(pad, g_codec);

						if (i == 0 && !m_external_subtitle_extension.empty()) {
							if (m_external_subtitle_extension == "srt")
								subs.type = stSRT;
							if (m_external_subtitle_extension == "ass")
								subs.type = stASS;
							if (m_external_subtitle_extension == "ssa")
								subs.type = stSSA;
							if (m_external_subtitle_extension == "vtt")
								subs.type = stWebVTT;
							if (!m_external_subtitle_language.empty())
								subs.language_code = m_external_subtitle_language;
						}

						gst_object_unref(pad);
					}
					g_free(g_codec);
					subtitleStreams_temp.push_back(subs);
				}

				bool hasChanges = m_audioStreams.size() != audioStreams_temp.size() ||
								  std::equal(m_audioStreams.begin(), m_audioStreams.end(), audioStreams_temp.begin());
				if (!hasChanges)
					hasChanges =
						m_subtitleStreams.size() != subtitleStreams_temp.size() ||
						std::equal(m_subtitleStreams.begin(), m_subtitleStreams.end(), subtitleStreams_temp.begin());

				if (hasChanges) {
					eTrace("[eServiceMP3] audio or subtitle stream difference -- re enumerating");
					m_audioStreams.clear();
					m_subtitleStreams.clear();
					std::copy(audioStreams_temp.begin(), audioStreams_temp.end(), back_inserter(m_audioStreams));
					std::copy(subtitleStreams_temp.begin(), subtitleStreams_temp.end(),
							  back_inserter(m_subtitleStreams));
					eDebug("[eServiceMP3] GST_MESSAGE_ASYNC_DONE before evUpdatedInfo");
					m_event((iPlayableService*)this, evUpdatedInfo);
				}
			} else {
				m_send_ev_start = true;
			}

			if (m_errorInfo.missing_codec != "") {
				if (m_errorInfo.missing_codec.find("video/") == 0 ||
					(m_errorInfo.missing_codec.find("audio/") == 0 && m_audioStreams.empty()))
					m_event((iPlayableService*)this, evUser + 12);
			}
			/*+++*workaround for mp3 playback problem on some boxes - e.g. xtrend et9200 (if press stop and play or
			switch to the next track is the state 'playing', but plays not. Restart the player-application or paused and
			then play the track fix this for once.)*/
			/*if (!m_paused && codec_tofix)
			{
				std::string filename = "/proc/stb/info/boxtype";
				FILE *f = fopen(filename.c_str(), "rb");
				if (f)
				{
					char boxtype[6];
					fread(boxtype, 6, 1, f);
					fclose(f);
					if (!memcmp(boxtype, "et5000", 6) || !memcmp(boxtype, "et6000", 6) || !memcmp(boxtype, "et6500", 6)
			|| !memcmp(boxtype, "et9000", 6) || !memcmp(boxtype, "et9100", 6) || !memcmp(boxtype, "et9200", 6) ||
			!memcmp(boxtype, "et9500", 6))
					{
						eDebug("[eServiceMP3] mp3,aac playback fix for xtrend et5x00,et6x00,et9x00 - set paused and then
			playing state"); GstStateChangeReturn ret; ret = gst_element_set_state (m_gst_playbin, GST_STATE_PAUSED); if
			(ret != GST_STATE_CHANGE_SUCCESS)
						{
							eDebug("[eServiceMP3] mp3 playback fix - failure set paused state - sleep one second before
			set playing state"); sleep(1);
						}
						gst_element_set_state (m_gst_playbin, GST_STATE_PLAYING);
					}
				}
			}*/
			/*+++*/
			break;
		}
		case GST_MESSAGE_ELEMENT: {
			const GstStructure* msgstruct = gst_message_get_structure(msg);
			if (msgstruct) {
				if (gst_is_missing_plugin_message(msg)) {
					GstCaps* caps = NULL;
					gst_structure_get(msgstruct, "detail", GST_TYPE_CAPS, &caps, NULL);
					if (caps) {
						std::string codec = (const char*)gst_caps_to_string(caps);
						gchar* description = gst_missing_plugin_message_get_description(msg);
						if (description) {
							eDebug("[eServiceMP3] m_errorInfo.missing_codec = %s", codec.c_str());
							m_errorInfo.error_message =
								"GStreamer plugin " + (std::string)description + " not available!\n";
							m_errorInfo.missing_codec = codec.substr(0, (codec.find_first_of(',')));
							g_free(description);
						}
						gst_caps_unref(caps);
					}
				} else {
					const gchar* eventname = gst_structure_get_name(msgstruct);
					if (eventname) {
						if (!strcmp(eventname, "eventSizeChanged") || !strcmp(eventname, "eventSizeAvail")) {
							gst_structure_get_int(msgstruct, "aspect_ratio", &m_aspect);
							gst_structure_get_int(msgstruct, "width", &m_width);
							gst_structure_get_int(msgstruct, "height", &m_height);
							if (strstr(eventname, "Changed"))
								m_event((iPlayableService*)this, evVideoSizeChanged);
						} else if (!strcmp(eventname, "eventFrameRateChanged") ||
								   !strcmp(eventname, "eventFrameRateAvail")) {
							gst_structure_get_int(msgstruct, "frame_rate", &m_framerate);
							if (strstr(eventname, "Changed"))
								m_event((iPlayableService*)this, evVideoFramerateChanged);
						} else if (!strcmp(eventname, "eventProgressiveChanged") ||
								   !strcmp(eventname, "eventProgressiveAvail")) {
							gst_structure_get_int(msgstruct, "progressive", &m_progressive);
							if (strstr(eventname, "Changed"))
								m_event((iPlayableService*)this, evVideoProgressiveChanged);
						} else if (!strcmp(eventname, "eventGammaChanged")) {
							gst_structure_get_int(msgstruct, "gamma", &m_gamma);
							if (strstr(eventname, "Changed"))
								m_event((iPlayableService*)this, evVideoGammaChanged);
						} else if (!strcmp(eventname, "redirect")) {
							const char* uri = gst_structure_get_string(msgstruct, "new-location");
							// eDebug("[eServiceMP3] redirect to %s", uri);
							gst_element_set_state(m_gst_playbin, GST_STATE_NULL);
							g_object_set(m_gst_playbin, "uri", uri, NULL);
							gst_element_set_state(m_gst_playbin, GST_STATE_PLAYING);
						}
					}
				}
			}
			break;
		}
		case GST_MESSAGE_BUFFERING:
			if (m_sourceinfo.is_streaming) {
				// GstBufferingMode mode;
				gst_message_parse_buffering(msg, &(m_bufferInfo.bufferPercent));
				// eDebug("[eServiceMP3] Buffering %u percent done", m_bufferInfo.bufferPercent);
				// gst_message_parse_buffering_stats(msg, &mode, &(m_bufferInfo.avgInRate), &(m_bufferInfo.avgOutRate),
				// &(m_bufferInfo.bufferingLeft)); m_event((iPlayableService*)this, evBuffering);
				/*
				 * we don't react to buffer level messages, unless we are configured to use a prefill buffer
				 * (even if we are not configured to, we still use the buffer, but we rely on it to remain at the
				 * healthy level at all times, without ever having to pause the stream)
				 *
				 * Also, it does not make sense to pause the stream if it is a live stream
				 * (in which case the sink will not produce data while paused, so we won't
				 * recover from an empty buffer)
				 */
				if (m_use_prefillbuffer && !m_is_live && !m_sourceinfo.is_hls && --m_ignore_buffering_messages <= 0) {
					if (m_bufferInfo.bufferPercent == 100) {
						GstState state, pending;
						/* avoid setting to play while still in async state change mode */
						gst_element_get_state(m_gst_playbin, &state, &pending, 5 * GST_SECOND);
						if (state != GST_STATE_PLAYING && !m_first_paused) {
							eDebug("[eServiceMP3] *** PREFILL BUFFER action start playing *** pending state was %s",
								   pending == GST_STATE_VOID_PENDING ? "NO_PENDING" : "A_PENDING_STATE");
							gst_element_set_state(m_gst_playbin, GST_STATE_PLAYING);
						}
						/*
						 * when we start the pipeline, the contents of the buffer will immediately drain
						 * into the (hardware buffers of the) sinks, so we will receive low buffer level
						 * messages right away.
						 * Ignore the first few buffering messages, giving the buffer the chance to recover
						 * a bit, before we start handling empty buffer states again.
						 */
						m_ignore_buffering_messages = 10;
					} else if (m_bufferInfo.bufferPercent == 0 && !m_first_paused) {
						eDebug("[eServiceMP3] *** PREFILLBUFFER action start pause ***");
						gst_element_set_state(m_gst_playbin, GST_STATE_PAUSED);
						m_ignore_buffering_messages = 0;
					} else {
						m_ignore_buffering_messages = 0;
					}
				}
			}
			break;
		default:
			break;
	}
	g_free(sourceName);
}

/**
 * @brief Handles GStreamer bus messages.
 *
 * This function processes GStreamer bus messages and handles various message types,
 * such as state changes, end-of-stream (EOS), and errors. It sends the messages to
 * a message pump for further processing.
 *
 * @param[in] msg The GStreamer message to process.
 */
void eServiceMP3::handleMessage(GstMessage* msg) {
	if (GST_MESSAGE_TYPE(msg) == GST_MESSAGE_STATE_CHANGED && GST_MESSAGE_SRC(msg) != GST_OBJECT(m_gst_playbin)) {
		/*
		 * ignore verbose state change messages for all active elements;
		 * we only need to handle state-change events for the playbin
		 */
		gst_message_unref(msg);
		return;
	}
	m_pump.send(new GstMessageContainer(1, msg, NULL, NULL));
}

/**
 * @brief GStreamer bus sync handler.
 *
 * This function is called when a GStreamer bus message is received. It processes the
 * message and calls the handleMessage function to handle it.
 *
 * @param[in] bus The GStreamer bus.
 * @param[in] message The GStreamer message to process.
 * @param[in] user_data User data passed to the handler.
 * @return GST_BUS_DROP to drop the message after processing.
 */
GstBusSyncReply eServiceMP3::gstBusSyncHandler(GstBus* bus, GstMessage* message, gpointer user_data) {
	eServiceMP3* _this = (eServiceMP3*)user_data;
	if (_this)
		_this->handleMessage(message);
	return GST_BUS_DROP;
}


/**
 * @brief Handles TOC entries from GStreamer messages.
 *
 * This function processes TOC entries from GStreamer messages, specifically for
 * video media. It extracts chapter information and updates the cue entries.
 *
 * @param[in] msg The GStreamer message containing TOC entries.
 */
void eServiceMP3::HandleTocEntry(GstMessage* msg) {
	/* limit TOC to dvbvideosink cue sheet only works for video media */
	if (!strncmp(GST_MESSAGE_SRC_NAME(msg), "dvbvideosink", 12)) {
		GstToc* toc;
		gboolean updated;
		gst_message_parse_toc(msg, &toc, &updated);
		for (GList* i = gst_toc_get_entries(toc); i; i = i->next) {
			GstTocEntry* entry = static_cast<GstTocEntry*>(i->data);
			if (gst_toc_entry_get_entry_type(entry) == GST_TOC_ENTRY_TYPE_EDITION &&
				eSimpleConfig::getBool("config.usage.useChapterInfo", true)) {
				/* extra debug info for testing purposes should_be_removed later on */
				// eDebug("[eServiceMP3] toc_type %s", gst_toc_entry_type_get_nick(gst_toc_entry_get_entry_type
				// (entry)));
				gint y = 0;
				for (GList* x = gst_toc_entry_get_sub_entries(entry); x; x = x->next) {
					GstTocEntry* sub_entry = static_cast<GstTocEntry*>(x->data);
					if (gst_toc_entry_get_entry_type(sub_entry) == GST_TOC_ENTRY_TYPE_CHAPTER) {
						if (y == 0) {
							m_use_chapter_entries = true;
							if (!m_cuesheet_loaded)
								loadCuesheet();
						}
						/* first chapter is movie start no cut needed */
						else if (y >= 1) {
							gint64 start = 0;
							gint64 pts = 0;
							guint type = 0;
							gst_toc_entry_get_start_stop_times(sub_entry, &start, NULL);
							type = 2;
							if (start > 0)
								pts = start / 11111;
							if (pts > 0) {
								/* check cue and toc for identical entries */
								bool tocadd = true;
								for (std::multiset<cueEntry>::iterator i(m_cue_entries.begin());
									 i != m_cue_entries.end(); ++i) {
									/* toc not add if cue available */
									if (pts == i->where && type == i->what) {
										tocadd = false;
										break;
									}
								}
								if (tocadd) {
									m_cue_entries.insert(cueEntry(pts, type));
								}
								m_cuesheet_changed = 1;
								m_event((iPlayableService*)this, evCuesheetChanged);
								/* extra debug info for testing purposes should_be_removed later on */
								/*eDebug("[eServiceMP3] toc_subtype %s,Nr = %d, start= %#"G_GINT64_MODIFIER "x",
										gst_toc_entry_type_get_nick(gst_toc_entry_get_entry_type (sub_entry)), y + 1,
								   pts); */
							}
						}
						y++;
					}
				}
			}
		}
		// eDebug("[eServiceMP3] TOC entry from source %s processed", GST_MESSAGE_SRC_NAME(msg));
	} else {
		// eDebug("[eServiceMP3] TOC entry from source %s not used", GST_MESSAGE_SRC_NAME(msg));
		;
	}
}

/**
 * @brief Callback function to notify when the source of the playbin changes.
 *
 * This function is called when the "source" property of the playbin changes.
 * It sets various properties on the source element, such as timeout, retries,
 * SSL strictness, user-agent, and extra headers.
 *
 * @param[in] object The GObject that emitted the signal.
 * @param[in] unused Unused parameter (not used in this implementation).
 * @param[in] user_data User data passed to the callback (eServiceMP3 instance).
 */
void eServiceMP3::playbinNotifySource(GObject* object, GParamSpec* unused, gpointer user_data) {
	GstElement* source = NULL;
	eServiceMP3* _this = (eServiceMP3*)user_data;
	g_object_get(object, "source", &source, NULL);
	if (source) {
		if (g_object_class_find_property(G_OBJECT_GET_CLASS(source), "timeout") != 0) {
			GstElementFactory* factory = gst_element_get_factory(source);
			if (factory) {
				const gchar* sourcename = gst_plugin_feature_get_name(GST_PLUGIN_FEATURE(factory));
				if (!strcmp(sourcename, "souphttpsrc")) {
					g_object_set(G_OBJECT(source), "timeout", HTTP_TIMEOUT, NULL);
					g_object_set(G_OBJECT(source), "retries", 20, NULL);
				}
			}
		}
		if (g_object_class_find_property(G_OBJECT_GET_CLASS(source), "ssl-strict") != 0) {
			g_object_set(G_OBJECT(source), "ssl-strict", FALSE, NULL);
		}
		if (g_object_class_find_property(G_OBJECT_GET_CLASS(source), "user-agent") != 0 &&
			!_this->m_useragent.empty()) {
			g_object_set(G_OBJECT(source), "user-agent", _this->m_useragent.c_str(), NULL);
		}
		if (g_object_class_find_property(G_OBJECT_GET_CLASS(source), "extra-headers") != 0 &&
			!_this->m_extra_headers.empty()) {
			GstStructure* extras = gst_structure_new_empty("extras");
			size_t pos = 0;
			while (pos != std::string::npos) {
				std::string name, value;
				size_t start = pos;
				size_t len = std::string::npos;
				pos = _this->m_extra_headers.find('=', pos);
				if (pos != std::string::npos) {
					len = pos - start;
					pos++;
					name = _this->m_extra_headers.substr(start, len);
					start = pos;
					len = std::string::npos;
					pos = _this->m_extra_headers.find('&', pos);
					if (pos != std::string::npos) {
						len = pos - start;
						pos++;
					}
					value = _this->m_extra_headers.substr(start, len);
				}
				if (!name.empty() && !value.empty()) {
					GValue header;
					// eDebug("[eServiceMP3] setting extra-header '%s:%s'", name.c_str(), value.c_str());
					memset(&header, 0, sizeof(GValue));
					g_value_init(&header, G_TYPE_STRING);
					g_value_set_string(&header, value.c_str());
					gst_structure_set_value(extras, name.c_str(), &header);
				} else {
					eDebug("[eServiceMP3] Invalid header format %s", _this->m_extra_headers.c_str());
					break;
				}
			}
			if (gst_structure_n_fields(extras) > 0) {
				g_object_set(G_OBJECT(source), "extra-headers", extras, NULL);
			}
			gst_structure_free(extras);
		}
		gst_object_unref(source);
	}
}

/**
 * @brief Callback function to handle the addition of elements to a GStreamer bin.
 *
 * This function is called when an element is added to a GStreamer bin. It checks if the
 * element is a queue2 element and sets its "temp-template" property based on the
 * download buffer path. It also connects to the "element-added" signal for uridecodebin
 * or decodebin elements to handle queue2 elements added there.
 *
 * @param[in] bin The GStreamer bin where the element was added.
 * @param[in] element The GStreamer element that was added.
 * @param[in] user_data User data passed to the callback (eServiceMP3 instance).
 */
void eServiceMP3::handleElementAdded(GstBin* bin, GstElement* element, gpointer user_data) {
	eServiceMP3* _this = (eServiceMP3*)user_data;
	if (_this) {
		gchar* elementname = gst_element_get_name(element);

		if (g_str_has_prefix(elementname, "queue2")) {
			if (_this->m_download_buffer_path != "") {
				g_object_set(G_OBJECT(element), "temp-template", _this->m_download_buffer_path.c_str(), NULL);
			} else {
				g_object_set(G_OBJECT(element), "temp-template", NULL, NULL);
			}
		} else if (g_str_has_prefix(elementname, "uridecodebin") || g_str_has_prefix(elementname, "decodebin")) {
			/*
			 * Listen for queue2 element added to uridecodebin/decodebin2 as well.
			 * Ignore other bins since they may have unrelated queues
			 */
			g_signal_connect(element, "element-added", G_CALLBACK(handleElementAdded), user_data);
		}
		g_free(elementname);
	}
}

/**
 * @brief Checks the audio pad structure to determine the audio type.
 *
 * This function checks the given GstStructure to determine the audio type
 * based on the codec information present in the structure.
 *
 * @param[in] structure The GstStructure to check.
 * @return The detected audio type as an audiotype_t enum value.
 */
audiotype_t eServiceMP3::gstCheckAudioPad(GstStructure* structure) {
	if (!structure)
		return atUnknown;

	if (gst_structure_has_name(structure, "audio/mpeg")) {
		gint mpegversion, layer = -1;
		if (!gst_structure_get_int(structure, "mpegversion", &mpegversion))
			return atUnknown;

		switch (mpegversion) {
			case 1: {
				gst_structure_get_int(structure, "layer", &layer);
				return (layer == 3) ? atMP3 : atMPEG;
			}
			case 2:
				return atAAC;
			case 4:
				return atAAC;
			default:
				return atUnknown;
		}
	}

	else if (gst_structure_has_name(structure, "audio/x-ac3") || gst_structure_has_name(structure, "audio/ac3"))
		return atAC3;
	else if (gst_structure_has_name(structure, "audio/x-eac3") || gst_structure_has_name(structure, "audio/eac3") ||
			 gst_structure_has_name(structure, "audio/x-true-hd") || gst_structure_has_name(structure, "audio/xTrueHD"))
		return atEAC3;
	else if (gst_structure_has_name(structure, "audio/x-dts") || gst_structure_has_name(structure, "audio/dts"))
		return atDTS;

	return atPCM;
}

/**
 * @brief Polls the message pump for GStreamer messages.
 *
 * This function processes messages from the message pump and handles different
 * types of messages, such as GstMessageContainer, GstBuffer, and GstPad.
 *
 * @param[in] msg The GStreamer message to process.
 */
void eServiceMP3::gstPoll(ePtr<GstMessageContainer> const& msg) {
	switch (msg->getType()) {
		case 1: {
			GstMessage* gstmessage = *((GstMessageContainer*)msg);
			if (gstmessage) {
				gstBusCall(gstmessage);
			}
			break;
		}
		case 2: {
			GstBuffer* buffer = *((GstMessageContainer*)msg);
			if (buffer) {
				pullSubtitle(buffer);
			}
			break;
		}
		case 3: {
			GstPad* pad = *((GstMessageContainer*)msg);
			gstTextpadHasCAPS_synced(pad);
			break;
		}
	}
}

/**
 * @brief Initializes the eServiceFactoryMP3 class.
 *
 * This function initializes the eServiceFactoryMP3 class, which is responsible for
 * creating instances of eServiceMP3. It sets the service number and name for the factory.
 */
eAutoInitPtr<eServiceFactoryMP3> init_eServiceFactoryMP3(eAutoInitNumbers::service + 1, "eServiceFactoryMP3");

/**
 * @brief Callback function to handle subtitle availability.
 *
 * This function is called when subtitles are available in the GstElement subsink.
 * It sends the subtitle buffer to the message pump for further processing.
 *
 * @param[in] subsink The GstElement that provides subtitles.
 * @param[in] buffer The GstBuffer containing the subtitle data.
 * @param[in] user_data User data passed to the callback (eServiceMP3 instance).
 */
void eServiceMP3::gstCBsubtitleAvail(GstElement* subsink, GstBuffer* buffer, gpointer user_data) {
	eServiceMP3* _this = (eServiceMP3*)user_data;
	if (!_this || !buffer || !_this->m_subtitle_widget || _this->m_currentSubtitleStream < 0) {
		if (buffer)
			gst_buffer_unref(buffer);
		return;
	}

	// Check array bounds
	if (_this->m_currentSubtitleStream >= (int)_this->m_subtitleStreams.size()) {
		if (buffer)
			gst_buffer_unref(buffer);
		return;
	}

	_this->m_pump.send(new GstMessageContainer(2, NULL, NULL, buffer));
}

/**
 * @brief Callback function to handle CAPS availability on a GstPad.
 *
 * This function is called when CAPS are available on a GstPad. It sends the pad
 * to the message pump for further processing.
 *
 * @param[in] pad The GstPad that has CAPS available.
 * @param[in] unused Unused parameter (not used in this implementation).
 * @param[in] user_data User data passed to the callback (eServiceMP3 instance).
 */
void eServiceMP3::gstTextpadHasCAPS(GstPad* pad, GParamSpec* unused, gpointer user_data) {
	eServiceMP3* _this = (eServiceMP3*)user_data;

	gst_object_ref(pad);

	_this->m_pump.send(new GstMessageContainer(3, NULL, pad, NULL));
}

/**
 * @brief Callback function to handle CAPS availability on a GstPad, synchronized.
 *
 * This function is called when CAPS are available on a GstPad. It retrieves the
 * CAPS and processes them to update subtitle streams.
 *
 * @param[in] pad The GstPad that has CAPS available.
 */
void eServiceMP3::gstTextpadHasCAPS_synced(GstPad* pad) {
	GstCaps* caps = NULL;

	g_object_get(G_OBJECT(pad), "caps", &caps, NULL);

	if (caps) {
		subtitleStream subs;

		//		eDebug("[eServiceMP3] gstTextpadHasCAPS:: signal::caps = %s", gst_caps_to_string(caps));
		//		eDebug("[eServiceMP3] gstGhostpadHasCAPS_synced %p %d", pad, m_subtitleStreams.size());

		if (m_currentSubtitleStream >= 0 && m_currentSubtitleStream < (int)m_subtitleStreams.size())
			subs = m_subtitleStreams[m_currentSubtitleStream];
		else {
			subs.type = stUnknown;
			subs.pad = pad;
		}

		if (subs.type == stUnknown) {
			GstTagList* tags = NULL;
			gchar *g_lang = NULL, *g_lang_title = NULL;
			g_signal_emit_by_name(m_gst_playbin, "get-text-tags", m_currentSubtitleStream, &tags);

			subs.language_code = "und";
			subs.type = getSubtitleType(pad);
			if (tags && GST_IS_TAG_LIST(tags)) {
				if (gst_tag_list_get_string(tags, GST_TAG_LANGUAGE_CODE, &g_lang)) {
					subs.language_code = std::string(g_lang);
					g_free(g_lang);
				}
				if (gst_tag_list_get_string(tags, GST_TAG_TITLE, &g_lang_title)) {
					subs.title = g_lang_title;
					g_free(g_lang_title);
				}
				gst_tag_list_free(tags);
			}

			if (m_currentSubtitleStream >= 0 && m_currentSubtitleStream < (int)m_subtitleStreams.size())
				m_subtitleStreams[m_currentSubtitleStream] = subs;
			else
				m_subtitleStreams.push_back(subs);
		}

		// eDebug("[eServiceMP3] gstGhostpadHasCAPS:: m_gst_prev_subtitle_caps=%s
		// equal=%i",gst_caps_to_string(m_gst_prev_subtitle_caps),gst_caps_is_equal(m_gst_prev_subtitle_caps, caps));

		gst_caps_unref(caps);
	}
}

/**
 * @brief Pulls subtitles from a GstBuffer and processes them.
 *
 * This function extracts subtitle data from the given GstBuffer and processes it
 * based on the current subtitle stream type. It supports WebVTT, DVB, and text subtitles.
 *
 * @param[in] buffer The GstBuffer containing subtitle data.
 */
void eServiceMP3::pullSubtitle(GstBuffer* buffer) {
	if (buffer && m_currentSubtitleStream >= 0 && m_currentSubtitleStream < (int)m_subtitleStreams.size()) {
		GstMapInfo map;
		if (!gst_buffer_map(buffer, &map, GST_MAP_READ))
			return;
		int subType = m_subtitleStreams[m_currentSubtitleStream].type;
		if (subType == stWebVTT) {
			std::string vtt_string(reinterpret_cast<char*>(map.data), map.size);
			std::vector<SubtitleEntry> parsed_subs;

			// eDebug("SUB DEBUG line");
			// eDebug(">>>\n%s\n<<<", vtt_string.c_str());

			if (parseWebVTT(vtt_string, parsed_subs)) {
				static int64_t base_mpegts = 0; // Store first MPEGTS as base

				for (const auto& sub : parsed_subs) {
					if (sub.vtt_mpegts_base) {
						if (!m_vtt_live)
							m_vtt_live = true; // Set live flag if we have a base MPEGTS
						int64_t decoder_pts = getLiveDecoderTime();
						int64_t delta = 0;

						// Initialize base MPEGTS with first subtitle's MPEGTS
						if (base_mpegts == 0) {
							base_mpegts = sub.vtt_mpegts_base;
						}

						if (decoder_pts >= 0) {
							// Both values are in 90kHz
							const uint64_t pts_mask = (1ULL << 33) - 1; // 33-bit mask

							// Calculate delta based on MPEGTS difference
							delta = (sub.vtt_mpegts_base - base_mpegts) / 90; // Convert to ms
						}

						int64_t adjusted_start = sub.start_time_ms + delta;
						int64_t adjusted_end = sub.end_time_ms + delta;

						std::lock_guard<std::mutex> lock(m_subtitle_pages_mutex);
						m_subtitle_pages.insert(subtitle_pages_map_pair_t(
							adjusted_end, subtitle_page_t(adjusted_start, adjusted_end, sub.text)));
					} else {
						m_subtitle_pages.insert(subtitle_pages_map_pair_t(
							sub.end_time_ms, subtitle_page_t(sub.start_time_ms, sub.end_time_ms, sub.text)));
					}
				}
				if (!parsed_subs.empty())
					m_subtitle_sync_timer->start(250, true);
			}
		} else if (subType == stDVB) {
			uint8_t* data = map.data;
			int64_t buf_pos = GST_BUFFER_PTS(buffer);
			m_dvb_subtitle_parser->processBuffer(data, map.size, buf_pos / 1000000ULL);
		} else if (subType < stVOB) {
			std::string line(reinterpret_cast<char*>(map.data), map.size);
			uint32_t start_ms = GST_BUFFER_PTS(buffer) / 1000000ULL;
			uint32_t duration = GST_BUFFER_DURATION(buffer) / 1000000ULL;
			uint32_t end_ms = start_ms + duration;
			// eDebug("[eServiceMP3] got new text subtitle @ start_ms=%d / dur=%d: '%s' ", start_ms, duration,
			// line.c_str());

			m_subtitle_pages.insert(subtitle_pages_map_pair_t(end_ms, subtitle_page_t(start_ms, end_ms, line)));
			m_subtitle_sync_timer->start(250, true);
		}
		gst_buffer_unmap(buffer, &map);
	}
}

/**
 * @brief Adds a new DVB subtitle page to the list and pushes it to the subtitle widget.
 *
 * This function adds a new DVB subtitle page to the list of pages and triggers
 * the subtitle widget to display it.
 *
 * @param[in] p The eDVBSubtitlePage to add.
 */
void eServiceMP3::newDVBSubtitlePage(const eDVBSubtitlePage& p) {
	m_dvb_subtitle_pages.push_back(p);
	pushDVBSubtitles();
}

/**
 * @brief Pushes DVB subtitles to the subtitle widget.
 *
 * This function processes the DVB subtitle pages and displays them in the
 * subtitle widget based on the current decoder time.
 */
void eServiceMP3::pushDVBSubtitles() {
	pts_t running_pts = 0, decoder_ms;

	if (getPlayPosition(running_pts) < 0)
		eTrace("[eServiceMP3] Cant get current decoder time.");

	while (1) {
		eDVBSubtitlePage dvb_page;
		pts_t show_time;
		if (!m_dvb_subtitle_pages.empty()) {
			dvb_page = m_dvb_subtitle_pages.front();
			show_time = dvb_page.m_show_time;
		} else
			return;

		decoder_ms = running_pts / 90;

		// If subtitle is overdue or within 20ms the video timing then display it.
		// If cant get decoder PTS then display the subtitles.
		// If not, pause subtitle processing until the subtitle should be shown
		pts_t diff = show_time - decoder_ms;
		if (diff < 20 || decoder_ms == 0) {
			eTrace("[eServiceMP3] Showing subtitles at %lld. Current decoder time: %lld. Difference: %lld", show_time,
				   decoder_ms, diff);
			m_subtitle_widget->setPage(dvb_page);
			m_dvb_subtitle_pages.pop_front();
		} else {
			eDebug("[eServiceMP3] Delay early subtitle by %.03fs. Page stack size %lu", diff / 1000.0f,
				   m_dvb_subtitle_pages.size());
			m_dvb_subtitle_sync_timer->start(diff, 1);
			break;
		}
	}
}

/**
 * @brief Pushes subtitles to the subtitle widget.
 *
 * This function processes the subtitle pages and displays them in the
 * subtitle widget based on the current decoder time. It handles both live
 * streams and VOD content, applying necessary delays and conversions.
 */
void eServiceMP3::pushSubtitles() {
	pts_t running_pts = 0;
	int32_t next_timer = 0, decoder_ms = 0, start_ms, end_ms, diff_start_ms, diff_end_ms, delay_ms;
	double convert_fps = 1.0;
	subtitle_pages_map_t::iterator current;

	// For live streams, get decoder time directly from videosink
	if (m_vtt_live && dvb_videosink) {
		gint64 pos = 0;
		gboolean success = FALSE;
		g_signal_emit_by_name(dvb_videosink, "get-decoder-time", &pos, &success);
		if (success && GST_CLOCK_TIME_IS_VALID(pos) && pos > 0) {
			// Convert from nanoseconds back to ms
			decoder_ms = pos / 1000000;
			running_pts = pos / 11111;
			m_decoder_time_valid_state = 4;
		} else {
			// If we can't get valid decoder time, use fallback for WebVTT
			if (m_subtitleStreams[m_currentSubtitleStream].type == stWebVTT) {
				m_decoder_time_valid_state = 4; // Consider clock stable
				// Let decoder_ms stay 0 to trigger fallback
			} else {
				if (getPlayPosition(running_pts) < 0)
					m_decoder_time_valid_state = 0;
				decoder_ms = running_pts / 90;
			}
		}
	} else {
		// Original VOD logic
		if (getPlayPosition(running_pts) < 0)
			m_decoder_time_valid_state = 0;
		if (m_decoder_time_valid_state == 0)
			m_decoder_time_valid_state = 2;
		else
			m_decoder_time_valid_state = 4;

		if (m_decoder_time_valid_state < 4) {
			m_decoder_time_valid_state++;

			if (m_decoder_time_valid_state < 4) {
				// eDebug("[eServiceMP3] *** push subtitles, waiting for clock to stabilise");
				m_prev_decoder_time = running_pts;
				next_timer = 100;
				goto exit;
			}

			// eDebug("[eServiceMP3] *** push subtitles, clock stable");
		}

		decoder_ms = running_pts / 90;
	}
	delay_ms = 0;

	// eDebug("[eServiceMP3] pushSubtitles running_pts=%lld decoder_ms=%d delay=%d fps=%.2f", running_pts, decoder_ms,
	//	   delay_ms, convert_fps);

#if 0
    eDebug("\n*** all subs: ");

    for (current = m_subtitle_pages.begin(); current != m_subtitle_pages.end(); current++) {
		start_ms = current->second.start_ms;
		end_ms = current->second.end_ms;
		diff_start_ms = start_ms - decoder_ms;
		diff_end_ms = end_ms - decoder_ms;

	eDebug("[eServiceMP3] start: %d, end: %d, diff_start: %d, diff_end: %d: %s", start_ms, end_ms, diff_start_ms,
	    diff_end_ms, current->second.text.c_str());
    }

    eDebug("\n\n");
#endif
	// Apply subtitle delay and fps conversion if needed
	if (m_currentSubtitleStream >= 0 && m_currentSubtitleStream < (int)m_subtitleStreams.size() &&
		m_subtitleStreams[m_currentSubtitleStream].type && m_subtitleStreams[m_currentSubtitleStream].type < stVOB) {
		delay_ms = eSubtitleSettings::pango_subtitles_delay / 90;
		int subtitle_fps = eSubtitleSettings::pango_subtitles_fps;
		if (subtitle_fps > 1 && m_framerate > 0)
			convert_fps = subtitle_fps / (double)m_framerate;
	}

	// Clean up old subtitles for live streams to prevent memory growth
	/*
	if (m_vtt_live && !m_subtitle_pages.empty()) {
		std::lock_guard<std::mutex> lock(m_subtitle_pages_mutex);
		subtitle_pages_map_t::iterator it = m_subtitle_pages.begin();
		while (it != m_subtitle_pages.end()) {
			bool erase = false;
			int end_ms = it->second.end_ms;

			if (m_subtitleStreams[m_currentSubtitleStream].type == stWebVTT && m_is_live) {
				int64_t now = getCurrentTimeMs();
				if (m_vtt_live_base_time == -1 && !m_subtitle_pages.empty())
					m_vtt_live_base_time = now - m_subtitle_pages.begin()->second.start_ms;
				int64_t live_playback_time = now - m_vtt_live_base_time;
				if ((end_ms - live_playback_time) < -5000) // 5 seconds
					erase = true;
			} else {
				if ((end_ms - decoder_ms) < -5000)
					erase = true;
			}

			if (erase) {
				eDebug("[eServiceMP3] Cleaning up old subtitle: end=%d", end_ms);
				it = m_subtitle_pages.erase(it);
			} else {
				++it;
			}
		}
	}
	*/
	for (current = m_subtitle_pages.begin(); current != m_subtitle_pages.end(); ++current) {
		start_ms = current->second.start_ms;
		end_ms = current->second.end_ms;

		if (m_subtitleStreams[m_currentSubtitleStream].type == stWebVTT && m_vtt_live) {
			// --- WebVTT LIVE WORKAROUND ---
			int64_t now = getCurrentTimeMs();

			if (m_vtt_live_base_time == -1)
				m_vtt_live_base_time = now - start_ms;

			int64_t live_playback_time = now - m_vtt_live_base_time;

			diff_start_ms = start_ms - live_playback_time;
			diff_end_ms = end_ms - live_playback_time;

			// eDebug("[eServiceMP3] WebVTT LIVE: now=%" PRId64 " base=%" PRId64 " live_playback_time=%" PRId64
			//	   " start=%d end=%d "
			//	   "diff_start=%d diff_end=%d",
			//	   now, m_vtt_live_base_time, live_playback_time, start_ms, end_ms, diff_start_ms, diff_end_ms);

			if (diff_end_ms < -500) {
				// eDebug("[eServiceMP3] *** current sub has already ended, skip: %d\n", diff_end_ms);
				continue;
			}
			if (diff_start_ms > 10) {
				// eDebug("[eServiceMP3] *** current sub in the future, start timer, %d\n", diff_start_ms);
				next_timer = diff_start_ms;
				goto exit;
			}
			// showtime for WebVTT
			if (m_subtitle_widget && !m_paused) {
				// eDebug("[eServiceMP3] *** current sub actual, show!");
				ePangoSubtitlePage pango_page;
				gRGB rgbcol(0xff, 0xff, 0xff); // White color for WebVTT
				pango_page.m_elements.push_back(ePangoSubtitlePageElement(rgbcol, current->second.text));
				pango_page.m_show_pts = start_ms * 90;
				pango_page.m_timeout = diff_end_ms > 0 ? diff_end_ms : end_ms - start_ms;
				m_subtitle_widget->setPage(pango_page);
				continue;
			}
			// --- END WORKAROUND ---
		} else if (m_subtitleStreams[m_currentSubtitleStream].type == stWebVTT) {
			diff_start_ms = start_ms - decoder_ms;
			diff_end_ms = end_ms - decoder_ms;

			// eDebug("[eServiceMP3] WebVTT decoder timing: start_ms=%d end_ms=%d decoder_ms=%d diff_start=%d
			// diff_end=%d", 	   start_ms, end_ms, decoder_ms, diff_start_ms, diff_end_ms);

			if (diff_end_ms < -500) {
				// eDebug("[eServiceMP3] *** current sub has already ended, skip: %d\n", diff_end_ms);
				continue;
			}
			if (diff_start_ms > 10) {
				// eDebug("[eServiceMP3] *** current sub in the future, start timer, %d\n", diff_start_ms);
				next_timer = diff_start_ms;
				goto exit;
			}
			if (m_subtitle_widget && !m_paused) {
				// eDebug("[eServiceMP3] *** current sub actual, show!");
				ePangoSubtitlePage pango_page;
				gRGB rgbcol(0xff, 0xff, 0xff);
				pango_page.m_elements.push_back(ePangoSubtitlePageElement(rgbcol, current->second.text));
				pango_page.m_show_pts = start_ms * 90;
				pango_page.m_timeout = diff_end_ms > 0 ? diff_end_ms : end_ms - start_ms;
				m_subtitle_widget->setPage(pango_page);
				continue;
			}
		} else {
			start_ms = (current->second.start_ms * convert_fps) + delay_ms;
			end_ms = (current->second.end_ms * convert_fps) + delay_ms;
			diff_start_ms = start_ms - decoder_ms;
			diff_end_ms = end_ms - decoder_ms;

			const int64_t wrap_threshold = 1LL << 31;
			const int64_t wrap_value = 1LL << 32;
			if (diff_start_ms > wrap_threshold)
				diff_start_ms -= wrap_value;
			else if (diff_start_ms < -wrap_threshold)
				diff_start_ms += wrap_value;
			if (diff_end_ms > wrap_threshold)
				diff_end_ms -= wrap_value;
			else if (diff_end_ms < -wrap_threshold)
				diff_end_ms += wrap_value;

#if 0
			eDebug("[eServiceMP3] *** next subtitle: decoder: %d start: %d, end: %d, duration_ms: %d, "
				   "diff_start: %d, diff_end: %d : %s",
				   decoder_ms, start_ms, end_ms, end_ms - start_ms, diff_start_ms, diff_end_ms,
				   current->second.text.c_str());
#endif

			if (diff_end_ms < 0) {
				// eDebug("[eServiceMP3] *** current sub has already ended, skip: %d\n", diff_end_ms);
				continue;
			}
			if (diff_start_ms > 20) {
				// eDebug("[eServiceMP3] *** current sub in the future, start timer, %d\n", diff_start_ms);
				next_timer = diff_start_ms;
				goto exit;
			}
			if (m_subtitle_widget && !m_paused) {
				eDebug("[eServiceMP3] *** current sub actual, show!");
				ePangoSubtitlePage pango_page;
				gRGB rgbcol(0xD0, 0xD0, 0xD0);
				pango_page.m_elements.push_back(ePangoSubtitlePageElement(rgbcol, current->second.text.c_str()));
				pango_page.m_show_pts = start_ms * 90; // actually completely unused by widget!
				if (!m_subtitles_paused)
					pango_page.m_timeout = end_ms - decoder_ms; // take late start into account
				else
					pango_page.m_timeout = 60000;
				// paused, subs must stay on (60s for now), avoid timeout in lib/gui/esubtitle.cpp:
				// m_hide_subtitles_timer->start(m_pango_page.m_timeout, true);
				m_subtitle_widget->setPage(pango_page);
			}
		}
		// eDebug("[eServiceMP3] *** no next sub scheduled, check NEXT subtitle");
	}

exit:
	if (next_timer == 0) {
		// eDebug("[eServiceMP3] *** next timer = 0, set default timer!");
		next_timer = 1000;
	}
	m_subtitle_sync_timer->start(next_timer, true);
}

/**
 * @brief Enables subtitles for the current service.
 *
 * This function enables subtitles for the current service by setting the
 * current text stream in the GStreamer playbin and updating the subtitle
 * widget with the specified track.
 *
 * @param[in] user The subtitle user interface to update.
 * @param[in] track The subtitle track to enable.
 * @return RESULT indicating success or failure.
 */
RESULT eServiceMP3::enableSubtitles(iSubtitleUser* user, struct SubtitleTrack& track) {
	bool starting_subtitle = false;
	if (m_currentSubtitleStream != track.pid || eSubtitleSettings::pango_autoturnon) {
		// if (m_currentSubtitleStream == -1)
		//	starting_subtitle = true;
		g_object_set(m_gst_playbin, "current-text", -1, NULL);
		// m_cachedSubtitleStream = -1;
		m_subtitle_sync_timer->stop();
		m_dvb_subtitle_sync_timer->stop();
		m_dvb_subtitle_pages.clear();
		m_subtitle_pages.clear();
		m_prev_decoder_time = -1;
		m_decoder_time_valid_state = 0;
		m_currentSubtitleStream = track.pid;
		m_cachedSubtitleStream = m_currentSubtitleStream;
		setCacheEntry(false, track.pid);
		g_object_set(m_gst_playbin, "current-text", m_currentSubtitleStream, NULL);

		if (track.type != stDVB) {
			m_clear_buffers = true;
			clearBuffers();
		}
		m_subtitle_widget = user;

		eDebug("[eServiceMP3] switched to subtitle stream %i", m_currentSubtitleStream);

#ifdef GSTREAMER_SUBTITLE_SYNC_MODE_BUG
		/*
		 * when we're running the subsink in sync=false mode,
		 * we have to force a seek, before the new subtitle stream will start
		 */
		seekRelative(-1, 90000);
#endif

		// Seek to last position for non-initial subtitle changes
		if (m_last_seek_pos > 0 && !starting_subtitle) {
			seekTo(m_last_seek_pos);
			gst_sleepms(50);
		}
	}

	return 0;
}

/**
 * @brief Disables subtitles for the current service.
 *
 * This function disables subtitles by setting the current text stream to -1
 * in the GStreamer playbin and clearing the subtitle widget.
 *
 * @return RESULT indicating success or failure.
 */
RESULT eServiceMP3::disableSubtitles() {
	eDebug("[eServiceMP3] disableSubtitles");
	m_currentSubtitleStream = -1;
	m_cachedSubtitleStream = m_currentSubtitleStream;
	setCacheEntry(false, -1);
	g_object_set(m_gst_playbin, "current-text", m_currentSubtitleStream, NULL);
	m_subtitle_sync_timer->stop();
	m_dvb_subtitle_sync_timer->stop();
	m_dvb_subtitle_pages.clear();
	m_subtitle_pages.clear();
	m_prev_decoder_time = -1;
	m_decoder_time_valid_state = 0;
	if (m_subtitle_widget)
		m_subtitle_widget->destroy();
	m_subtitle_widget = 0;
	return 0;
}

/**
 * @brief Retrieves the cached subtitle stream for the current service.
 *
 * This function checks if there is a cached subtitle stream available and
 * returns the corresponding SubtitleTrack structure. If no suitable subtitle
 * stream is found, it returns -1.
 *
 * @param[out] track The SubtitleTrack structure to fill with subtitle information.
 * @return RESULT indicating success or failure.
 */
RESULT eServiceMP3::getCachedSubtitle(struct SubtitleTrack& track) {
	// If autostart not active, exit
	if (!eSubtitleSettings::pango_autoturnon)
		return -1;
	int autosub_level = 5;
	std::string configvalue;
	std::vector<std::string> autosub_languages;


	// Initialize cache if needed
	if (m_cachedSubtitleStream == -2 && !m_subtitleStreams.empty()) {
		m_cachedSubtitleStream = 0;

		// Get configured languages
		configvalue = eSubtitleSettings::subtitle_autoselect1;
		if (configvalue != "")
			autosub_languages.push_back(configvalue);
		configvalue = eSubtitleSettings::subtitle_autoselect2;
		if (configvalue != "")
			autosub_languages.push_back(configvalue);
		configvalue = eSubtitleSettings::subtitle_autoselect3;
		if (configvalue != "")
			autosub_languages.push_back(configvalue);
		configvalue = eSubtitleSettings::subtitle_autoselect4;
		if (configvalue != "")
			autosub_languages.push_back(configvalue);

		// Find best matching subtitle
		for (size_t i = 0; i < m_subtitleStreams.size(); i++) {
			if (!m_subtitleStreams[i].language_code.empty()) {
				int x = 1;
				for (std::vector<std::string>::iterator it = autosub_languages.begin();
					 x < autosub_level && it != autosub_languages.end(); x++, it++) {
					if ((*it).find(m_subtitleStreams[i].language_code) != std::string::npos) {
						autosub_level = x;
						m_cachedSubtitleStream = i;
						break;
					}
				}
			}
		}
	}

	if (m_cachedSubtitleStream >= 0 && m_cachedSubtitleStream < (int)m_subtitleStreams.size()) {
		track.type = m_subtitleStreams[m_cachedSubtitleStream].type == stDVB ? 0 : 2;
		track.pid = m_cachedSubtitleStream;
		track.page_number = int(m_subtitleStreams[m_cachedSubtitleStream].type);
		track.magazine_number = 0;
		track.language_code = m_subtitleStreams[m_cachedSubtitleStream].language_code;
		track.title = m_subtitleStreams[m_cachedSubtitleStream].title;
		return 0;
	}

	return -1;
}

/**
 * @brief Retrieves the list of available subtitle tracks for the current service.
 *
 * This function populates the provided vector with SubtitleTrack structures
 * representing the available subtitle streams. It iterates through the
 * m_subtitleStreams vector and fills in the details for each subtitle track.
 *
 * @param[out] subtitlelist The vector to fill with available subtitle tracks.
 * @return RESULT indicating success or failure.
 */
RESULT eServiceMP3::getSubtitleList(std::vector<struct SubtitleTrack>& subtitlelist) {
	// Process all subtitle streams including CC streams in one loop
	for (size_t i = 0; i < m_subtitleStreams.size(); i++) {
		const subtitleStream& stream = m_subtitleStreams[i];

		// Skip unsupported types
		if (stream.type == stUnknown || stream.type == stVOB || stream.type == stPGS) {
			continue;
		}

		struct SubtitleTrack track;
		track.type = (stream.type == stDVB) ? 0 : 2;
		track.pid = i;
		track.page_number = int(stream.type);
		track.magazine_number = 0;
		track.language_code = stream.language_code;
		track.title = stream.title;

		subtitlelist.push_back(track);
	}

	return 0;
}

/**
 * @brief Retrieves the current subtitle stream.
 *
 * This function returns the current subtitle stream as an integer. If no
 * subtitle stream is set, it returns -1.
 *
 * @return The current subtitle stream ID or -1 if none is set.
 */
RESULT eServiceMP3::streamed(ePtr<iStreamedService>& ptr) {
	ptr = this;
	return 0;
}

/**
 * @brief Retrieves the buffer charge information for the service.
 *
 * This function returns a pointer to an iStreamBufferInfo object containing
 * the current buffer charge information, including buffer percentage, average
 * input and output rates, buffering left time, and buffer size.
 *
 * @return A pointer to an iStreamBufferInfo object with buffer charge details.
 */
ePtr<iStreamBufferInfo> eServiceMP3::getBufferCharge() {
	return new eStreamBufferInfo(m_bufferInfo.bufferPercent, m_bufferInfo.avgInRate, m_bufferInfo.avgOutRate,
								 m_bufferInfo.bufferingLeft, m_buffer_size);
}


/* cuesheet CVR */
/**
 * @brief Retrieves the cut list as a Python list.
 *
 * This function creates a Python list containing tuples of cue entries,
 * where each tuple consists of the position (pts) and type of the cue entry.
 *
 * @return A Python list containing the cut list.
 */
PyObject* eServiceMP3::getCutList() {
	ePyObject list = PyList_New(0);

	for (std::multiset<struct cueEntry>::iterator i(m_cue_entries.begin()); i != m_cue_entries.end(); ++i) {
		ePyObject tuple = PyTuple_New(2);
		PyTuple_SET_ITEM(tuple, 0, PyLong_FromLongLong(i->where));
		PyTuple_SET_ITEM(tuple, 1, PyLong_FromLong(i->what));
		PyList_Append(list, tuple);
		Py_DECREF(tuple);
	}

	return list;
}

/**
 * @brief Sets the cut list from a Python list.
 *
 * This function takes a Python list of tuples, where each tuple contains
 * a position (pts) and type of the cue entry, and updates the internal
 * cut list accordingly. It clears the existing entries before adding new ones.
 *
 * @param[in] list A Python list containing tuples of cue entries.
 */
void eServiceMP3::setCutList(ePyObject list) {
	if (!PyList_Check(list))
		return;
	int size = PyList_Size(list);
	int i;

	m_cue_entries.clear();

	for (i = 0; i < size; ++i) {
		ePyObject tuple = PyList_GET_ITEM(list, i);
		if (!PyTuple_Check(tuple)) {
			eDebug("[eServiceMP3] non-tuple in cutlist");
			continue;
		}
		if (PyTuple_Size(tuple) != 2) {
			eDebug("[eServiceMP3] cutlist entries need to be a 2-tuple");
			continue;
		}
		ePyObject ppts = PyTuple_GET_ITEM(tuple, 0), ptype = PyTuple_GET_ITEM(tuple, 1);
		if (!(PyLong_Check(ppts) && PyLong_Check(ptype))) {
			eDebug("[eServiceMP3] cutlist entries need to be (pts, type)-tuples (%d %d)", PyLong_Check(ppts),
				   PyLong_Check(ptype));
			continue;
		}
		pts_t pts = PyLong_AsLongLong(ppts);
		int type = PyLong_AsLong(ptype);
		m_cue_entries.insert(cueEntry(pts, type));
		eDebug("[eServiceMP3] adding %" G_GINT64_FORMAT " type %d", (gint64)pts, type);
	}
	m_cuesheet_changed = 1;
	m_event((iPlayableService*)this, evCuesheetChanged);
}

/**
 * @brief Sets whether the cut list is enabled.
 *
 * This function enables or disables the cut list functionality based on the
 * provided integer value. If the value is non-zero, the cut list is enabled;
 * otherwise, it is disabled.
 *
 * @param[in] enable An integer indicating whether to enable (non-zero) or disable (zero) the cut list.
 */
void eServiceMP3::setCutListEnable(int enable) {
	m_cutlist_enabled = enable;
}

/**
 * @brief Retrieves whether the cut list is enabled.
 *
 * This function returns the current state of the cut list, indicating whether
 * it is enabled or not.
 *
 * @return An integer indicating whether the cut list is enabled (non-zero) or disabled (zero).
 */
int eServiceMP3::setBufferSize(int size) {
	m_buffer_size = size;
	g_object_set(m_gst_playbin, "buffer-size", m_buffer_size, NULL);
	return 0;
}

/**
 * @brief Retrieves the current buffer size.
 *
 * This function returns the current buffer size set for the service.
 *
 * @return The current buffer size in bytes.
 */
int eServiceMP3::getAC3Delay() {
	return ac3_delay;
}

/**
 * @brief Retrieves the current PCM delay.
 *
 * This function returns the current PCM delay set for the service.
 *
 * @return The current PCM delay in milliseconds.
 */
int eServiceMP3::getPCMDelay() {
	return pcm_delay;
}

/**
 * @brief Sets the AC3 delay for the service.
 *
 * This function sets the AC3 delay in milliseconds. If the playbin is running,
 * it configures the hardware decoder with the specified delay, adjusted by
 * the general AC3 delay setting if a video sink is present.
 *
 * @param[in] delay The AC3 delay in milliseconds to set.
 */
void eServiceMP3::setAC3Delay(int delay) {
	ac3_delay = delay;
	if (!m_gst_playbin || m_state != stRunning)
		return;
	else {
		int config_delay_int = delay;

		/*
		 * NOTE: We only look for dvbmediasinks.
		 * If either the video or audio sink is of a different type,
		 * we have no chance to get them synced anyway.
		 */
		if (dvb_videosink) {
			config_delay_int += eSimpleConfig::getInt("config.av.generalAC3delay");
		} else {
			// eDebug("[eServiceMP3]dont apply ac3 delay when no video is running!");
			config_delay_int = 0;
		}

		if (dvb_audiosink) {
			eTSMPEGDecoder::setHwAC3Delay(config_delay_int);
		}
	}
}

/**
 * @brief Sets the PCM delay for the service.
 *
 * This function sets the PCM delay in milliseconds. If the playbin is running,
 * it configures the hardware decoder with the specified delay, adjusted by
 * the general PCM delay setting if a video sink is present.
 *
 * @param[in] delay The PCM delay in milliseconds to set.
 */
void eServiceMP3::setPCMDelay(int delay) {
	pcm_delay = delay;
	if (!m_gst_playbin || m_state != stRunning)
		return;
	else {
		int config_delay_int = delay;

		/*
		 * NOTE: We only look for dvbmediasinks.
		 * If either the video or audio sink is of a different type,
		 * we have no chance to get them synced anyway.
		 */
		if (dvb_videosink) {
			config_delay_int += eSimpleConfig::getInt("config.av.generalPCMdelay");
		} else {
			// eDebug("[eServiceMP3] dont apply pcm delay when no video is running!");
			config_delay_int = 0;
		}

		if (dvb_audiosink) {
			eTSMPEGDecoder::setHwPCMDelay(config_delay_int);
		}
	}
}


/* cuesheet CVR */
/**
 * @brief Loads the cuesheet from a file.
 *
 * This function loads the cuesheet entries from a file with the same name as
 * the service path, appending ".cuts" to it. It reads the entries and stores
 * them in the m_cue_entries multiset.
 */
void eServiceMP3::loadCuesheet() {
	if (!m_cuesheet_loaded) {
		eDebug("[eServiceMP3] loading cuesheet");
		m_cuesheet_loaded = true;
	} else {
		// eDebug("[eServiceMP3] skip loading cuesheet multiple times");
		return;
	}

	m_cue_entries.clear();

	std::string filename = m_ref.path + ".cuts";

	FILE* f = fopen(filename.c_str(), "rb");

	if (f) {
		while (1) {
			unsigned long long where;
			unsigned int what;

			if (!fread(&where, sizeof(where), 1, f))
				break;
			if (!fread(&what, sizeof(what), 1, f))
				break;

			where = be64toh(where);
			what = ntohl(what);

			if (what < 4)
				m_cue_entries.insert(cueEntry(where, what));

			// if (m_cuesheet_changed == 2)
			//	eDebug("[eServiceMP3] reloading cuts: %" G_GINT64_FORMAT " type %d", (gint64)where, what);
		}
		fclose(f);
		eDebug("[eServiceMP3] cuts file has %zd entries", m_cue_entries.size());
	} else
		eDebug("[eServiceMP3] cutfile not found!");

	m_cuesheet_changed = 0;
	m_event((iPlayableService*)this, evCuesheetChanged);
}
/* cuesheet */

/**
 * @brief Saves the cuesheet to a file.
 *
 * This function saves the current cuesheet entries to a file with the same
 * name as the service path, appending ".cuts" to it. It writes the entries
 * in a binary format, where each entry consists of a position (pts) and type.
 */
void eServiceMP3::saveCuesheet() {
	std::string filename = m_ref.path;

	if (::access(filename.c_str(), R_OK) < 0)
		return;

	filename.append(".cuts");

	struct stat s = {};
	bool removefile = false;
	bool use_videocuesheet = eSimpleConfig::getBool("config.usage.useVideoCuesheet", true);
	bool use_audiocuesheet = eSimpleConfig::getBool("config.usage.useAudioCuesheet", true);
	bool exist_cuesheetfile = (stat(filename.c_str(), &s) == 0);

	if (!exist_cuesheetfile && m_cue_entries.size() == 0)
		return;
	else if ((use_videocuesheet && !m_sourceinfo.is_audio) || (m_sourceinfo.is_audio && use_audiocuesheet)) {
		if (m_cue_entries.size() == 0) {
			m_cuesheet_loaded = false;
			// m_cuesheet_changed = 2;
			loadCuesheet();
			if (m_cue_entries.size() != 0) {
				eDebug("[eServiceMP3] *** NO NEW CUTS TO WRITE CUTS FILE ***");
				return;
			} else {
				eDebug("[eServiceMP3] *** REMOVING EXISTING CUTS FILE NO LAST PLAY NO MANUAL CUTS ***");
				removefile = true;
			}
		} else
			eDebug("[eServiceMP3] *** WRITE CUTS TO CUTS FILE ***");
	} else if (exist_cuesheetfile) {
		eDebug("[eServiceMP3] *** REMOVING EXISTING CUTS FILE ***");
		removefile = true;
	} else
		return;

	FILE* f = fopen(filename.c_str(), "wb");

	if (f) {
		if (removefile) {
			fclose(f);
			remove(filename.c_str());
			eDebug("[eServiceMP3] cuts file has been removed");
			return;
		}

		signed long long where = 0;
		guint what = 0;

		for (std::multiset<cueEntry>::iterator i(m_cue_entries.begin()); i != m_cue_entries.end(); ++i) {
			if (where == i->where && what == i->what)
				/* ignore double entries */
				continue;
			else {
				where = htobe64(i->where);
				what = htonl(i->what);
				fwrite(&where, sizeof(where), 1, f);
				fwrite(&what, sizeof(what), 1, f);
				/* temorary save for comparing */
				where = i->where;
				what = i->what;
			}
		}
		fclose(f);
		eDebug("[eServiceMP3] cuts file has been write");
	}
	m_cuesheet_changed = 0;
}
