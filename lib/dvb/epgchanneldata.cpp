#include <lib/dvb/epgchanneldata.h>

#include <lib/dvb/epgtransponderdatareader.h>
#include <lib/dvb/pmt.h>

#include <sstream>
#include <iomanip>


eEPGChannelData::eEPGChannelData(eEPGTransponderDataReader *ml)
	:epgReader(ml)
	,abortTimer(eTimer::create(ml)), zapTimer(eTimer::create(ml)), state(-2)
	,isRunning(0), haveData(0)
#ifdef ENABLE_PRIVATE_EPG
	,startPrivateTimer(eTimer::create(ml))
#endif
#ifdef ENABLE_MHW_EPG
	,m_MHWTimeoutTimer(eTimer::create(ml))
#endif
#ifdef ENABLE_OPENTV
	,m_OPENTV_Timer(eTimer::create(ml))
#endif
{
#ifdef ENABLE_MHW_EPG
	CONNECT(m_MHWTimeoutTimer->timeout, eEPGChannelData::MHWTimeout);
#endif
	CONNECT(zapTimer->timeout, eEPGChannelData::startEPG);
	CONNECT(abortTimer->timeout, eEPGChannelData::abortNonAvail);
#ifdef ENABLE_PRIVATE_EPG
	CONNECT(startPrivateTimer->timeout, eEPGChannelData::startPrivateReader);
#endif
#ifdef ENABLE_OPENTV
	CONNECT(m_OPENTV_Timer->timeout, eEPGChannelData::cleanupOPENTV);
#endif
	pthread_mutex_init(&channel_active, 0);
}

void eEPGChannelData::startChannel()
{
	pthread_mutex_lock(&channel_active);
	singleLock l(eEPGTransponderDataReader::last_channel_update_lock);
	updateMap::iterator It = epgReader->m_channelLastUpdated.find( channel->getChannelID() );

	int update = ( It != epgReader->m_channelLastUpdated.end() ? ( UPDATE_INTERVAL - ( (::time(0)-It->second) * 1000 ) ) : ZAP_DELAY );

	if (update < ZAP_DELAY)
		update = ZAP_DELAY;

	zapTimer->start(update, true);
	if (update >= 60000)
		eDebug("[eEPGChannelData] next update in %i min", update/60000);
	else if (update >= 1000)
		eDebug("[eEPGChannelData] next update in %i sec", update/1000);
}

/**
 * @brief Entry point for the EPG update timer
 *
 * @return void
 */
void eEPGChannelData::startEPG()
{
	eDebug("[eEPGChannelData] start reading events(%ld)", ::time(0));
	state=0;
	haveData=0;
	for (unsigned int i=0; i < sizeof(seenSections)/sizeof(tidMap); ++i)
	{
		seenSections[i].clear();
		calcedSections[i].clear();
	}
#ifdef ENABLE_MHW_EPG
		cleanupMHW();
#endif
#ifdef ENABLE_FREESAT
		cleanupFreeSat();
#endif
#ifdef ENABLE_OPENTV
		huffman_dictionary_read = false;
		cleanupOPENTV();
#endif
	eDVBSectionFilterMask mask;
	memset(&mask, 0, sizeof(mask));

#ifdef ENABLE_MHW_EPG
	if (eEPGCache::getInstance()->getEpgSources() & eEPGCache::MHW && m_MHWReader)
	{
		mask.pid = 0xD3;
		mask.data[0] = 0x91;
		mask.mask[0] = 0xFF;
		m_MHWReader->connectRead(sigc::mem_fun(*this, &eEPGChannelData::readMHWData), m_MHWConn);
		m_MHWReader->start(mask);
		isRunning |= eEPGCache::MHW;
		memcpy(&m_MHWFilterMask, &mask, sizeof(eDVBSectionFilterMask));

		mask.pid = m_mhw2_channel_pid;
		mask.data[0] = 0xC8;
		mask.mask[0] = 0xFF;
		mask.data[1] = 0;
		mask.mask[1] = 0xFF;
		if (eEPGCache::getInstance()->getEpgmaxdays() < 4)
		{
			m_MHWReader2->connectRead(sigc::mem_fun(*this, &eEPGChannelData::readMHWData2_old), m_MHWConn2);
		} else {
			m_MHWReader2->connectRead(sigc::mem_fun(*this, &eEPGChannelData::readMHWData2), m_MHWConn2);
		}
		m_MHWReader2->start(mask);
		isRunning |= eEPGCache::MHW;
		memcpy(&m_MHWFilterMask2, &mask, sizeof(eDVBSectionFilterMask));
		mask.data[1] = 0;
		mask.mask[1] = 0;
		m_MHWTimeoutet=false;
	}
#endif
#ifdef ENABLE_FREESAT
	if (eEPGCache::getInstance()->getEpgSources() & eEPGCache::FREESAT_SCHEDULE_OTHER && m_FreeSatScheduleOtherReader)
	{
		mask.pid = 3842;
		mask.flags = eDVBSectionFilterMask::rfCRC;
		mask.data[0] = 0x60;
		mask.mask[0] = 0xFE;
		m_FreeSatScheduleOtherReader->connectRead(sigc::mem_fun(*this, &eEPGChannelData::readFreeSatScheduleOtherData), m_FreeSatScheduleOtherConn);
		m_FreeSatScheduleOtherReader->start(mask);

		/*
		 * faster pid, available on ITV HD transponder.
		 * We rely on the fact that we have either of the two,
		 * never both. (both readers share the same data callback
		 * and status maps)
		 */
		mask.pid = 3003;
		m_FreeSatScheduleOtherReader2->connectRead(sigc::mem_fun(*this, &eEPGChannelData::readFreeSatScheduleOtherData), m_FreeSatScheduleOtherConn2);
		m_FreeSatScheduleOtherReader2->start(mask);
		isRunning |= eEPGCache::FREESAT_SCHEDULE_OTHER;
	}
#endif
	mask.pid = 0x12;
	mask.flags = eDVBSectionFilterMask::rfCRC;

	eDVBChannelID chid = channel->getChannelID();
	std::ostringstream epg_id;
	epg_id << std::hex << std::setfill('0') <<
		std::setw(0) << ((chid.dvbnamespace.get() & 0xffff0000) >> 16) <<
		std::setw(4) << chid.transport_stream_id.get() <<
		std::setw(4) << chid.original_network_id.get();

	std::map<std::string,int>::iterator it = epgReader->customeitpids.find(epg_id.str());
	if (it != epgReader->customeitpids.end())
	{
		mask.pid = it->second;
		eDebug("[eEPGChannelData] Using non-standard pid %#x", mask.pid);
	}

	if (eEPGCache::getInstance()->getEpgSources() & eEPGCache::NOWNEXT && m_NowNextReader)
	{
		mask.data[0] = 0x4E;
		mask.mask[0] = 0xFE;
		m_NowNextReader->connectRead(bind(sigc::mem_fun(*this, &eEPGChannelData::readData), (int)eEPGCache::NOWNEXT), m_NowNextConn);
		m_NowNextReader->start(mask);
		isRunning |= eEPGCache::NOWNEXT;
	}

	if (eEPGCache::getInstance()->getEpgSources() & eEPGCache::SCHEDULE && m_ScheduleReader)
	{
		mask.data[0] = 0x50;
		mask.mask[0] = 0xF0;
		m_ScheduleReader->connectRead(bind(sigc::mem_fun(*this, &eEPGChannelData::readData), (int)eEPGCache::SCHEDULE), m_ScheduleConn);
		m_ScheduleReader->start(mask);
		isRunning |= eEPGCache::SCHEDULE;
	}

	if (eEPGCache::getInstance()->getEpgSources() & eEPGCache::SCHEDULE_OTHER && m_ScheduleOtherReader)
	{
		mask.data[0] = 0x60;
		mask.mask[0] = 0xF0;
		m_ScheduleOtherReader->connectRead(bind(sigc::mem_fun(*this, &eEPGChannelData::readData), (int)eEPGCache::SCHEDULE_OTHER), m_ScheduleOtherConn);
		m_ScheduleOtherReader->start(mask);
		isRunning |= eEPGCache::SCHEDULE_OTHER;
	}

#ifdef ENABLE_VIRGIN
	if (eEPGCache::getInstance()->getEpgSources() & eEPGCache::VIRGIN_NOWNEXT && m_VirginNowNextReader)
	{
		mask.pid = 0x2bc;
		mask.data[0] = 0x4E;
		mask.mask[0] = 0xFE;
		m_VirginNowNextReader->connectRead(bind(sigc::mem_fun(*this, &eEPGChannelData::readData), (int)eEPGCache::VIRGIN_NOWNEXT), m_VirginNowNextConn);
		m_VirginNowNextReader->start(mask);
		isRunning |= eEPGCache::VIRGIN_NOWNEXT;
	}

	if (eEPGCache::getInstance()->getEpgSources() & eEPGCache::VIRGIN_SCHEDULE && m_VirginScheduleReader)
	{
		mask.pid = 0x2bc;
		mask.data[0] = 0x50;
		mask.mask[0] = 0xFE;
		m_VirginScheduleReader->connectRead(bind(sigc::mem_fun(*this, &eEPGChannelData::readData), (int)eEPGCache::VIRGIN_SCHEDULE), m_VirginScheduleConn);
		m_VirginScheduleReader->start(mask);
		isRunning |= eEPGCache::VIRGIN_SCHEDULE;
	}
#endif
#ifdef ENABLE_NETMED
	if (eEPGCache::getInstance()->getEpgSources() & eEPGCache::NETMED_SCHEDULE && m_NetmedScheduleReader)
	{
		mask.pid = 0x1388;
		mask.data[0] = 0x50;
		mask.mask[0] = 0xF0;
		m_NetmedScheduleReader->connectRead(bind(sigc::mem_fun(*this, &eEPGChannelData::readData), (int)eEPGCache::NETMED_SCHEDULE), m_NetmedScheduleConn);
		m_NetmedScheduleReader->start(mask);
		isRunning |= eEPGCache::NETMED_SCHEDULE;
	}

	if (eEPGCache::getInstance()->getEpgSources() & eEPGCache::NETMED_SCHEDULE_OTHER && m_NetmedScheduleOtherReader)
	{
		mask.pid = 0x1388;
		mask.data[0] = 0x60;
		mask.mask[0] = 0xF0;
		m_NetmedScheduleOtherReader->connectRead(bind(sigc::mem_fun(*this, &eEPGChannelData::readData), (int)eEPGCache::NETMED_SCHEDULE_OTHER), m_NetmedScheduleOtherConn);
		m_NetmedScheduleOtherReader->start(mask);
		isRunning |= eEPGCache::NETMED_SCHEDULE_OTHER;
	}
#endif
#ifdef ENABLE_ATSC
	if (eEPGCache::getInstance()->getEpgSources() & eEPGCache::ATSC_EIT && m_ATSC_MGTReader)
	{
		m_atsc_eit_index = 0;
		m_ATSC_MGTReader->connectRead(sigc::mem_fun(*this, &eEPGChannelData::ATSC_MGTsection), m_ATSC_MGTConn);
		m_ATSC_VCTReader->connectRead(sigc::mem_fun(*this, &eEPGChannelData::ATSC_VCTsection), m_ATSC_VCTConn);
		m_ATSC_EITReader->connectRead(sigc::mem_fun(*this, &eEPGChannelData::ATSC_EITsection), m_ATSC_EITConn);
		m_ATSC_ETTReader->connectRead(sigc::mem_fun(*this, &eEPGChannelData::ATSC_ETTsection), m_ATSC_ETTConn);
		mask.pid = 0x1ffb;
		mask.data[0] = 0xc7;
		mask.mask[0] = 0xff;
		m_ATSC_MGTReader->start(mask);
		mask.pid = 0x1ffb;
		mask.data[0] = 0xc8;
		mask.mask[0] = 0xfe;
		m_ATSC_VCTReader->start(mask);
		isRunning |= eEPGCache::ATSC_EIT;
	}
#endif
#ifdef ENABLE_OPENTV
	if (eEPGCache::getInstance()->getEpgSources() & eEPGCache::OPENTV && m_OPENTV_ChannelsReader)
	{
		char dictionary[256];
		memset(dictionary, '\0', 256);

		//load correct EPG dictionary data "otv_namespace_onid_tsid.dict"
		sprintf (dictionary, "/usr/share/enigma2/otv_%08x_%04x_%04x.dict",
			(chid.dvbnamespace.get() >> 16) << 16, // without subnet
			chid.original_network_id.get(),
			chid.transport_stream_id.get());

		huffman_dictionary_read = huffman_read_dictionary(dictionary);

		if (huffman_dictionary_read)
		{
			m_OPENTV_EIT_index = m_OPENTV_crc32 = 0;
			m_OPENTV_ChannelsReader->connectRead(sigc::mem_fun(*this, &eEPGChannelData::OPENTV_ChannelsSection), m_OPENTV_ChannelsConn);
			mask.pid = 0x11;
			mask.data[0] = 0x4a;
			mask.mask[0] = 0xff;
			m_OPENTV_ChannelsReader->start(mask);
			isRunning |= eEPGCache::OPENTV;
		}
		else
			eDebug("[eEPGChannelData] abort non avail OpenTV EIT reading");
	}
#endif
	if (eEPGCache::getInstance()->getEpgSources() & eEPGCache::VIASAT && m_ViasatReader)
	{
		mask.pid = 0x39;

		mask.data[0] = 0x40;
		mask.mask[0] = 0x40;
		m_ViasatReader->connectRead(bind(sigc::mem_fun(*this, &eEPGChannelData::readData), (int)eEPGCache::VIASAT), m_ViasatConn);
		m_ViasatReader->start(mask);
		isRunning |= eEPGCache::VIASAT;
	}
#ifdef ENABLE_OPENTV
	if ( isRunning & eEPGCache::OPENTV )
		abortTimer->start(27000,true);
	else
#endif
		abortTimer->start(7000,true);
}

