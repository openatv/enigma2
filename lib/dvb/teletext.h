#ifndef __lib_dvb_teletext_h
#define __lib_dvb_teletext_h

#include <lib/base/object.h>
#include <lib/dvb/idvb.h>
#include <lib/dvb/pesparse.h>
#include <lib/dvb/pmt.h>
#include <lib/gdi/gpixmap.h>
#include <map>

struct eDVBTeletextSubtitlePageElement
{
	gRGB m_color;
	std::string m_text;
	eRect m_area;
	eDVBTeletextSubtitlePageElement(const gRGB &color, const std::string &text)
		: m_color(color), m_text(text)
	{
	}
};

struct eDVBTeletextSubtitlePage
{
	pts_t m_pts;
	int m_have_pts;
	int m_timeout; /* in pts */
	int m_C, m_Y;
	std::vector<eDVBTeletextSubtitlePageElement> m_elements;
	
	void clear() { m_elements.clear(); }
};

class eDVBTeletextParser: public iObject, public ePESParser, public Object
{
	DECLARE_REF(eDVBTeletextParser);
public:
	eDVBTeletextParser(iDVBDemux *demux);
	virtual ~eDVBTeletextParser();
	int start(int pid);
	void setPageAndMagazine(int page, int magazine);
	void setMagazine(int magazine);
	void connectNewPage(const Slot1<void,const eDVBTeletextSubtitlePage &> &slot, ePtr<eConnection> &connection);
	std::set<eDVBServicePMTHandler::subtitleStream> m_found_subtitle_pages;
private:
	std::map<int, unsigned int> m_modifications;
	void processPESPacket(__u8 *pkt, int len);
	
	ePtr<iDVBPESReader> m_pes_reader;
	ePtr<eConnection> m_read_connection;
	
	eDVBTeletextSubtitlePage m_subtitle_page;
	
	int m_pid, m_page_M, m_page_X, m_page_open, m_double_height, m_box_open;
	
	void handlePageStart();
	void handleLine(unsigned char *line, int len);
	void handlePageEnd(int have_pts, const pts_t &pts);
	
	std::string m_subtitle_text;
	int m_subtitle_color;
	
	void addSubtitleString(int color, std::string string);
	
	void sendSubtitlePage();
	
	Signal1<void,const eDVBTeletextSubtitlePage&> m_new_subtitle_page;
};

#endif
