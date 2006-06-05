#ifndef __lib_dvb_teletext_h
#define __lib_dvb_teletext_h

#include <lib/base/object.h>
#include <lib/dvb/idvb.h>
#include <lib/dvb/pesparse.h>
#include <lib/gdi/gpixmap.h>

struct eDVBTeletextSubtitlePageElement
{
	gRGB m_color;
	std::string m_text;
	eDVBTeletextSubtitlePageElement(const gRGB &color, const std::string &text)
		: m_color(color), m_text(text)
	{
	}
};

struct eDVBTeletextSubtitlePage
{
	pts_t m_pts;
	int m_timeout; /* in pts */
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
	void setPage(int page);
	
	void connectNewPage(const Slot1<void,const eDVBTeletextSubtitlePage &> &slot, ePtr<eConnection> &connection);
	
	std::set<int> m_found_subtitle_pages;
private:
	void processPESPacket(__u8 *pkt, int len);
	
	ePtr<iDVBPESReader> m_pes_reader;
	ePtr<eConnection> m_read_connection;
	
	eDVBTeletextSubtitlePage m_subtitle_page;
	
	int m_M, m_Y, m_X, m_S1, m_S2, m_S3, m_S4, m_C;
	
	int m_page_M, m_page_X, m_page_open;
	
	void handlePageStart();
	void handleLine(unsigned char *line, int len);
	void handlePageEnd();
	
	std::string m_subtitle_text;
	int m_subtitle_color;
	
	void addSubtitleString(int color, const std::string &string);
	
	void sendSubtitlePage();
	
	Signal1<void,const eDVBTeletextSubtitlePage&> m_new_subtitle_page;
};

#endif