void eEPGChannelData::finishEPG()
{
	if (!isRunning)  // epg ready
	{
		eDebug("[eEPGChannelData] stop caching events(%ld)", ::time(0));
		zapTimer->start(UPDATE_INTERVAL, 1);
		eDebug("[eEPGChannelData] next update in %i min", UPDATE_INTERVAL / 60000);
		for (unsigned int i=0; i < sizeof(seenSections)/sizeof(tidMap); ++i)
		{
			seenSections[i].clear();
			calcedSections[i].clear();
		}
#ifdef ENABLE_MHW_EPG
		cleanupMHW();
#endif
#ifdef ENABLE_FREESAT
		cleanupFreeSat();
#endif
#ifdef ENABLE_OPENTV
		cleanupOPENTV();
#endif
		singleLock l(eEPGTransponderDataReader::last_channel_update_lock);
		epgReader->m_channelLastUpdated[channel->getChannelID()] = ::time(0);
	}
}

void eEPGChannelData::abortEPG()
{
	for (unsigned int i=0; i < sizeof(seenSections)/sizeof(tidMap); ++i)
	{
		seenSections[i].clear();
		calcedSections[i].clear();
	}
#ifdef ENABLE_MHW_EPG
	cleanupMHW();
#endif
#ifdef ENABLE_FREESAT
	cleanupFreeSat();
#endif
	abortTimer->stop();
	zapTimer->stop();
	if (isRunning)
	{
		eDebug("[eEPGChannelData] abort caching events !!");
		if (isRunning & eEPGCache::SCHEDULE)
		{
			isRunning &= ~eEPGCache::SCHEDULE;
			m_ScheduleReader->stop();
			m_ScheduleConn=0;
		}
		if (isRunning & eEPGCache::NOWNEXT)
		{
			isRunning &= ~eEPGCache::NOWNEXT;
			m_NowNextReader->stop();
			m_NowNextConn=0;
		}
		if (isRunning & eEPGCache::SCHEDULE_OTHER)
		{
			isRunning &= ~eEPGCache::SCHEDULE_OTHER;
			m_ScheduleOtherReader->stop();
			m_ScheduleOtherConn=0;
		}
#ifdef ENABLE_VIRGIN
		if (isRunning & eEPGCache::VIRGIN_NOWNEXT)
		{
			isRunning &= ~eEPGCache::VIRGIN_NOWNEXT;
			m_VirginNowNextReader->stop();
			m_VirginNowNextConn=0;
		}
		if (isRunning & eEPGCache::VIRGIN_SCHEDULE)
		{
			isRunning &= ~eEPGCache::VIRGIN_SCHEDULE;
			m_VirginScheduleReader->stop();
			m_VirginScheduleConn=0;
		}
#endif
#ifdef ENABLE_NETMED
		if (isRunning & eEPGCache::NETMED_SCHEDULE)
		{
			isRunning &= ~eEPGCache::NETMED_SCHEDULE;
			m_NetmedScheduleReader->stop();
			m_NetmedScheduleConn=0;
		}
		if (isRunning & eEPGCache::NETMED_SCHEDULE_OTHER)
		{
			isRunning &= ~eEPGCache::NETMED_SCHEDULE_OTHER;
			m_NetmedScheduleOtherReader->stop();
			m_NetmedScheduleOtherConn=0;
		}
#endif
#ifdef ENABLE_FREESAT
		if (isRunning & eEPGCache::FREESAT_SCHEDULE_OTHER)
		{
			isRunning &= ~eEPGCache::FREESAT_SCHEDULE_OTHER;
			m_FreeSatScheduleOtherReader->stop();
			m_FreeSatScheduleOtherReader2->stop();
			m_FreeSatScheduleOtherConn=0;
			m_FreeSatScheduleOtherConn2=0;
		}
#endif
		if (isRunning & eEPGCache::VIASAT)
		{
			isRunning &= ~eEPGCache::VIASAT;
			m_ViasatReader->stop();
			m_ViasatConn=0;
		}
#ifdef ENABLE_MHW_EPG
		if (isRunning & eEPGCache::MHW)
		{
			isRunning &= ~eEPGCache::MHW;
			m_MHWReader->stop();
			m_MHWConn=0;
			m_MHWReader2->stop();
			m_MHWConn2=0;
		}
#endif
#ifdef ENABLE_ATSC
		if (isRunning & eEPGCache::ATSC_EIT)
		{
			isRunning &= ~eEPGCache::ATSC_EIT;
			cleanupATSC();
		}
#endif
#ifdef ENABLE_OPENTV
		if (isRunning & eEPGCache::OPENTV)
		{
			isRunning &= ~eEPGCache::OPENTV;
			cleanupOPENTV();
		}
#endif
	}
#ifdef ENABLE_PRIVATE_EPG
	if (m_PrivateReader)
		m_PrivateReader->stop();
	if (m_PrivateConn)
		m_PrivateConn=0;
#endif
	pthread_mutex_unlock(&channel_active);
}

void eEPGChannelData::readData( const uint8_t *data, int source)
{
	int map;
	iDVBSectionReader *reader = NULL;
#ifdef __sh__
/* Dagobert: this is still very hacky, but currently I cant find
 * the origin of the readData call. I think the caller is
 * responsible for the unaligned data pointer in this call.
 * So we malloc our own memory here which _should_ be aligned.
 *
 * TODO: We should search for the origin of this call. As I
 * said before I need an UML Diagram or must try to import
 * e2 and all libs into an IDE for better overview ;)
 *
 */
	const uint8_t *aligned_data;
	bool isNotAligned = false;

	if ((unsigned int) data % 4 != 0)
		isNotAligned = true;

	if (isNotAligned)
	{
		int len = ((data[1] & 0x0F) << 8 | data[2]) -1;

		/*eDebug("[eEPGChannelData] len %d %x, %x %x\n", len, len, data[1], data[2]);*/

		if ( EIT_SIZE >= len )
			return;

		aligned_data = (const uint8_t *) malloc(len);

		if ((unsigned int)aligned_data % 4 != 0)
		{
			eDebug("[eEPGChannelData] eEPGChannelData::readData: ERRORERRORERROR: unaligned data pointer %p\n", aligned_data);
		}

		/*eDebug("%p %p\n", aligned_data, data); */
		memcpy((void *) aligned_data, (const uint8_t *) data, len);
		data = aligned_data;
	}
#endif
	switch (source)
	{
		case eEPGCache::NOWNEXT:
			reader = m_NowNextReader;
			map = 0;
			break;
		case eEPGCache::SCHEDULE:
			reader = m_ScheduleReader;
			map = 1;
			break;
		case eEPGCache::SCHEDULE_OTHER:
			reader = m_ScheduleOtherReader;
			map = 2;
			break;
		case eEPGCache::VIASAT:
			reader = m_ViasatReader;
			map = 3;
			break;
#ifdef ENABLE_NETMED
		case eEPGCache::NETMED_SCHEDULE:
			reader = m_NetmedScheduleReader;
			map = 1;
			break;
		case eEPGCache::NETMED_SCHEDULE_OTHER:
			reader = m_NetmedScheduleOtherReader;
			map = 2;
			break;
#endif
#ifdef ENABLE_VIRGIN
		case eEPGCache::VIRGIN_NOWNEXT:
			reader = m_VirginNowNextReader;
			map = 0;
			break;
		case eEPGCache::VIRGIN_SCHEDULE:
			reader = m_VirginScheduleReader;
			map = 1;
			break;
#endif
		default:
			eDebug("[eEPGChannelData] unknown source");
			return;
	}
	tidMap &seenSections = this->seenSections[map];
	tidMap &calcedSections = this->calcedSections[map];
	if ( (state == 1 && calcedSections == seenSections) || state > 1 )
	{
		eDebugNoNewLineStart("[eEPGChannelData] ");
		switch (source)
		{
			case eEPGCache::NOWNEXT:
				m_NowNextConn=0;
				eDebugNoNewLine("nownext");
				break;
			case eEPGCache::SCHEDULE:
				m_ScheduleConn=0;
				eDebugNoNewLine("schedule");
				break;
			case eEPGCache::SCHEDULE_OTHER:
				m_ScheduleOtherConn=0;
				eDebugNoNewLine("schedule other");
				break;
			case eEPGCache::VIASAT:
				m_ViasatConn=0;
				eDebugNoNewLine("viasat");
				break;
#ifdef ENABLE_NETMED
			case eEPGCache::NETMED_SCHEDULE:
				m_NetmedScheduleConn=0;
				eDebugNoNewLine("netmed schedule");
				break;
			case eEPGCache::NETMED_SCHEDULE_OTHER:
				m_NetmedScheduleOtherConn=0;
				eDebugNoNewLine("netmed schedule other");
				break;
#endif
#ifdef ENABLE_VIRGIN
			case eEPGCache::VIRGIN_NOWNEXT:
				m_VirginNowNextConn=0;
				eDebugNoNewLine("virgin nownext");
				break;
			case eEPGCache::VIRGIN_SCHEDULE:
				m_VirginScheduleConn=0;
				eDebugNoNewLine("virgin schedule");
				break;
#endif
			default: eDebugNoNewLine("unknown");break;
		}
		eDebugNoNewLine(" finished(%ld)\n", ::time(0));
		if ( reader )
			reader->stop();
		isRunning &= ~source;
		if (!isRunning)
			finishEPG();
	}
	else
	{
		eit_t *eit = (eit_t*) data;
		uint32_t sectionNo = data[0] << 24;
		sectionNo |= data[3] << 16;
		sectionNo |= data[4] << 8;
		sectionNo |= eit->section_number;

		tidMap::iterator it =
			seenSections.find(sectionNo);

		if ( it == seenSections.end() )
		{
			seenSections.insert(sectionNo);
			calcedSections.insert(sectionNo);
			uint32_t tmpval = sectionNo & 0xFFFFFF00;
			uint8_t incr = source == eEPGCache::NOWNEXT ? 1 : 8;
			for ( int i = 0; i <= eit->last_section_number; i+=incr )
			{
				if ( i == eit->section_number )
				{
					for (int x=i; x <= eit->segment_last_section_number; ++x)
						calcedSections.insert(tmpval|(x&0xFF));
				}
				else
					calcedSections.insert(tmpval|(i&0xFF));
			}
			if (eEPGCache::getInstance())
				eEPGCache::getInstance()->sectionRead(data, source, this);
		}
	}
#ifdef __sh__
	if (isNotAligned)
		free((void *)aligned_data);
#endif
}

void eEPGChannelData::abortNonAvail()
{
	if (!state)
	{
		if ( !(haveData & eEPGCache::NOWNEXT) && (isRunning & eEPGCache::NOWNEXT) )
		{
			eDebug("[eEPGChannelData] abort non avail nownext reading");
			isRunning &= ~eEPGCache::NOWNEXT;
			m_NowNextReader->stop();
			m_NowNextConn=0;
		}
		if ( !(haveData & eEPGCache::SCHEDULE) && (isRunning & eEPGCache::SCHEDULE) )
		{
			eDebug("[eEPGChannelData] abort non avail schedule reading");
			isRunning &= ~eEPGCache::SCHEDULE;
			m_ScheduleReader->stop();
			m_ScheduleConn=0;
		}
		if ( !(haveData & eEPGCache::SCHEDULE_OTHER) && (isRunning & eEPGCache::SCHEDULE_OTHER) )
		{
			eDebug("[eEPGChannelData] abort non avail schedule other reading");
			isRunning &= ~eEPGCache::SCHEDULE_OTHER;
			m_ScheduleOtherReader->stop();
			m_ScheduleOtherConn=0;
		}
#ifdef ENABLE_VIRGIN
		if ( !(haveData & eEPGCache::VIRGIN_NOWNEXT) && (isRunning & eEPGCache::VIRGIN_NOWNEXT) )
		{
			eDebug("[eEPGChannelData] abort non avail virgin nownext reading");
			isRunning &= ~eEPGCache::VIRGIN_NOWNEXT;
			m_VirginNowNextReader->stop();
			m_VirginNowNextConn=0;
		}
		if ( !(haveData & eEPGCache::VIRGIN_SCHEDULE) && (isRunning & eEPGCache::VIRGIN_SCHEDULE) )
		{
			eDebug("[eEPGChannelData] abort non avail virgin schedule reading");
			isRunning &= ~eEPGCache::VIRGIN_SCHEDULE;
			m_VirginScheduleReader->stop();
			m_VirginScheduleConn=0;
		}
#endif
#ifdef ENABLE_NETMED
		if ( !(haveData & eEPGCache::NETMED_SCHEDULE) && (isRunning & eEPGCache::NETMED_SCHEDULE) )
		{
			eDebug("[eEPGChannelData] abort non avail netmed schedule reading");
			isRunning &= ~eEPGCache::NETMED_SCHEDULE;
			m_NetmedScheduleReader->stop();
			m_NetmedScheduleConn=0;
		}
		if ( !(haveData & eEPGCache::NETMED_SCHEDULE_OTHER) && (isRunning & eEPGCache::NETMED_SCHEDULE_OTHER) )
		{
			eDebug("[eEPGChannelData] abort non avail netmed schedule other reading");
			isRunning &= ~eEPGCache::NETMED_SCHEDULE_OTHER;
			m_NetmedScheduleOtherReader->stop();
			m_NetmedScheduleOtherConn=0;
		}
#endif
#ifdef ENABLE_FREESAT
		if ( !(haveData & eEPGCache::FREESAT_SCHEDULE_OTHER) && (isRunning & eEPGCache::FREESAT_SCHEDULE_OTHER) )
		{
			eDebug("[eEPGChannelData] abort non avail FreeSat schedule_other reading");
			isRunning &= ~eEPGCache::FREESAT_SCHEDULE_OTHER;
			m_FreeSatScheduleOtherReader->stop();
			m_FreeSatScheduleOtherReader2->stop();
			m_FreeSatScheduleOtherConn=0;
			m_FreeSatScheduleOtherConn2=0;
			cleanupFreeSat();
		}
#endif
		if ( !(haveData & eEPGCache::VIASAT) && (isRunning & eEPGCache::VIASAT) )
		{
			eDebug("[eEPGChannelData] abort non avail viasat reading");
			isRunning &= ~eEPGCache::VIASAT;
			m_ViasatReader->stop();
			m_ViasatConn=0;
		}
#ifdef ENABLE_MHW_EPG
		if ( !(haveData & eEPGCache::MHW) && (isRunning & eEPGCache::MHW) )
		{
			eDebug("[eEPGChannelData] abort non avail mhw reading");
			isRunning &= ~eEPGCache::MHW;
			m_MHWReader->stop();
			m_MHWConn=0;
			m_MHWReader2->stop();
			m_MHWConn2=0;
		}
#endif
#ifdef ENABLE_ATSC
		if (!(haveData & eEPGCache::ATSC_EIT) && (isRunning & eEPGCache::ATSC_EIT))
		{
			eDebug("[eEPGChannelData] abort non avail ATSC EIT reading");
			isRunning &= ~eEPGCache::ATSC_EIT;
			cleanupATSC();
		}
#endif
#ifdef ENABLE_OPENTV
		if (!(haveData & eEPGCache::OPENTV) && (isRunning & eEPGCache::OPENTV))
		{
			eDebug("[eEPGChannelData] abort non avail OpenTV EIT reading");
			isRunning &= ~eEPGCache::OPENTV;
			cleanupOPENTV();
		}
#endif
		if ( isRunning & eEPGCache::VIASAT )
			abortTimer->start(300000, true);
		else if ( isRunning & eEPGCache::MHW )
			abortTimer->start(500000, true);
		else if ( isRunning )
			abortTimer->start(90000, true);
		else
		{
			++state;
			for (unsigned int i=0; i < sizeof(seenSections)/sizeof(tidMap); ++i)
			{
				seenSections[i].clear();
				calcedSections[i].clear();
			}
#ifdef ENABLE_MHW_EPG
			cleanupMHW();
#endif
#ifdef ENABLE_FREESAT
			cleanupFreeSat();
#endif
#ifdef ENABLE_OPENTV
			cleanupOPENTV();
#endif
		}
	}
	++state;
}


