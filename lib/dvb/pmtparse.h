#ifndef _dvb_pmtparse_h
#define _dvb_pmtparse_h

#include <vector>

#include <lib/dvb/esection.h>

#include <dvbsi++/program_map_section.h>
#include <dvbsi++/program_association_section.h>
#include <dvbsi++/application_information_section.h>

class eDVBPMTParser: public sigc::trackable
{
protected:
	eAUTable<eTable<ProgramMapSection> > m_PMT;
	virtual void PMTready(int error) = 0;

public:
	eDVBPMTParser();
	virtual ~eDVBPMTParser() {}

	struct videoStream
	{
		int pid;
		int component_tag;
		enum { vtMPEG2, vtMPEG4_H264, vtMPEG1, vtMPEG4_Part2, vtVC1, vtVC1_SM, vtH265_HEVC, vtCAVS };
		int type;
	};

	struct audioStream
	{
		int pid,
		rdsPid; // hack for some radio services which transmit radiotext on different pid (i.e. harmony fm, HIT RADIO FFH, ...)
		enum { atMPEG, atAC3, atDTS, atAAC, atAACHE, atLPCM, atDTSHD, atDDP };
		int type; // mpeg2, ac3, dts, ...

		int component_tag;
		std::string language_code; /* iso-639, if available. */
	};

	struct subtitleStream
	{
		int pid;
		int subtitling_type;  	/*  see ETSI EN 300 468 table 26 component_type
									when stream_content is 0x03
									0x10..0x13, 0x20..0x23 is used for dvb subtitles
									0x01 is used for teletext subtitles */
		union
		{
			int composition_page_id;  // used for dvb subtitles
			int teletext_page_number;  // used for teletext subtitles
		};
		union
		{
			int ancillary_page_id;  // used for dvb subtitles
			int teletext_magazine_number;  // used for teletext subtitles
		};
		std::string language_code;
		bool operator<(const subtitleStream &s) const
		{
			if (pid != s.pid)
				return pid < s.pid;
			if (teletext_page_number != s.teletext_page_number)
				return teletext_page_number < s.teletext_page_number;
			return teletext_magazine_number < s.teletext_magazine_number;
		}
	};

	struct program
	{
		struct capid_pair
		{
			uint16_t caid;
			int capid;
			bool operator< (const struct capid_pair &t) const { return t.caid < caid; }
		};
		std::vector<videoStream> videoStreams;
		std::vector<audioStream> audioStreams;
		int defaultAudioStream;
		std::vector<subtitleStream> subtitleStreams;
		int defaultSubtitleStream;
		std::list<capid_pair> caids;
		int pcrPid;
		int pmtPid;
		int textPid;
		int aitPid;
		int dsmccPid;
		int serviceId;
		int adapterId;
		int demuxId;
		bool isCrypted() { return !caids.empty(); }
	};

	class eStreamData : public iStreamData
	{
		DECLARE_REF(eStreamData);
		std::vector<int> caIds;
		std::vector<int> ecmPids;
		std::vector<int> videoStreams;
		std::vector<int> audioStreams;
		std::vector<int> subtitleStreams;
		int pcrPid, pmtPid, textPid, aitPid, serviceId, adapterId, demuxId;
	public:
		eStreamData(struct program &program);
		RESULT getAllPids(std::vector<int> &result) const;
		RESULT getVideoPids(std::vector<int> &result) const;
		RESULT getAudioPids(std::vector<int> &result) const;
		RESULT getSubtitlePids(std::vector<int> &result) const;
		RESULT getPmtPid(int &result) const;
		RESULT getPatPid(int &result) const;
		RESULT getPcrPid(int &result) const;
		RESULT getTxtPid(int &result) const;
		RESULT getAitPid(int &result) const;
		RESULT getServiceId(int &result) const;
		RESULT getAdapterId(int &result) const;
		RESULT getDemuxId(int &result) const;
		RESULT getCaIds(std::vector<int> &caids, std::vector<int> &ecmpids) const;
	};

	virtual int getProgramInfo(program &program);
	void clearProgramInfo(program &program);
};

#endif