#ifdef ENABLE_PRIVATE_EPG
void eEPGChannelData::startPrivateReader()
{
	eDVBSectionFilterMask mask;
	memset(&mask, 0, sizeof(mask));
	mask.pid = m_PrivatePid;
	mask.flags = eDVBSectionFilterMask::rfCRC;
	mask.data[0] = 0xA0;
	mask.mask[0] = 0xFF;
	eDebug("[eEPGChannelData] start privatefilter for pid %04x and version %d", m_PrivatePid, m_PrevVersion);
	if (m_PrevVersion != -1)
	{
		mask.data[3] = m_PrevVersion << 1;
		mask.mask[3] = 0x3E;
		mask.mode[3] = 0x3E;
	}
	seenPrivateSections.clear();
	if (!m_PrivateConn)
		m_PrivateReader->connectRead(sigc::mem_fun(*this, &eEPGChannelData::readPrivateData), m_PrivateConn);
	m_PrivateReader->start(mask);
}

void eEPGChannelData::readPrivateData( const uint8_t *data)
{
	if ( seenPrivateSections.find(data[6]) == seenPrivateSections.end() )
	{
		if (eEPGCache::getInstance())
			eEPGCache::getInstance()->privateSectionRead(m_PrivateService, data);
		seenPrivateSections.insert(data[6]);
	}
	if ( seenPrivateSections.size() == (unsigned int)(data[7] + 1) )
	{
		eDebug("[eEPGChannelData] private finished");
		eDVBChannelID chid = channel->getChannelID();
		int tmp = chid.original_network_id.get();
		tmp |= 0x80000000; // we use highest bit as private epg indicator
		chid.original_network_id = tmp;
		singleLock l(eEPGTransponderDataReader::last_channel_update_lock);
		epgReader->m_channelLastUpdated[chid] = ::time(0);
		m_PrevVersion = (data[5] & 0x3E) >> 1;
		startPrivateReader();
	}
}

#endif // ENABLE_PRIVATE_EPG


#ifdef ENABLE_MHW_EPG
static FILE *log_file = NULL;
uint32_t nbr_summary;
std::map<uint32_t, uint32_t> m_titlesID;

void eEPGChannelData::cleanupMHW()
{
	m_MHWTimeoutTimer->stop();
	m_channels.clear();
	m_themes.clear();
	m_titles.clear();
	m_titlesID.clear();
	m_program_ids.clear();
}

uint8_t *eEPGChannelData::delimitName( uint8_t *in, uint8_t *out, int len_in )
{
	// Names in mhw structs are not strings as they are not '\0' terminated.
	// This function converts the mhw name into a string.
	// Constraint: "length of out" = "length of in" + 1.
	int i;
	for ( i=0; i < len_in; i++ )
		out[i] = in[i];

	i = len_in - 1;
	while ( ( i >=0 ) && ( out[i] == 0x20 ) )
		i--;

	out[i+1] = 0;
	return out;
}

void eEPGChannelData::timeMHW2DVB( u_char hours, u_char minutes, u_char *return_time)
// For time of day
{
	return_time[0] = toBCD( hours );
	return_time[1] = toBCD( minutes );
	return_time[2] = 0;
}

void eEPGChannelData::timeMHW2DVB( int minutes, u_char *return_time)
{
	timeMHW2DVB( int(minutes/60), minutes%60, return_time );
}

void eEPGChannelData::timeMHW2DVB( u_char day, u_char hours, u_char minutes, u_char *return_time)
// For date plus time of day
{
	char tz_saved[1024];
	// Remove offset in mhw time.
	uint8_t local_hours = hours;
	if ( hours >= 16 )
		local_hours -= 4;
	else if ( hours >= 8 )
		local_hours -= 2;

	// As far as we know all mhw time data is sent in central Europe time zone.
	// So, temporarily set timezone to western europe
	time_t dt = ::time(0);

	char *old_tz = getenv( "TZ" );
	if (old_tz)
		strcpy(tz_saved, old_tz);
	putenv((char*)"TZ=CET-1CEST,M3.5.0/2,M10.5.0/3");
	tzset();

	tm localnow;
	localtime_r(&dt, &localnow);

	if (day == 7)
		day = 0;
	if ( day + 1 < localnow.tm_wday )		// day + 1 to prevent old events to show for next week.
		day += 7;
	if (local_hours <= 5)
		day++;

	dt += 3600*24*(day - localnow.tm_wday);	// Shift dt to the recording date (local time zone).
	dt += 3600*(local_hours - localnow.tm_hour);  // Shift dt to the recording hour.

	tm recdate;
	gmtime_r( &dt, &recdate );   // This will also take care of DST.

	if ( old_tz == NULL )
		unsetenv( "TZ" );
	else
		setenv("TZ", tz_saved, 1);
	tzset();

	// Calculate MJD according to annex in ETSI EN 300 468
	int l=0;
	if ( recdate.tm_mon <= 1 )	// Jan or Feb
		l=1;
	int mjd = 14956 + recdate.tm_mday + int( (recdate.tm_year - l) * 365.25) +
		int( (recdate.tm_mon + 2 + l * 12) * 30.6001);

	return_time[0] = (mjd & 0xFF00)>>8;
	return_time[1] = mjd & 0xFF;

	timeMHW2DVB( recdate.tm_hour, minutes, return_time+2 );
}

void eEPGChannelData::storeMHWTitle(std::map<uint32_t, mhw_title_t>::iterator itTitle, std::string sumText, const uint8_t *data)
// data is borrowed from calling proc to save memory space.
{
	uint8_t name[34];

	// For each title a separate EIT packet will be sent to eEPGCache::sectionRead()
	bool isMHW2 = itTitle->second.mhw2_mjd_hi || itTitle->second.mhw2_mjd_lo ||
		itTitle->second.mhw2_duration_hi || itTitle->second.mhw2_duration_lo;

	eit_t *packet = (eit_t *) data;
	packet->table_id = 0x50;
	packet->section_syntax_indicator = 1;

	packet->service_id_hi = m_channels[ itTitle->second.channel_id - 1 ].channel_id_hi;
	packet->service_id_lo = m_channels[ itTitle->second.channel_id - 1 ].channel_id_lo;
	packet->version_number = 0;	// eEPGCache::sectionRead() will dig this for the moment
	packet->current_next_indicator = 0;
	packet->section_number = 0;	// eEPGCache::sectionRead() will dig this for the moment
	packet->last_section_number = 0;	// eEPGCache::sectionRead() will dig this for the moment
	packet->transport_stream_id_hi = m_channels[ itTitle->second.channel_id - 1 ].transport_stream_id_hi;
	packet->transport_stream_id_lo = m_channels[ itTitle->second.channel_id - 1 ].transport_stream_id_lo;
	packet->original_network_id_hi = m_channels[ itTitle->second.channel_id - 1 ].network_id_hi;
	packet->original_network_id_lo = m_channels[ itTitle->second.channel_id - 1 ].network_id_lo;
	packet->segment_last_section_number = 0; // eEPGCache::sectionRead() will dig this for the moment
	packet->segment_last_table_id = 0x50;

	uint8_t *title = isMHW2 ? ((uint8_t*)(itTitle->second.title))-4 : (uint8_t*)itTitle->second.title;
	std::string prog_title = (char *) delimitName( title, name, isMHW2 ? 35 : 23 );
	int prog_title_length = prog_title.length();

	int packet_length = EIT_SIZE + EIT_LOOP_SIZE + EIT_SHORT_EVENT_DESCRIPTOR_SIZE +
		prog_title_length + 1;

	eit_event_t *event_data = (eit_event_t *) (data + EIT_SIZE);
	event_data->event_id_hi = (( itTitle->first ) >> 8 ) & 0xFF;
	event_data->event_id_lo = ( itTitle->first ) & 0xFF;

	if (isMHW2)
	{
		u_char *data = (u_char*) event_data;
		data[2] = itTitle->second.mhw2_mjd_hi;
		data[3] = itTitle->second.mhw2_mjd_lo;
		data[4] = itTitle->second.mhw2_hours;
		data[5] = itTitle->second.mhw2_minutes;
		data[6] = itTitle->second.mhw2_seconds;
		timeMHW2DVB( itTitle->second.getMhw2Duration(), data+7 );
	}
	else
	{
		timeMHW2DVB( itTitle->second.dh.day, itTitle->second.dh.hours, itTitle->second.ms.minutes,
		(u_char *) event_data + 2 );
		timeMHW2DVB( itTitle->second.getDuration(), (u_char *) event_data+7 );
	}

	event_data->running_status = 0;
	event_data->free_CA_mode = 0;
	int descr_ll = EIT_SHORT_EVENT_DESCRIPTOR_SIZE + 1 + prog_title_length;

	eit_short_event_descriptor_struct *short_event_descriptor =
		(eit_short_event_descriptor_struct *) ( (u_char *) event_data + EIT_LOOP_SIZE);
	short_event_descriptor->descriptor_tag = EIT_SHORT_EVENT_DESCRIPTOR;
	short_event_descriptor->descriptor_length = EIT_SHORT_EVENT_DESCRIPTOR_SIZE +
		prog_title_length - 1;
	short_event_descriptor->language_code_1 = 'e';
	short_event_descriptor->language_code_2 = 'n';
	short_event_descriptor->language_code_3 = 'g';
	short_event_descriptor->event_name_length = prog_title_length;
	u_char *event_name = (u_char *) short_event_descriptor + EIT_SHORT_EVENT_DESCRIPTOR_SIZE;
	memcpy(event_name, prog_title.c_str(), prog_title_length);

	// Set text length
	event_name[prog_title_length] = 0;

	if ( sumText.length() > 0 )
	// There is summary info
	{
		unsigned int sum_length = sumText.length();
		if ( sum_length + short_event_descriptor->descriptor_length <= 0xff )
		// Store summary in short event descriptor
		{
			// Increase all relevant lengths
			event_name[prog_title_length] = sum_length;
			short_event_descriptor->descriptor_length += sum_length;
			packet_length += sum_length;
			descr_ll += sum_length;
			sumText.copy( (char *) event_name+prog_title_length+1, sum_length );
		}
		else
		// Store summary in extended event descriptors
		{
			int remaining_sum_length = sumText.length();
			int nbr_descr = int(remaining_sum_length/247) + 1;
			for ( int i=0; i < nbr_descr; i++)
			// Loop once per extended event descriptor
			{
				eit_extended_descriptor_struct *ext_event_descriptor = (eit_extended_descriptor_struct *) (data + packet_length);
				sum_length = remaining_sum_length > 247 ? 247 : remaining_sum_length;
				remaining_sum_length -= sum_length;
				packet_length += 8 + sum_length;
				descr_ll += 8 + sum_length;

				ext_event_descriptor->descriptor_tag = EIT_EXTENDED_EVENT_DESCRIPOR;
				ext_event_descriptor->descriptor_length = sum_length + 6;
				ext_event_descriptor->descriptor_number = i;
				ext_event_descriptor->last_descriptor_number = nbr_descr - 1;
				ext_event_descriptor->iso_639_2_language_code_1 = 'e';
				ext_event_descriptor->iso_639_2_language_code_2 = 'n';
				ext_event_descriptor->iso_639_2_language_code_3 = 'g';
				u_char *the_text = (u_char *) ext_event_descriptor + 8;
				the_text[-2] = 0;
				the_text[-1] = sum_length;
				sumText.copy( (char *) the_text, sum_length, sumText.length() - sum_length - remaining_sum_length );
			}
		}
	}

	if (!isMHW2)
	{
		// Add content descriptor
		u_char *descriptor = (u_char *) data + packet_length;
		packet_length += 4;
		descr_ll += 4;

		int content_id = 0;
		std::string content_descr = (char *) delimitName( m_themes[itTitle->second.theme_id].name, name, 15 );
		if ( content_descr.find( "FILM" ) != std::string::npos )
			content_id = 0x10;
		else if ( content_descr.find( "SPORT" ) != std::string::npos )
			content_id = 0x40;

		descriptor[0] = 0x54;
		descriptor[1] = 2;
		descriptor[2] = content_id;
		descriptor[3] = 0;
	}
	else
		{
		// Add content descriptor
		u_char *descriptor = (u_char *) data + packet_length;
		packet_length += 4;
		descr_ll += 4;

		u_char content_id = 0;

		if (eEPGCache::getInstance()->getEpgmaxdays() < 4)
		{
			switch (itTitle->second.mhw2_theme)  // convert to standar theme
			{
			case 0x0: content_id = 0x10;break;  // Cine 
			case 0x1: content_id = 0x40;break; // Deportes
			case 0x2: content_id = 0x10;break; // Series
			case 0x3: content_id = 0x50;break; // Infantiles
			case 0x20: content_id = 0x70;break;
			case 0x21: content_id = 0x80;break;
			case 0x22: content_id = 0x70;break;
			case 0x23: content_id = 0x80;break;
			case 0x24: content_id = 0x90;break;
			case 0x25: content_id = 0x90;break;
			case 0x26: content_id = 0x70;break;
			case 0x27: content_id = 0x80;break;
			case 0x28: content_id = 0x80;break;
			case 0x29: content_id = 0x70;break;
			case 0x2A: content_id = 0x90;break;
			case 0x2B: content_id = 0x80;break;
			case 0x2C: content_id = 0x90;break;
			case 0x2D: content_id = 0x80;break;
			case 0x2E: content_id = 0x80;break;
			case 0x2F: content_id = 0x90;break;
			case 0x30: content_id = 0x70;break;
			case 0x5: content_id = 0x60;break; // Musica
			case 0x6: content_id = 0x20;break; // informacion
			case 0x7: content_id = 0x30;break; // Entretenimiento
			case 0x8: content_id = 0xA0;break; // Ocio
			case 0x40: content_id = 0x90;break;
			case 0x41: content_id = 0x70;break;
			case 0x42: content_id = 0x70;break;
			case 0x43: content_id = 0x90;break;
			case 0x44: content_id = 0x90;break;
			case 0x45: content_id = 0x70;break;
			case 0x46: content_id = 0x70;break;
			case 0x47: content_id = 0x70;break;
			case 0x48: content_id = 0x70;break;
			case 0x49: content_id = 0x90;break;
			case 0x4A: content_id = 0x70;break;
			case 0x4B: content_id = 0x90;break;
			case 0x4C: content_id = 0x70;break;
			case 0x4D: content_id = 0x90;break;
			case 0xA: content_id = 0xB0;break; // Otros
			default: content_id = 0xB0;
			}
		} else {
			switch (itTitle->second.mhw2_theme)  // convert to standar theme
			{
			// New clasification for 7 days epg
			case 0x0: content_id = 0x10;break;  // Cine 
			case 0x10: content_id = 0x10;break; // Cine
			case 0x20: content_id = 0x10;break; // Series
			case 0x30: content_id = 0x20;break; // Informacion
			case 0x40: content_id = 0x30;break; // Entretenimiento
			case 0x50: content_id = 0x40;break; // Deportes
			case 0x60: content_id = 0x50;break; // infantiles
			case 0x70: content_id = 0x60;break; // Musica
			case 0x80: content_id = 0x91;break; // Documentales / Educacion
			case 0x90: content_id = 0x70;break; // Cultura
			case 0xA0: content_id = 0xA0;break; // Ocio
			default: content_id = 0x0F;
			}
		}


		descriptor[0] = 0x54;
		descriptor[1] = 2;
		descriptor[2] = content_id;
		descriptor[3] = 0;
	}

	event_data->descriptors_loop_length_hi = (descr_ll & 0xf00)>>8;
	event_data->descriptors_loop_length_lo = (descr_ll & 0xff);

	packet->section_length_hi =  ((packet_length - 3)&0xf00)>>8;
	packet->section_length_lo =  (packet_length - 3)&0xff;

	// Feed the data to eEPGCache::sectionRead()
	if (eEPGCache::getInstance())
		eEPGCache::getInstance()->sectionRead( data, eEPGCache::MHW, this );

	int i;
	for (i=0;i<nb_equiv;i++)
	{
		if (( m_channels[ itTitle->second.channel_id - 1 ].channel_id_hi == m_equiv[i].original_sid_hi )
			&& ( m_channels[ itTitle->second.channel_id - 1 ].transport_stream_id_hi == m_equiv[i].original_tid_hi )
			&& ( m_channels[ itTitle->second.channel_id - 1 ].network_id_hi == m_equiv[i].original_nid_hi )
			&& ( m_channels[ itTitle->second.channel_id - 1 ].channel_id_lo == m_equiv[i].original_sid_lo )
			&& ( m_channels[ itTitle->second.channel_id - 1 ].transport_stream_id_lo == m_equiv[i].original_tid_lo )
			&& ( m_channels[ itTitle->second.channel_id - 1 ].network_id_lo == m_equiv[i].original_nid_lo ))
		{
			packet->service_id_hi = m_equiv[i].equiv_sid_hi;
			packet->transport_stream_id_hi = m_equiv[i].equiv_tid_hi;
			packet->original_network_id_hi = m_equiv[i].equiv_nid_hi;
			packet->service_id_lo = m_equiv[i].equiv_sid_lo;
			packet->transport_stream_id_lo = m_equiv[i].equiv_tid_lo;
			packet->original_network_id_lo = m_equiv[i].equiv_nid_lo;
			if (eEPGCache::getInstance())
				eEPGCache::getInstance()->sectionRead( data, eEPGCache::MHW, this );
		}
	}

}

void eEPGChannelData::startMHWTimeout(int msec)
{
	m_MHWTimeoutTimer->start(msec,true);
	m_MHWTimeoutet=false;
}

void eEPGChannelData::startMHWReader(uint16_t pid, uint8_t tid)
{
	m_MHWFilterMask.pid = pid;
	m_MHWFilterMask.data[0] = tid;
	m_MHWReader->start(m_MHWFilterMask);
//	eDebug("[eEPGChannelData] start 0x%02x 0x%02x", pid, tid);
}

void eEPGChannelData::startMHWReader2(uint16_t pid, uint8_t tid, int ext)
{
	m_MHWFilterMask2.pid = pid;
	m_MHWFilterMask2.data[0] = tid;
	if (tid == 0xdc)
	{
		m_MHWFilterMask2.mask[0] = 0xB5;
	}
	else
	{
		m_MHWFilterMask2.mask[0] = 0xFF;
	}
	if (ext != -1)
	{
		m_MHWFilterMask2.data[1] = ext;
		m_MHWFilterMask2.mask[1] = 0xFF;
//		eDebug("[eEPGChannelData] start 0x%03x 0x%02x 0x%02x", pid, tid, ext);
	}
	else
	{
		m_MHWFilterMask2.data[1] = 0;
		m_MHWFilterMask2.mask[1] = 0;
//		eDebug("[eEPGChannelData] start 0x%02x 0x%02x", pid, tid);
	}
	m_MHWReader2->start(m_MHWFilterMask2);
}

bool eEPGChannelData::log_open ()
{
	log_file = fopen (FILE_LOG, "w");
	 
	return (log_file != NULL);
}

void eEPGChannelData::log_close ()
{
	if (log_file != NULL)
		fclose (log_file);
}

void eEPGChannelData::log_add (const char *message, ...)
{
	va_list args;
	char msg[16*1024];
	time_t now_time;
	struct tm loctime;

	now_time = time (NULL);
	localtime_r(&now_time, &loctime);
	strftime (msg, 255, "%d/%m/%Y %H:%M:%S ", &loctime);
	 
	if (log_file != NULL) fwrite (msg, strlen (msg), 1, log_file);

	va_start (args, message);
	vsnprintf (msg, 16*1024, message, args);
	va_end (args);
	msg[(16*1024)-1] = '\0';
	 
	if (log_file != NULL)
	{
		fwrite (msg, strlen (msg), 1, log_file);
		fwrite ("\n", 1, 1, log_file);
		fflush (log_file);
	}
}

void eEPGChannelData::GetEquiv(void)
{
	nb_equiv=0;
	m_equiv.resize(100);
 
 	FILE *eq=fopen(FILE_EQUIV,"r");
 	if (eq) 
	{
		char linea[256];
		while ((fgets(linea,256,eq)!=NULL) && (nb_equiv<100))
		{
		    if (linea[0]!='#')
		    {
			int r1,r2,r3,osid,otid,onid,r4,r5,r6,r7,r8,r9,r10,r11,r12,r13,r14,esid,etid,enid;
			char name[20];
			if (sscanf(linea,"%x:%x:%x:%x:%x:%x:%x:%x:%x:%x: %x:%x:%x:%x:%x:%x:%x:%x:%x:%x: %s",&r1,&r2,&r3,&osid,&otid,&onid,&r4,&r5,&r6,&r7,&r8,&r9,&r10,&esid,&etid,&enid,&r11,&r12,&r13,&r14,name)==21)
			{
				mhw_channel_equiv_t channel;
				channel.original_nid_hi = (onid >> 8) &0xFF;
				channel.original_nid_lo = onid & 0xFF;
				channel.original_tid_hi = (otid >> 8) &0xFF;
				channel.original_tid_lo = otid & 0xFF;
				channel.original_sid_hi = (osid >> 8) &0xFF;
				channel.original_sid_lo = osid & 0xFF;
				channel.equiv_nid_hi = (enid >> 8) &0xFF;
				channel.equiv_nid_lo = enid & 0xFF;
				channel.equiv_tid_hi = (etid >> 8) &0xFF;
				channel.equiv_tid_lo = etid & 0xFF;
				channel.equiv_sid_hi = (esid >> 8) &0xFF;
				channel.equiv_sid_lo = esid & 0xFF;
				m_equiv[nb_equiv++] = channel;
			}
			}
		}
		fclose(eq);
	}
	m_equiv.resize(nb_equiv);
}

void eEPGChannelData::readMHWData(const uint8_t *data)
{
	if ( m_MHWReader2 )
		m_MHWReader2->stop();

	if ( state > 1 || // aborted
		// have si data.. so we dont read mhw data
		(haveData & (eEPGCache::SCHEDULE|eEPGCache::SCHEDULE_OTHER|eEPGCache::VIASAT)) )
	{
		eDebug("[eEPGChannelData] mhw aborted %d", state);
	}
	else if (m_MHWFilterMask.pid == 0xD3 && m_MHWFilterMask.data[0] == 0x91)
	// Channels table
	{
		nbr_summary = 0;
		int len = ((data[1]&0xf)<<8) + data[2] - 1;
		int record_size = sizeof( mhw_channel_name_t );
		int nbr_records = int (len/record_size);

		GetEquiv();
		FILE *f=fopen(FILE_CHANNELS,"w");

		char dated[22];
		time_t now_time;
		struct tm loctime;
		now_time = time (NULL);
		localtime_r(&now_time, &loctime);
		strftime (dated, 21, "%d/%m/%Y %H:%M:%S", &loctime);
		if (f)
		{
			fprintf(f,"#########################################\n");
			fprintf(f,"#                                       #\n");
			fprintf(f,"#       Channels list in mhw EPG        #\n");
			fprintf(f,"#    Generated at %s   #\n",dated);
			fprintf(f,"#                                       #\n");
			fprintf(f,"#      Format: (NAME) SID:TSID:NID      #\n");
			fprintf(f,"#                                       #\n");
			fprintf(f,"#########################################\n");
			fprintf(f,"#\n");
		}

		m_channels.resize(nbr_records);
		for ( int i = 0; i < nbr_records; i++ )
		{
			mhw_channel_name_t *channel = (mhw_channel_name_t*) &data[4 + i*record_size];
			m_channels[i]=*channel;
		
			if (f)
				fprintf(f,"(%s) %x:%x:%x\n",m_channels[i].name,m_channels[i].getChannelId(),
					m_channels[i].getTransportStreamId(),m_channels[i].getNetworkId());
		}
		haveData |= eEPGCache::MHW;

		eDebug("[eEPGChannelData] mhw %zu channels found", m_channels.size());

		fclose(f);
		log_open();
		log_add("EPG download in Mediahighway");
		log_add("Channels nbr.: %zu",m_channels.size());
		log_add("Equivalences Nbr.: %d",nb_equiv);

		// Channels table has been read, start reading the themes table.
		startMHWReader(0xD3, 0x92);
		return;
	}
	else if (m_MHWFilterMask.pid == 0xD3 && m_MHWFilterMask.data[0] == 0x92)
	// Themes table
	{
		int len = ((data[1]&0xf)<<8) + data[2] - 16;
		int record_size = sizeof( mhw_theme_name_t );
		int nbr_records = int (len/record_size);
		int idx_ptr = 0;
		uint8_t next_idx = (uint8_t) *(data + 3 + idx_ptr);
		uint8_t idx = 0;
		uint8_t sub_idx = 0;
		for ( int i = 0; i < nbr_records; i++ )
		{
			mhw_theme_name_t *theme = (mhw_theme_name_t*) &data[19 + i*record_size];
			if ( i >= next_idx )
			{
				idx = (idx_ptr<<4);
				idx_ptr++;
				next_idx = (uint8_t) *(data + 3 + idx_ptr);
				sub_idx = 0;
			}
			else
				sub_idx++;

			m_themes[idx+sub_idx] = *theme;
		}
		eDebug("[eEPGChannelData] mhw %zu themes found", m_themes.size());
		// Themes table has been read, start reading the titles table.
		startMHWReader(0xD2, 0x90);
		startMHWTimeout(5000);
		return;
	}
	else if (m_MHWFilterMask.pid == 0xD2 && m_MHWFilterMask.data[0] == 0x90)
	// Titles table
	{
		mhw_title_t *title = (mhw_title_t*) data;
		uint8_t name[24];
		std::string prog_title = (char *) delimitName( title->title, name, 23 );

		int table_len=data[2]|((data[1]&0x0f)<<8);
		if ( title->channel_id == 0xFF  || table_len < 19 || prog_title.substr(0,7) == "BIENTOT" )	// Separator or BIENTOT record
			return;	// Continue reading of the current table.
		else
		{
			// Create unique key per title
			uint32_t title_id = ((title->channel_id)<<16)|((title->dh.day)<<13)|((title->dh.hours)<<8)|
				(title->ms.minutes);
			uint32_t program_id = ((title->program_id_hi)<<24)|((title->program_id_mh)<<16)|
				((title->program_id_ml)<<8)|(title->program_id_lo);

			if ( m_titles.find( title_id ) == m_titles.end() )
			{
				startMHWTimeout(5000);
				title->mhw2_mjd_hi = 0;
				title->mhw2_mjd_lo = 0;
				title->mhw2_duration_hi = 0;
				title->mhw2_duration_lo = 0;
				m_titles[ title_id ] = *title;
				if ( (title->ms.summary_available) && (m_program_ids.find(program_id) == m_program_ids.end()) )
					// program_ids will be used to gather summaries.
					m_program_ids.insert(std::pair<uint32_t,uint32_t>(program_id,title_id));
				return;	// Continue reading of the current table.
			}
			else if (!checkMHWTimeout())
				return;
		}
		if ( !m_program_ids.empty())
		{
			// Titles table has been read, there are summaries to read.
			// Start reading summaries, store corresponding titles on the fly.
			startMHWReader(0xD3, 0x90);
			eDebug("[eEPGChannelData] mhw %zu titles(%zu with summary) found",
				m_titles.size(),
				m_program_ids.size());
			log_add("Titles Nbr.: %zu",m_titles.size());
			log_add("Titles Nbr. with summary: %zu",m_program_ids.size());
			startMHWTimeout(5000);
			return;
		}
	}
	else if (m_MHWFilterMask.pid == 0xD3 && m_MHWFilterMask.data[0] == 0x90)
	// Summaries table
	{
		mhw_summary_t *summary = (mhw_summary_t*) data;

		int table_len=data[2]|((data[1]&0x0f)<<8);
		if (table_len < (data[14] + 17)) return;
		// Create unique key per record
		uint32_t program_id = ((summary->program_id_hi)<<24)|((summary->program_id_mh)<<16)|
			((summary->program_id_ml)<<8)|(summary->program_id_lo);
		int len = ((data[1]&0xf)<<8) + data[2];

		// ugly workaround to convert const __u8* to char*
		char *tmp=0;
		memcpy(&tmp, &data, sizeof(void*));
		tmp[len+3] = 0;	// Terminate as a string.

		std::multimap<uint32_t, uint32_t>::iterator itProgid( m_program_ids.find( program_id ) );
		if ( itProgid == m_program_ids.end() )
		{ /*	This part is to prevent to looping forever if some summaries are not received yet.
			There is a timeout of 4 sec. after the last successfully read summary. */
			if (!m_program_ids.empty() && !checkMHWTimeout())
				return;	// Continue reading of the current table.
		}
		else
		{
			std::string the_text = (char *) (data + 11 + summary->nb_replays * 7);

			size_t pos = 0;
			while((pos = the_text.find("\r\n")) != std::string::npos)
				the_text.replace(pos, 2, " ");

			// Find corresponding title, store title and summary in epgcache.
			std::map<uint32_t, mhw_title_t>::iterator itTitle( m_titles.find( itProgid->second ) );
			if ( itTitle != m_titles.end() )
			{
				startMHWTimeout(5000);
				storeMHWTitle( itTitle, the_text, data );
				m_titles.erase( itTitle );
			}
			m_program_ids.erase( itProgid );
			if ( !m_program_ids.empty() )
				return;	// Continue reading of the current table.
		}
	}
	eDebug("[eEPGChannelData] mhw finished(%ld) %zu summaries not found",
		::time(0),
		m_program_ids.size());
	log_add("Summaries not found: %zu",m_program_ids.size());
	// Summaries have been read, titles that have summaries have been stored.
	// Now store titles that do not have summaries.
	for (std::map<uint32_t, mhw_title_t>::iterator itTitle(m_titles.begin()); itTitle != m_titles.end(); itTitle++)
		storeMHWTitle( itTitle, "", data );
	log_add("mhw2 EPG download finished");
	isRunning &= ~eEPGCache::MHW;
	m_MHWConn=0;
	if ( m_MHWReader )
		m_MHWReader->stop();
	if (haveData)
		finishEPG();
}

void eEPGChannelData::readMHWData2(const uint8_t *data)
{
	int dataLen = (((data[1]&0xf) << 8) | data[2]) + 3;

	if ( m_MHWReader )
		m_MHWReader->stop();

	if ( state > 1 || // aborted
		// have si data.. so we dont read mhw data
		(haveData & (eEPGCache::SCHEDULE|eEPGCache::SCHEDULE_OTHER|eEPGCache::VIASAT)) )
	{
		eDebug("[eEPGChannelData] mhw2 aborted %d", state);
	}
	else if (m_MHWFilterMask2.pid == m_mhw2_channel_pid && m_MHWFilterMask2.data[0] == 0xC8 && m_MHWFilterMask2.data[1] == 0)
	// Channels table
	{
		int num_channels = data[120];
		m_channels.resize(num_channels);
		if(dataLen > 120)
		{
			int ptr = 121 + 8 * num_channels;
			if( dataLen > ptr )
			{
				for( int chid = 0; chid < num_channels; ++chid )
				{
					ptr += ( data[ptr] & 0x0f ) + 1;
					if( dataLen < ptr )
						goto abort;
				}
			}
			else
				goto abort;
		}
		else
			goto abort;
		// data seems consistent...
		const uint8_t *tmp = data+121;
		GetEquiv();
		FILE *f=fopen(FILE_CHANNELS,"w");

		char dated[22];
		time_t now_time;
		struct tm loctime;
		now_time = time (NULL);
		localtime_r(&now_time, &loctime);
		strftime (dated, 21, "%d/%m/%Y %H:%M:%S", &loctime);
		if (f)
		{
			fprintf(f,"#########################################\n");
			fprintf(f,"#                                       #\n");
			fprintf(f,"#       Channels list in mhw EPG        #\n");
			fprintf(f,"#    Generated at %s   #\n",dated);
			fprintf(f,"#                                       #\n");
			fprintf(f,"#      Format: (NAME) SID:TSID:NID      #\n");
			fprintf(f,"#                                       #\n");
			fprintf(f,"#########################################\n");
			fprintf(f,"#\n");
		}

		for (int i=0; i < num_channels; ++i)
		{
			mhw_channel_name_t channel;
			channel.network_id_hi = *(tmp++);
			channel.network_id_lo = *(tmp++);
			channel.transport_stream_id_hi = *(tmp++);
			channel.transport_stream_id_lo = *(tmp++);
			channel.channel_id_hi = *(tmp++);
			channel.channel_id_lo = *(tmp++);
			m_channels[i]=channel;
//			eDebug("[eEPGChannelData] %d(%02x) %04x: %02x %02x", i, i, (channel.channel_id_hi << 8) | channel.channel_id_lo, *tmp, *(tmp+1));
			tmp+=2;
		}
		for (int i=0; i < num_channels; ++i)
		{
			mhw_channel_name_t &channel = m_channels[i];
			int channel_name_len=*(tmp++)&0x0f;
			int x=0;
			for (; x < channel_name_len; ++x)
				channel.name[x]=*(tmp++);
			channel.name[channel_name_len]=0;
//			eDebug("[eEPGChannelData] %d(%02x) %s", i, i, channel.name);

			if (f) fprintf(f,"(%s) %x:%x:%x\n",channel.name,
			channel.getChannelId(), channel.getTransportStreamId(), channel.getNetworkId());
		}

		fclose(f);
		log_open();
		log_add("EPG download in Mediahighway 2 (New)");
		log_add("Days: %d",eEPGCache::getInstance()->getEpgmaxdays());
		log_add("Channels nbr.: %d",num_channels);
		log_add("Equivalences Nbr.: %d",nb_equiv);

		haveData |= eEPGCache::MHW;
		eDebug("[eEPGChannelData] mhw2 %zu channels found", m_channels.size());
	}
	else if (m_MHWFilterMask2.pid == m_mhw2_channel_pid && m_MHWFilterMask2.data[0] == 0xC8 && m_MHWFilterMask2.data[1] == 1)
	{
		// Themes table
		eDebug("[eEPGChannelData] mhw2 themes nyi");
	}
	else if (m_MHWFilterMask2.pid == m_mhw2_title_pid)
	// Titles table
	{
		if (data[0] == 0xdc)
		{
			int pos=10;
			bool valid=false;
			int len=dataLen-1;
			while( pos < dataLen && !valid)
			{
				pos += 18;
				pos += (data[pos] & 0x3F) + 3;
				if( pos == len )
					valid = true;
			}

			if (!valid)
			{
				if (dataLen > 10)
					eDebug("[eEPGChannelData] mhw2 title table invalid!!");
				if (checkMHWTimeout())
					goto abort;
				if (!m_MHWTimeoutTimer->isActive())
					startMHWTimeout(20000);
				return; // continue reading
			}

			// data seems consistent...
			mhw_title_t title;
			pos = 10;
			while (pos < dataLen)
			{
				title.channel_id = data[7]+1;
				title.mhw2_mjd_hi = data[pos+11];
				title.mhw2_mjd_lo = data[pos+12];
				title.mhw2_hours = data[pos+13];
				title.mhw2_minutes = data[pos+14];
				title.mhw2_seconds = data[pos+15];
				int duration = ((data[pos+16] << 8)|data[pos+17]) >> 4;
				title.mhw2_duration_hi = (duration&0xFF00) >> 8;
				title.mhw2_duration_lo = duration&0xFF;

				// Create unique key per title
				uint32_t title_id = (data[pos+7] << 24) | (data[pos+8] << 16) | (data[pos+9] << 8) | data[pos+10];

				uint32_t summary_id = (data[pos+4] << 16) | (data[pos+5] << 8) | data[pos+6];
				uint8_t slen = data[pos+18] & 0x3f;
				uint8_t *dest = ((uint8_t*)title.title)-4;
				memcpy(dest, &data[pos+19], slen>35 ? 35 : slen);
				if ( slen < 35 )
					memset(dest+slen, 0, 35-slen);
				//memset(dest+slen, 0, (slen>35 ? 0 : 35-slen));
				pos += 19 + slen;

				title.mhw2_theme = 0xFF;

				if (summary_id == 0xFFFFFF)
					summary_id = (data[pos+1] << 8) | data[pos+2];

				pos += 2;

				//std::map<uint32_t, mhw_title_t>::iterator it = m_titles.find( title_id );
				std::map<uint32_t, uint32_t>::iterator it1 = m_titlesID.find( title_id );
				if ( it1 == m_titlesID.end() )
				{
					std::map<uint32_t, mhw_title_t>::iterator it = m_titles.find( title_id );
					if ( it == m_titles.end() )
					{
					startMHWTimeout(40000);
					m_titles[ title_id ] = title;
					m_titlesID[ title_id ] = title_id;
					if (summary_id != 0xFFFF)
					{

						bool add=true;
						std::multimap<uint32_t, uint32_t>::iterator it(m_program_ids.lower_bound(summary_id));
						while (it != m_program_ids.end() && it->first == summary_id)
						{
							if (it->second == title_id) {
								add=false;
								break;
							}
							++it;
						}
						if (add)
						{
							m_program_ids.insert(std::pair<uint32_t,uint32_t>(summary_id,title_id));
							nbr_summary = nbr_summary + 1;
						}
					}
				  }
			   }
			}
		}
		else if (data[0] == 0x96)
		{
		// more Summaries table
			if (!checkMHWTimeout())
			{
				int len, loop, pos;
				bool valid;
				valid = false;
				if( dataLen > 13 )
				{
					loop = data[14];
					pos = 15 + loop;
					if( dataLen > pos )
					{
						len = ((((data[pos]-0xe)&0xf) << 8) | data[pos+1]);
						if( dataLen > (pos+len) && len > 0)
							valid=true;
					}
				}

				if (valid)
				{
					// data seems consistent...
					uint32_t summary_id = (data[3] << 8) | data[4];

					// ugly workaround to convert const uint8_t* to char*
					char *tmp=0;
					memcpy(&tmp, &data, sizeof(void*));

					if( len > 0 )
						tmp[pos+len+1] = 0;
					else
						tmp[pos+1] = 0;

					std::multimap<uint32_t, uint32_t>::iterator itProgId( m_program_ids.lower_bound(summary_id) );
					if ( itProgId == m_program_ids.end() || itProgId->first != summary_id)
					{ /*	This part is to prevent to looping forever if some summaries are not received yet.
						There is a timeout of 4 sec. after the last successfully read summary. */
						if ( !m_program_ids.empty() )
							return;	// Continue reading of the current table.
					}
					else
					{
						//startMHWTimeout(15000);
						std::string the_text = (char *) (data + pos + 2);

						pos=pos+len+1;
						int nb = 0;


						while( itProgId != m_program_ids.end() && itProgId->first == summary_id )
						{
							// Find corresponding title, store title and summary in epgcache.
							std::map<uint32_t, mhw_title_t>::iterator itTitle( m_titles.find( itProgId->second ) );
							if ( itTitle != m_titles.end() )
							{
								nb = nb+1;
								itTitle->second.mhw2_theme = data[13] & 0xF0;
								storeMHWTitle( itTitle, the_text, data );
								m_titles.erase( itTitle );
							}
							m_program_ids.erase( itProgId++ );
						}
						if (nb>0 && !checkMHWTimeout())
						{
							startMHWTimeout(15000);
						}
					}
				}
			}
		}
		if (checkMHWTimeout())
		{
			eDebug("[eEPGChannelData] mhw2 %zu titles(%zu with summary) found", m_titles.size(), m_program_ids.size());
			log_add("Titles Nbr.: %zu",m_titlesID.size());
			log_add("Titles Nbr. with summary: %d",nbr_summary);
			if (!m_program_ids.empty())
			{
				// Titles table has been read, there are summaries to read.
				// Start reading summaries, store corresponding titles on the fly.
				startMHWReader2(m_mhw2_summary_pid, 0x96);
				startMHWTimeout(60000);
				return;
			}
		}
		else
			return;
	}
	else if (m_MHWFilterMask2.pid == m_mhw2_summary_pid && m_MHWFilterMask2.data[0] == 0x96)
	// Summaries table
	{
		if (!checkMHWTimeout())
		{
			int loop=0;
			int pos=0;
			int len=0;
			bool valid;
			valid = true;
			if( dataLen > 20 )
			{
				loop = data[19];
				pos = 20 + loop;
				if( dataLen > pos )
				{
					len = (((data[pos]&0xf) << 8) | data[pos+1]);
					if( dataLen < (pos+len) )
						valid=false;
				}
			}
			else
				return;  // continue reading

			if (valid)
			{
				// data seems consistent...
				uint32_t summary_id = (data[6] << 16) | (data[7] << 8) | data[8];
//				eDebug("[eEPGChannelData] summary id %04x\n", summary_id);
//				eDebug("[eEPGChannelData] [%02x %02x] %02x %02x %02x %02x %02x %02x %02x %02x XX\n", data[3], data[4], data[5], data[6], data[7], data[8], data[9], data[10], data[11], data[12], data[13] );

				// ugly workaround to convert const uint8_t* to char*
				char *tmp=0;
				memcpy(&tmp, &data, sizeof(void*));

				if( len > 0 )
					tmp[pos+len+1] = 0;
				else
					tmp[pos+1] = 0;

				std::multimap<uint32_t, uint32_t>::iterator itProgId( m_program_ids.lower_bound(summary_id) );
				if ( itProgId == m_program_ids.end() || itProgId->first != summary_id)
				{ /*	This part is to prevent to looping forever if some summaries are not received yet.
					There is a timeout of 4 sec. after the last successfully read summary. */
					if ( !m_program_ids.empty() )
						return;	// Continue reading of the current table.
				}
				else
				{
					startMHWTimeout(17000);
					std::string the_text = (char *) (data + pos + 2);

					pos=pos+len+12;

					while( itProgId != m_program_ids.end() && itProgId->first == summary_id )
					{
						// Find corresponding title, store title and summary in epgcache.
						std::map<uint32_t, mhw_title_t>::iterator itTitle( m_titles.find( itProgId->second ) );
						if ( itTitle != m_titles.end() )
						{
							std::string the_text2 = "";
							the_text2.append(the_text);
							while (pos<dataLen)
							{
								uint32_t title_id = (data[pos] << 24) | (data[pos+1] << 16) | (data[pos+2] << 8) | data[pos+3];
								std::map<uint32_t, mhw_title_t>::iterator it = m_titles.find( title_id );
								if ( it != m_titles.end() )
								{
									const char *const days[] = {"D", "L", "M", "M", "J", "V", "S", "D"};

									int chid = it->second.channel_id - 1;
									time_t ndate, edate;
									struct tm next_date;
									u_char mhw2_mjd_hi = data[pos+10];
									u_char mhw2_mjd_lo = data[pos+11];
									u_char mhw2_hours = data[pos+12];
									u_char mhw2_minutes = data[pos+13];
										ndate = MjdToEpochTime(mhw2_mjd) + (((mhw2_hours&0xf0)>>4)*10+(mhw2_hours&0x0f)) * 3600 + (((mhw2_minutes&0xf0)>>4)*10+(mhw2_minutes&0x0f)) * 60;
									edate = MjdToEpochTime(itTitle->second.mhw2_mjd)
									+ (((itTitle->second.mhw2_hours&0xf0)>>4)*10+(itTitle->second.mhw2_hours&0x0f)) * 3600 
									+ (((itTitle->second.mhw2_minutes&0xf0)>>4)*10+(itTitle->second.mhw2_minutes&0x0f)) * 60;
									localtime_r(&ndate, &next_date);
									if (ndate > edate)
									{
										char nd[200];
										sprintf (nd," %s %s%02d %02d:%02d",m_channels[chid].name,days[next_date.tm_wday],next_date.tm_mday,next_date.tm_hour, next_date.tm_min);
										the_text2.append(nd);
									}
								}
								pos += 19;
							}

							itTitle->second.mhw2_theme = data[17] & 0xF0;
							storeMHWTitle( itTitle, the_text2, data );
							m_titles.erase( itTitle );
						}
						m_program_ids.erase( itProgId++ );
					}
					if ( !m_program_ids.empty() )
						return;	// Continue reading of the current table.
				}
			}
			else
				return;  // continue reading
		}
	}
	if (isRunning & eEPGCache::MHW)
	{
		if ( m_MHWFilterMask2.pid == m_mhw2_channel_pid && m_MHWFilterMask2.data[0] == 0xC8 && m_MHWFilterMask2.data[1] == 0)
		{
			// Channels table has been read, start reading the themes table.
			startMHWReader2(m_mhw2_channel_pid, 0xC8, 1);
			return;
		}
		else if ( m_MHWFilterMask2.pid == m_mhw2_channel_pid && m_MHWFilterMask2.data[0] == 0xC8 && m_MHWFilterMask2.data[1] == 1)
		{
			// Themes table has been read, start reading the titles table.
			startMHWReader2(m_mhw2_title_pid, 0xdc);
			return;
		}
		else
		{
			// Summaries have been read, titles that have summaries have been stored.
			// Now store titles that do not have summaries.
			for (std::map<uint32_t, mhw_title_t>::iterator itTitle(m_titles.begin()); itTitle != m_titles.end(); itTitle++)
				storeMHWTitle( itTitle, "", data );
			eDebug("[eEPGChannelData] mhw2 finished(%ld) %zu summaries not found",
				::time(0),
				m_program_ids.size());
			log_add("Summaries not found: %zu",m_program_ids.size());
			log_add("mhw2 EPG download finished");
		}
	}
abort:
	isRunning &= ~eEPGCache::MHW;
	m_MHWConn2=0;
	if ( m_MHWReader2 )
		m_MHWReader2->stop();
	if (haveData)
		finishEPG();
}

void eEPGChannelData::readMHWData2_old(const uint8_t *data)
{
	int dataLen = (((data[1]&0xf) << 8) | data[2]) + 3;

	if ( m_MHWReader )
		m_MHWReader->stop();

	if ( state > 1 || // aborted
		// have si data.. so we dont read mhw data
		(haveData & (eEPGCache::SCHEDULE|eEPGCache::SCHEDULE_OTHER|eEPGCache::VIASAT)) )
	{
		eDebug("[eEPGChannelData] mhw2 aborted %d", state);
		log_add("mhw download aborted %d", state);
	}
	else if (m_MHWFilterMask2.pid == m_mhw2_channel_pid && m_MHWFilterMask2.data[0] == 0xC8 && m_MHWFilterMask2.data[1] == 0)
	// Channels table
	{
		int num_channels = data[120];
		m_channels.resize(num_channels);
		if(dataLen > 120)
		{
			int ptr = 121 + 8 * num_channels;
			if( dataLen > ptr )
			{
				for( int chid = 0; chid < num_channels; ++chid )
				{
					ptr += ( data[ptr] & 0x0f ) + 1;
					if( dataLen < ptr )
						goto abort;
				}
			}
			else
				goto abort;
		}
		else
			goto abort;
		// data seems consistent...
		const uint8_t *tmp = data+121;
		GetEquiv();
		FILE *f=fopen(FILE_CHANNELS,"w");

		char dated[22];
		time_t now_time;
		struct tm loctime;
		now_time = time (NULL);
		localtime_r(&now_time, &loctime);
		strftime (dated, 21, "%d/%m/%Y %H:%M:%S", &loctime);
		if (f)
		{
			fprintf(f,"#########################################\n");
			fprintf(f,"#                                       #\n");
			fprintf(f,"#       Channels list in mhw EPG        #\n");
			fprintf(f,"#    Generated at %s   #\n",dated);
			fprintf(f,"#                                       #\n");
			fprintf(f,"#      Format: (NAME) SID:TSID:NID      #\n");
			fprintf(f,"#                                       #\n");
			fprintf(f,"#########################################\n");
			fprintf(f,"#\n");
		}
		
		for (int i=0; i < num_channels; ++i)
		{
			mhw_channel_name_t channel;
			channel.network_id_hi = *(tmp++);
			channel.network_id_lo = *(tmp++);
			channel.transport_stream_id_hi = *(tmp++);
			channel.transport_stream_id_lo = *(tmp++);
			channel.channel_id_hi = *(tmp++);
			channel.channel_id_lo = *(tmp++);
			m_channels[i]=channel;
//			eDebug("[eEPGChannelData] %d(%02x) %04x: %02x %02x", i, i, (channel.channel_id_hi << 8) | channel.channel_id_lo, *tmp, *(tmp+1));
			tmp+=2;
		}
		for (int i=0; i < num_channels; ++i)
		{
			mhw_channel_name_t &channel = m_channels[i];
			int channel_name_len=*(tmp++)&0x0f;
			int x=0;
			for (; x < channel_name_len; ++x)
				channel.name[x]=*(tmp++);
			channel.name[channel_name_len]=0;
//			eDebug("[eEPGChannelData] %d(%02x) %s", i, i, channel.name);

			if (f) fprintf(f,"(%s) %x:%x:%x\n", channel.name, channel.getChannelId(), channel.getTransportStreamId(), channel.getNetworkId());
		}

		fclose(f);
		log_open();
		log_add("EPG download in Mediahighway 2 (old)");
		log_add("Days: %d",eEPGCache::getInstance()->getEpgmaxdays());
		log_add("Channels nbr.: %d",num_channels);
		log_add("Equivalences Nbr.: %d",nb_equiv);

		haveData |= eEPGCache::MHW;
		eDebug("[eEPGChannelData] mhw2 %zu channels found", m_channels.size());
	}
	else if (m_MHWFilterMask2.pid == m_mhw2_channel_pid && m_MHWFilterMask2.data[0] == 0xC8 && m_MHWFilterMask2.data[1] == 1)
	{
		// Themes table
		eDebug("[eEPGChannelData] mhw2 themes nyi");
	}
	else if (m_MHWFilterMask2.pid == m_mhw2_title_pid && m_MHWFilterMask2.data[0] == 0xe6)
	// Titles table
	{
		int pos=18;
		bool valid=false;
		bool finish=false;

//		eDebug("[eEPGChannelData] %02x %02x %02x %02x %02x %02x %02x %02x %02x %02x %02x %02x %02x %02x %02x",
//			data[3], data[4], data[5], data[6], data[7], data[8], data[9], data[10],
//			data[11], data[12], data[13], data[14], data[15], data[16], data[17] );

		while( pos < dataLen && !valid)
		{
			pos += 18;
			pos += (data[pos] & 0x3F) + 4;
			if( pos == dataLen )
				valid = true;
		}

		if (!valid)
		{
			if (dataLen > 18)
				eDebug("[eEPGChannelData] mhw2 title table invalid!!");
			if (checkMHWTimeout())
				goto abort;
			if (!m_MHWTimeoutTimer->isActive())
				startMHWTimeout(5000);
			return; // continue reading
		}

		// data seems consistent...
		mhw_title_t title;
		pos = 18;
		while (pos < dataLen)
		{
//			eDebugNoNewLine("[eEPGChannelData]    [%02x] %02x %02x %02x %02x %02x %02x %02x %02x %02x %02x [%02x %02x %02x %02x %02x %02x %02x] LL - DESCR - ",
//				data[pos], data[pos+1], data[pos+2], data[pos+3], data[pos+4], data[pos+5], data[pos+6], data[pos+7],
//				data[pos+8], data[pos+9], data[pos+10], data[pos+11], data[pos+12], data[pos+13], data[pos+14], data[pos+15], data[pos+16], data[pos+17]);
			title.channel_id = data[pos]+1;
			title.mhw2_mjd_hi = data[pos+11];
			title.mhw2_mjd_lo = data[pos+12];
			title.mhw2_hours = data[pos+13];
			title.mhw2_minutes = data[pos+14];
			title.mhw2_seconds = data[pos+15];
			int duration = ((data[pos+16] << 8)|data[pos+17]) >> 4;
			title.mhw2_duration_hi = (duration&0xFF00) >> 8;
			title.mhw2_duration_lo = duration&0xFF;

			// Create unique key per title
			uint32_t title_id = (data[pos+7] << 24) | (data[pos+8] << 16) | (data[pos+9] << 8) | data[pos+10];

			uint8_t slen = data[pos+18] & 0x3f;
			uint8_t *dest = ((uint8_t*)title.title)-4;
			memcpy(dest, &data[pos+19], slen>35 ? 35 : slen);
			if ( slen < 35 )
				memset(dest+slen, 0, 35-slen);
			pos += 19 + slen;
//			eDebugNoNewLine("%02x [%02x %02x]: %s", data[pos], data[pos+1], data[pos+2], dest);

//			not used theme id (data[7] & 0x3f) + (data[pos] & 0x3f);
			uint32_t summary_id = (data[pos+1] << 8) | data[pos+2];

//			if (title.channel_id > m_channels.size())
//				eDebug("[eEPGChannelData] channel_id(%d %02x) to big!!", title.channel_id);

//			eDebug("[eEPGChannelData] pos %d prog_id %02x %02x chid %02x summary_id %04x dest %p len %d\n",
//				pos, title.program_id_ml, title.program_id_lo, title.channel_id, summary_id, dest, slen);

//			eDebug("[eEPGChannelData] title_id %08x -> summary_id %04x\n", title_id, summary_id);

			pos += 3;

			std::map<uint32_t, mhw_title_t>::iterator it = m_titles.find( title_id );
			if ( it == m_titles.end() )
			{
				startMHWTimeout(5000);
				m_titles[ title_id ] = title;
				if (summary_id != 0xFFFF)
				{
					bool add=true;
					std::multimap<uint32_t, uint32_t>::iterator it(m_program_ids.lower_bound(summary_id));
					while (it != m_program_ids.end() && it->first == summary_id)
					{
						if (it->second == title_id) {
							add=false;
							break;
						}
						++it;
					}
					if (add)
						m_program_ids.insert(std::pair<uint32_t,uint32_t>(summary_id,title_id));
				}
			}
			else
			{
				if ( !checkMHWTimeout() )
					continue;	// Continue reading of the current table.
				finish=true;
				break;
			}
		}
		if (finish)
		{
			eDebug("[eEPGChannelData] mhw2 %zu titles(%zu with summary) found", m_titles.size(), m_program_ids.size());
			log_add("Titles Nbr.: %zu",m_titles.size());
			log_add("Titles Nbr. with summary: %zu",m_program_ids.size());
			if (!m_program_ids.empty())
			{
				// Titles table has been read, there are summaries to read.
				// Start reading summaries, store corresponding titles on the fly.
				startMHWReader2(m_mhw2_summary_pid, 0x96);
				startMHWTimeout(15000);
				return;
			}
		}
		else
			return;
	}
	else if (m_MHWFilterMask2.pid == m_mhw2_summary_pid && m_MHWFilterMask2.data[0] == 0x96)
	// Summaries table
	{
		if (!checkMHWTimeout())
		{
			int len, loop, pos, lenline;
			bool valid;
			valid = true;
			if( dataLen > 15 )
			{
				loop = data[14];
				pos = 15 + loop;
				if( dataLen > pos )
				{
					loop = data[pos] & 0x0f;
					pos += 1;
					if( dataLen > pos )
					{
						len = 0;
						for( ; loop > 0; --loop )
						{
							if( dataLen > (pos+len) )
							{
								lenline = data[pos+len];
								len += lenline + 1;
							}
							else
								valid=false;
						}
					}
				}
			}
			else
				return;  // continue reading

			if (valid)
			{
				// data seems consistent...
				uint32_t summary_id = (data[3]<<8)|data[4];
//				eDebug ("[eEPGChannelData] summary id %04x\n", summary_id);
//				eDebug("[eEPGChannelData] [%02x %02x] %02x %02x %02x %02x %02x %02x %02x %02x XX\n", data[3], data[4], data[5], data[6], data[7], data[8], data[9], data[10], data[11], data[12], data[13] );

				// ugly workaround to convert const __u8* to char*
				char *tmp=0;
				memcpy(&tmp, &data, sizeof(void*));

				len = 0;
				loop = data[14];
				pos = 15 + loop;
				loop = tmp[pos] & 0x0f;
				pos += 1;
				for( ; loop > 0; loop -- )
				{
					lenline = tmp[pos+len];
					tmp[pos+len] = ' ';
					len += lenline + 1;
				}
				if( len > 0 )
					tmp[pos+len] = 0;
				else
					tmp[pos+1] = 0;

				std::multimap<uint32_t, uint32_t>::iterator itProgId( m_program_ids.lower_bound(summary_id) );
				if ( itProgId == m_program_ids.end() || itProgId->first != summary_id)
				{ /*	This part is to prevent to looping forever if some summaries are not received yet.
					There is a timeout of 4 sec. after the last successfully read summary. */
					if ( !m_program_ids.empty() )
						return;	// Continue reading of the current table.
				}
				else
				{
					startMHWTimeout(15000);
					std::string the_text = (char *) (data + pos + 1);

					pos=pos+len+1;
					int nb_replays;
					if (dataLen > pos + 5)
						nb_replays=data[pos] - 0xC0;
					else
						nb_replays = 0;
					if (nb_replays>10) nb_replays=10;
					int replay_chid[10];
					time_t replay_time[10];
					epg_replay_t *epg_replay;
						epg_replay = (epg_replay_t *) (data+pos+1);
					int i;
					for (i=0; i< nb_replays; i++)
					{
						epg_replay->replay_time_s=0;
						replay_time[i] = MjdToEpochTime(epg_replay->replay_mjd) +
								BcdTimeToSeconds(epg_replay->replay_time);
						replay_chid[i] = epg_replay->channel_id;
						epg_replay++;
					}


//					eDebug("[eEPGChannelData] summary id %04x : %s\n", summary_id, data+pos+1);

					while( itProgId != m_program_ids.end() && itProgId->first == summary_id )
					{
//						eDebug("[eEPGChannelData] .");
						// Find corresponding title, store title and summary in epgcache.
						std::map<uint32_t, mhw_title_t>::iterator itTitle( m_titles.find( itProgId->second ) );
						if ( itTitle != m_titles.end() )
						{
							std::string the_text2 = "";
							the_text2.append(the_text);
							int n=0;
							while (n<nb_replays)
							{
								char const *const days[] = {"D", "L", "M", "M", "J", "V", "S", "D"};

								time_t ndate, edate;
								struct tm next_date;
								ndate = replay_time[n];
								edate = MjdToEpochTime(itTitle->second.mhw2_mjd) 
									+ (((itTitle->second.mhw2_hours&0xf0)>>4)*10+(itTitle->second.mhw2_hours&0x0f)) * 3600 
									+ (((itTitle->second.mhw2_minutes&0xf0)>>4)*10+(itTitle->second.mhw2_minutes&0x0f)) * 60;
								localtime_r(&ndate, &next_date);
								if (ndate > edate)
								{
									char nd[200];
									sprintf (nd," %s %s%02d %02d:%02d",m_channels[replay_chid[n]].name,days[next_date.tm_wday],next_date.tm_mday,next_date.tm_hour, next_date.tm_min);
									the_text2.append(nd);
								}
								n++;
							}

							storeMHWTitle( itTitle, the_text2, data );
							m_titles.erase( itTitle );
						}
						m_program_ids.erase( itProgId++ );
					}
					if ( !m_program_ids.empty() )
						return;	// Continue reading of the current table.
				}
			}
			else
				return;  // continue reading
		}
	}
	if (isRunning & eEPGCache::MHW)
	{
		if ( m_MHWFilterMask2.pid == m_mhw2_channel_pid && m_MHWFilterMask2.data[0] == 0xC8 && m_MHWFilterMask2.data[1] == 0)
		{
			// Channels table has been read, start reading the themes table.
			startMHWReader2(m_mhw2_channel_pid, 0xC8, 1);
			return;
		}
		else if ( m_MHWFilterMask2.pid == m_mhw2_channel_pid && m_MHWFilterMask2.data[0] == 0xC8 && m_MHWFilterMask2.data[1] == 1)
		{
			// Themes table has been read, start reading the titles table.
			startMHWReader2(m_mhw2_title_pid, 0xe6);
			return;
		}
		else
		{
			// Summaries have been read, titles that have summaries have been stored.
			// Now store titles that do not have summaries.
			for (std::map<uint32_t, mhw_title_t>::iterator itTitle(m_titles.begin()); itTitle != m_titles.end(); itTitle++)
				storeMHWTitle( itTitle, "", data );
			eDebug("[eEPGChannelData] mhw2 finished(%ld) %zu summaries not found",
				::time(0),
				m_program_ids.size());
			log_add("Summaries not found: %zu",m_program_ids.size());
			log_add("mhw2 EPG download finished");
		}
	}
abort:
	isRunning &= ~eEPGCache::MHW;
	m_MHWConn2=0;
	if ( m_MHWReader2 )
		m_MHWReader2->stop();
	if (haveData)
		finishEPG();
}
#endif // ENABLE_MHW_EPG


#if ENABLE_FREESAT

freesatEITSubtableStatus::freesatEITSubtableStatus(u_char version, uint8_t maxSection) : version(version)
{
	initMap(maxSection);
}

void freesatEITSubtableStatus::initMap(uint8_t maxSection)
{
	int i, maxSectionIdx = maxSection / 8;
	for (i = 0; i < 32; i++)
	{
		sectionMap[i] = (i <= maxSectionIdx ? 0x0100 : 0x0000 );
	}
}

bool freesatEITSubtableStatus::isSectionPresent(uint8_t sectionNo)
{
	uint8_t sectionIdx = sectionNo / 8;
	uint8_t bitOffset = sectionNo % 8;

	return ((sectionMap[sectionIdx] & (1 << bitOffset)) != 0);
}

bool freesatEITSubtableStatus::isCompleted()
{
	uint32_t i = 0;
	uint8_t calc;

	while ( i < 32 )
	{
		calc = sectionMap[i] >> 8;
		if (! calc) return true; // Last segment passed
		if (calc ^ ( sectionMap[i] & 0xFF ) ) // Segment not fully found
			return false;
		i++;
	}
	return true; // All segments ok
}

void freesatEITSubtableStatus::seen(uint8_t sectionNo, uint8_t maxSegmentSection)
{
	uint8_t sectionIdx = sectionNo / 8;
	uint8_t bitOffset = sectionNo % 8;
	uint8_t maxBitOffset = maxSegmentSection % 8;

	sectionMap[sectionIdx] &= 0x00FF; // Clear calc map
	sectionMap[sectionIdx] |= ((0x01FF << maxBitOffset) & 0xFF00); // Set calc map
	sectionMap[sectionIdx] |= (1 << bitOffset); // Set seen map
}

bool freesatEITSubtableStatus::isVersionChanged(u_char testVersion)
{
	return version != testVersion;
}

void freesatEITSubtableStatus::updateVersion(u_char newVersion, uint8_t maxSection)
{
	version = newVersion;
	initMap(maxSection);
}

void eEPGChannelData::cleanupFreeSat()
{
	m_FreeSatSubTableStatus.clear();
	m_FreesatTablesToComplete = 0;
}

void eEPGChannelData::readFreeSatScheduleOtherData( const uint8_t *data)
{
	eit_t *eit = (eit_t*) data;
	uint32_t subtableNo = data[0] << 24; // Table ID
	subtableNo |= data[3] << 16; // Service ID Hi
	subtableNo |= data[4] << 8; // Service ID Lo

	// Check for sub-table version in map
	std::map<uint32_t, freesatEITSubtableStatus> &freeSatSubTableStatus = this->m_FreeSatSubTableStatus;
	std::map<uint32_t, freesatEITSubtableStatus>::iterator itmap = freeSatSubTableStatus.find(subtableNo);

	freesatEITSubtableStatus *fsstatus;
	if ( itmap == freeSatSubTableStatus.end() )
	{
		// New sub table. Store version.
		//eDebug("[eEPGChannelData] New subtable (%x) version (%d) now/next (%d) tsid (%x/%x) onid (%x/%x)", subtableNo, eit->version_number, eit->current_next_indicator, eit->transport_stream_id_hi, eit->transport_stream_id_lo, eit->original_network_id_hi, eit->original_network_id_lo);
		fsstatus = new freesatEITSubtableStatus(eit->version_number, eit->last_section_number);
		m_FreesatTablesToComplete++;
		freeSatSubTableStatus.insert(std::pair<uint32_t,freesatEITSubtableStatus>(subtableNo, *fsstatus));
	}
	else
	{
		fsstatus = &itmap->second;
		// Existing subtable. Check version. Should check current / next as well? Seems to always be current for Freesat
		if ( fsstatus->isVersionChanged(eit->version_number) )
		{
			eDebug("[eEPGChannelData] FS subtable (%x) version changed (%d) now/next (%d)", subtableNo, eit->version_number, eit->current_next_indicator);
			m_FreesatTablesToComplete++;
			fsstatus->updateVersion(eit->version_number, eit->last_section_number);
		}
		else
		{
			if ( fsstatus->isSectionPresent(eit->section_number) )
			{
//				eDebug("[eEPGChannelData] DUP FS sub/sec/ver (%x/%d/%d)", subtableNo, eit->section_number, eit->version_number);
				return;
			}
		}
	}

//	eDebug("[eEPGChannelData] New FS sub/sec/ls/lss/ver (%x/%d/%d/%d/%d)", subtableNo, eit->section_number, eit->last_section_number, eit->segment_last_section_number, eit->version_number);
	fsstatus->seen(eit->section_number, eit->segment_last_section_number);
	if (fsstatus->isCompleted())
	{
		m_FreesatTablesToComplete--;
	}
	if (eEPGCache::getInstance())
		eEPGCache::getInstance()->sectionRead(data, eEPGCache::FREESAT_SCHEDULE_OTHER, this);
}
#endif // ENABLE_FREESAT


#ifdef ENABLE_ATSC
void eEPGChannelData::ATSC_checkCompletion()
{
	if (!m_ATSC_VCTConn && !m_ATSC_MGTConn && !m_ATSC_EITConn && !m_ATSC_ETTConn)
	{
		eDebug("[eEPGChannelData] ATSC EIT index %d completed", m_atsc_eit_index);
		for (std::map<uint32_t, struct atsc_event>::const_iterator it = m_ATSC_EIT_map.begin(); it != m_ATSC_EIT_map.end(); ++it)
		{
			std::vector<int> sids;
			std::vector<eDVBChannelID> chids;
			int sourceid = (it->first >> 16) & 0xffff;
			sids.push_back(m_ATSC_VCT_map[sourceid]);
			chids.push_back(channel->getChannelID());
			if (eEPGCache::getInstance())
				eEPGCache::getInstance()->submitEventData(sids, chids, it->second.startTime, it->second.lengthInSeconds, it->second.title.c_str(), "", m_ATSC_ETT_map[it->first].c_str(), 0, eEPGCache::ATSC_EIT, it->second.eventId);
		}
		m_ATSC_EIT_map.clear();
		m_ATSC_ETT_map.clear();
		if (m_atsc_eit_index < 128)
		{
			eDVBSectionFilterMask mask = {};
			m_atsc_eit_index++;
			m_ATSC_MGTReader->connectRead(sigc::mem_fun(*this, &eEPGChannelData::ATSC_MGTsection), m_ATSC_MGTConn);
			mask.pid = 0x1ffb;
			mask.data[0] = 0xc7;
			mask.mask[0] = 0xff;
			m_ATSC_MGTReader->start(mask);
		}
		else
		{
			eDebug("[eEPGChannelData] ATSC EIT parsing completed");
			m_ATSC_VCT_map.clear();
			isRunning &= ~eEPGCache::ATSC_EIT;
			if (!isRunning)
			{
				finishEPG();
			}
		}
	}
}

void eEPGChannelData::ATSC_VCTsection(const uint8_t *d)
{
	VirtualChannelTableSection vct(d);
	for (VirtualChannelListConstIterator channel = vct.getChannels()->begin(); channel != vct.getChannels()->end(); ++channel)
	{
		if (m_ATSC_VCT_map.find((*channel)->getSourceId()) == m_ATSC_VCT_map.end())
		{
			m_ATSC_VCT_map[(*channel)->getSourceId()] = (*channel)->getServiceId();
		}
		else
		{
			m_ATSC_VCTReader->stop();
			m_ATSC_VCTConn = NULL;
			ATSC_checkCompletion();
			break;
		}
	}
}

void eEPGChannelData::ATSC_MGTsection(const uint8_t *d)
{
	MasterGuideTableSection mgt(d);
	for (MasterGuideTableListConstIterator table = mgt.getTables()->begin(); table != mgt.getTables()->end(); ++table)
	{
		eDVBSectionFilterMask mask = {};
		if ((*table)->getTableType() == 0x0100 + m_atsc_eit_index)
		{
			/* EIT */
			mask.pid = (*table)->getPID();
			mask.data[0] = 0xcb;
			mask.mask[0] = 0xff;
			m_ATSC_EITReader->connectRead(sigc::mem_fun(*this, &eEPGChannelData::ATSC_EITsection), m_ATSC_EITConn);
			m_ATSC_EITReader->start(mask);
		}
		else if ((*table)->getTableType() == 0x0200 + m_atsc_eit_index)
		{
			/* ETT */
			mask.pid = (*table)->getPID();
			mask.data[0] = 0xcc;
			mask.mask[0] = 0xff;
			m_ATSC_ETTReader->connectRead(sigc::mem_fun(*this, &eEPGChannelData::ATSC_ETTsection), m_ATSC_ETTConn);
			m_ATSC_ETTReader->start(mask);
		}
	}
	m_ATSC_MGTReader->stop();
	m_ATSC_MGTConn = NULL;
	if (!m_ATSC_EITConn)
	{
		/* no more EIT */
		m_ATSC_ETTReader->stop();
		m_ATSC_ETTConn = NULL;
		m_atsc_eit_index = 128;
		ATSC_checkCompletion();
	}
}

void eEPGChannelData::ATSC_EITsection(const uint8_t *d)
{
	ATSCEventInformationSection eit(d);
	for (ATSCEventListConstIterator ev = eit.getEvents()->begin(); ev != eit.getEvents()->end(); ++ev)
	{
		uint32_t etm = ((eit.getTableIdExtension() & 0xffff) << 16) | (((*ev)->getEventId() & 0x3fff) << 2) | 0x2;
		if (m_ATSC_EIT_map.find(etm) == m_ATSC_EIT_map.end())
		{
			struct atsc_event event;
			event.title = (*ev)->getTitle("---");
			event.eventId = (*ev)->getEventId();
			event.startTime = (*ev)->getStartTime() + (time_t)315964800; /* ATSC GPS system time epoch is 00:00 Jan 6th 1980 */
			event.lengthInSeconds = (*ev)->getLengthInSeconds();
			m_ATSC_EIT_map[etm] = event;
		}
		else
		{
			m_ATSC_EITReader->stop();
			m_ATSC_EITConn = NULL;
			ATSC_checkCompletion();
			break;
		}
	}
	haveData |= eEPGCache::ATSC_EIT;
}

void eEPGChannelData::ATSC_ETTsection(const uint8_t *d)
{
	ExtendedTextTableSection ett(d);
	if (m_ATSC_ETT_map.find(ett.getETMId()) == m_ATSC_ETT_map.end())
	{
		m_ATSC_ETT_map[ett.getETMId()] = ett.getMessage("---");
	}
	else
	{
		m_ATSC_ETTReader->stop();
		m_ATSC_ETTConn = NULL;
		ATSC_checkCompletion();
	}
}

void eEPGChannelData::cleanupATSC()
{
	m_ATSC_VCTReader->stop();
	m_ATSC_MGTReader->stop();
	m_ATSC_EITReader->stop();
	m_ATSC_ETTReader->stop();
	m_ATSC_VCTConn = NULL;
	m_ATSC_MGTConn = NULL;
	m_ATSC_EITConn = NULL;
	m_ATSC_ETTConn = NULL;

	m_ATSC_EIT_map.clear();
	m_ATSC_ETT_map.clear();
	m_ATSC_VCT_map.clear();
}
#endif // ENABLE_ATSC


#ifdef ENABLE_OPENTV
void eEPGChannelData::OPENTV_checkCompletion(uint32_t data_crc)
{
	if (!m_OPENTV_crc32)
	{
		m_OPENTV_crc32 = data_crc;
	}
	else if (m_OPENTV_crc32 == data_crc)
	{
		m_OPENTV_crc32 = 0;
	}

	eDVBSectionFilterMask mask;
	memset(&mask, 0, sizeof(mask));

	if ((m_OPENTV_ChannelsConn && (m_OPENTV_EIT_index > 0xff)) || (m_OPENTV_ChannelsConn && !m_OPENTV_crc32))
	{
		eDebug("[eEPGChannelData] OpenTV channels, found=%d%s", (int)m_OPENTV_channels_map.size(), m_OPENTV_crc32 ? ", crc32 incomplete" : "");
		m_OPENTV_ChannelsReader->stop();
		m_OPENTV_ChannelsConn = NULL;
		m_OPENTV_EIT_index = m_OPENTV_crc32 = 0;
		m_OPENTV_Timer->start(200000, true);
		m_OPENTV_TitlesReader->connectRead(sigc::mem_fun(*this, &eEPGChannelData::OPENTV_TitlesSection), m_OPENTV_TitlesConn);
		mask = {};
		mask.pid = m_OPENTV_pid = 0x30;
		mask.data[0] = 0xa0;
		mask.mask[0] = 0xfc;
		mask.flags = eDVBSectionFilterMask::rfCRC;
		m_OPENTV_TitlesReader->start(mask);
	}
	else if ((m_OPENTV_TitlesConn && (m_OPENTV_EIT_index > 0xfff)) || (m_OPENTV_TitlesConn && !m_OPENTV_crc32))
	{
		m_OPENTV_TitlesReader->stop();
		m_OPENTV_TitlesConn = NULL;
		m_OPENTV_EIT_index = m_OPENTV_crc32 = 0;
		m_OPENTV_pid += 0x10;

		if (m_OPENTV_pid < 0x48)
		{
			eDebug("[eEPGChannelData] OpenTV titles %d stored=%d%s", (int)m_OPENTV_EIT_map.size(), (int)m_OPENTV_descriptors_map.size(), m_OPENTV_crc32 ? ", crc32 incomplete" : "");
			m_OPENTV_SummariesReader->connectRead(sigc::mem_fun(*this, &eEPGChannelData::OPENTV_SummariesSection), m_OPENTV_SummariesConn);
			mask = {};
			mask.pid = m_OPENTV_pid;
			mask.data[0] = 0xa8;
			mask.mask[0] = 0xfc;
			mask.flags = eDVBSectionFilterMask::rfCRC;
			m_OPENTV_SummariesReader->start(mask);
		}
	}
	else if ((m_OPENTV_SummariesConn && (m_OPENTV_EIT_index > 0xfff)) || (m_OPENTV_SummariesConn && !m_OPENTV_crc32))
	{
		m_OPENTV_SummariesReader->stop();
		m_OPENTV_SummariesConn = NULL;
		m_OPENTV_EIT_index = m_OPENTV_crc32 = 0;
		m_OPENTV_pid -= 0x10;

		//cache remaining uncached events for which the provider only sends title with no summary data.. off air/overnight!
		eDebug("[eEPGChannelData] OpenTV summaries, uncached=%d%s", (int)m_OPENTV_EIT_map.size(), m_OPENTV_crc32 ? ", crc32 incomplete" : "");

		for (std::map<uint32_t, struct opentv_event>::const_iterator it = m_OPENTV_EIT_map.begin(); it != m_OPENTV_EIT_map.end(); ++it)
		{
			int channelid = (it->first >> 16) & 0xffff;

			if (m_OPENTV_channels_map.find(channelid) != m_OPENTV_channels_map.end())
			{
				std::vector<int> sids;
				std::vector<eDVBChannelID> chids;
				eDVBChannelID chid = channel->getChannelID();
				chid.transport_stream_id = m_OPENTV_channels_map[channelid].transportStreamId;
				chid.original_network_id = m_OPENTV_channels_map[channelid].originalNetworkId;
				chids.push_back(chid);
				sids.push_back(m_OPENTV_channels_map[channelid].serviceId);
				if (eEPGCache::getInstance())
					eEPGCache::getInstance()->submitEventData(sids, chids, it->second.startTime, it->second.duration, m_OPENTV_descriptors_map[it->second.title_crc].c_str(), "", "", 0, eEPGCache::OPENTV, it->second.eventId);
			}
		}
		m_OPENTV_descriptors_map.clear();
		m_OPENTV_EIT_map.clear();

		if (++m_OPENTV_pid < 0x38)
		{
			m_OPENTV_TitlesReader->connectRead(sigc::mem_fun(*this, &eEPGChannelData::OPENTV_TitlesSection), m_OPENTV_TitlesConn);
			mask = {};
			mask.pid = m_OPENTV_pid;
			mask.data[0] = 0xa0;
			mask.mask[0] = 0xfc;
			mask.flags = eDVBSectionFilterMask::rfCRC;
			m_OPENTV_TitlesReader->start(mask);
		}
		else
			eDebug("[eEPGChannelData] OpenTV finishing, uncached=%d", (int)m_OPENTV_EIT_map.size());
	}
	else
		m_OPENTV_EIT_index++;

	if (!m_OPENTV_ChannelsConn && !m_OPENTV_TitlesConn && !m_OPENTV_SummariesConn)
	{
		eDebug("[eEPGChannelData] OpenTV EIT parsing completed");
		isRunning &= ~eEPGCache::OPENTV;

		if (!isRunning)
			finishEPG();
		else
			cleanupOPENTV();
	}
}

void eEPGChannelData::OPENTV_ChannelsSection(const uint8_t *d)
{
	OpenTvChannelSection otcs(d);

	for (OpenTvChannelListConstIterator channel = otcs.getChannels()->begin(); channel != otcs.getChannels()->end(); ++channel)
	{
		if (m_OPENTV_channels_map.find((*channel)->getChannelId()) == m_OPENTV_channels_map.end())
		{
			struct opentv_channel otc;
			otc.originalNetworkId = (*channel)->getOriginalNetworkId();
			otc.transportStreamId = (*channel)->getTransportStreamId();
			otc.serviceId = (*channel)->getServiceId();
			otc.serviceType = (*channel)->getServiceType();
			m_OPENTV_channels_map[(*channel)->getChannelId()] = otc;
		}
	}
	OPENTV_checkCompletion(otcs.getCrc32());
}

void eEPGChannelData::OPENTV_TitlesSection(const uint8_t *d)
{
	OpenTvTitleSection otts(d);

	for (OpenTvTitleListConstIterator title = otts.getTitles()->begin(); title != otts.getTitles()->end(); ++title)
	{
		uint32_t etm = ((otts.getTableIdExtension() & 0xffff) << 16) | ((*title)->getEventId() & 0xffff);

		if (m_OPENTV_EIT_map.find(etm) == m_OPENTV_EIT_map.end())
		{
			struct opentv_event ote;
			ote.eventId = (*title)->getEventId();
			ote.startTime = (*title)->getStartTime();
			ote.duration = (*title)->getDuration();
			ote.title_crc = (*title)->getCRC32();
			m_OPENTV_EIT_map[etm] = ote;

			if (m_OPENTV_descriptors_map.find(ote.title_crc) == m_OPENTV_descriptors_map.end())
				m_OPENTV_descriptors_map[ote.title_crc] = (*title)->getTitle();
		}
	}

	OPENTV_checkCompletion(otts.getCrc32());
}

void eEPGChannelData::OPENTV_SummariesSection(const uint8_t *d)
{
	OpenTvSummarySection otss(d);

	int channelid = otss.getTableIdExtension();

	if (m_OPENTV_channels_map.find(channelid) != m_OPENTV_channels_map.end())
	{
		for (OpenTvSummaryListConstIterator summary = otss.getSummaries()->begin(); summary != otss.getSummaries()->end(); ++summary)
		{
			uint32_t otce = ((channelid & 0xffff) << 16) | ((*summary)->getEventId() & 0xffff);

			if (m_OPENTV_EIT_map.find(otce) != m_OPENTV_EIT_map.end())
			{
				struct opentv_event ote = m_OPENTV_EIT_map[otce];

				//cache events with matching title and summary eventId on the fly!
				if (m_OPENTV_descriptors_map.find(ote.title_crc) != m_OPENTV_descriptors_map.end())
				{
					std::vector<int> sids;
					std::vector<eDVBChannelID> chids;
					eDVBChannelID chid = channel->getChannelID();
					chid.transport_stream_id = m_OPENTV_channels_map[channelid].transportStreamId;
					chid.original_network_id = m_OPENTV_channels_map[channelid].originalNetworkId;
					chids.push_back(chid);
					sids.push_back(m_OPENTV_channels_map[channelid].serviceId);

					// hack to fix split titles
					std::string sTitle = m_OPENTV_descriptors_map[ote.title_crc];
					std::string sSummary = (*summary)->getSummary();

					if (sTitle.length() > 3 && sSummary.length() > 3)
					{
						// check if the title is split
						if (sTitle.substr(sTitle.length() - 3) == "..." && sSummary.substr(0, 3) == "...")
						{
							// find the end of the title in the sumarry
							std::size_t found = sSummary.find_first_of(".:!?", 4);

							if (found < sSummary.length())
							{
								std::string sTmpTitle;
								std::string sTmpSummary;

								// strip off the ellipsis and any leading/trailing space
								if (sTitle.substr(sTitle.length() - 4, 1) == " ")
								{
									sTmpTitle  = sTitle.substr(0, sTitle.length() - 4);
								}
								else
								{
									sTmpTitle = sTitle.substr(0, sTitle.length() - 3);
								}

								if (sSummary.substr(3, 1) == " ")
								{
									sTmpSummary  = sSummary.substr(4);
								}
								else
								{
									sTmpSummary = sSummary.substr(3);
								}

								// construct the new title and summary
								found = sTmpSummary.find_first_of(".:!?");
								if (found < sTmpSummary.length())
								{
									sTitle = sTmpTitle + " " + sTmpSummary.substr(0, found);
									if (sTmpSummary.length() - found > 2)
									{
										sSummary = sTmpSummary.substr(found + 2);
									}
									else
									{
										sSummary = "";
									}
								}
								else
								{
									// shouldn't happen, but you never know...
									sTitle + sTmpTitle;
									sSummary = sTmpSummary;
								}
							}
						}
					}
					if (eEPGCache::getInstance())
						eEPGCache::getInstance()->submitEventData(sids, chids, ote.startTime, ote.duration, sTitle.c_str(), "", sSummary.c_str(), 0, eEPGCache::OPENTV, ote.eventId);
				}
				m_OPENTV_EIT_map.erase(otce);
			}
		}
	}
	haveData |= eEPGCache::OPENTV;

	OPENTV_checkCompletion(otss.getCrc32());
}

void eEPGChannelData::cleanupOPENTV()
{
	m_OPENTV_Timer->stop();
	if (m_OPENTV_ChannelsReader)
		m_OPENTV_ChannelsReader->stop();
	if (m_OPENTV_TitlesReader)
		m_OPENTV_TitlesReader->stop();
	if (m_OPENTV_SummariesReader)
		m_OPENTV_SummariesReader->stop();
	m_OPENTV_ChannelsConn = NULL;
	m_OPENTV_TitlesConn = NULL;
	m_OPENTV_SummariesConn = NULL;
	m_OPENTV_channels_map.clear();
	m_OPENTV_descriptors_map.clear();
	m_OPENTV_EIT_map.clear();

	if (huffman_dictionary_read)
	{
		huffman_free_dictionary();
		huffman_dictionary_read = false;
	}

	if (isRunning & eEPGCache::OPENTV)
		isRunning &= ~eEPGCache::OPENTV;
}
#endif // ENABLE_OPENTV
