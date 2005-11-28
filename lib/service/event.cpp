#include <lib/service/event.h>
#include <lib/base/estring.h>
#include <lib/base/encoding.h>
#include <lib/dvb/dvbtime.h>
#include <dvbsi++/event_information_section.h>
#include <dvbsi++/short_event_descriptor.h>
#include <dvbsi++/extended_event_descriptor.h>
#include <dvbsi++/linkage_descriptor.h>
#include <dvbsi++/descriptor_tag.h>

DEFINE_REF(eServiceEvent);

const char MAX_LANG = 37;
/* OSD language (see /share/locales/locales) to iso639 conversion table */
std::string ISOtbl[MAX_LANG][2] =
{
	{"ar_AE","ara"},
	{"C","eng"},
	{"cs_CZ","ces"},     /* or 'cze' */
	{"cs_CZ","cze"},
	{"da_DK","dan"},
	{"de_DE","deu"},     /* also 'ger' is valid iso639 code!! */
	{"de_DE","ger"},
	{"el_GR","gre"},     /* also 'ell' is valid */
	{"el_GR","ell"},
	{"es_ES","esl"},     /* also 'spa' is ok */
	{"es_ES","spa"},
	{"et_EE","est"},
	{"fi_FI","fin"},
	{"fr_FR","fra"},
	{"hr_HR","hrv"},     /* or 'scr' */
	{"hr_HR","scr"},
	{"hu_HU","hun"},
	{"is_IS","isl"},     /* or 'ice' */
	{"is_IS","ice"},
	{"it_IT","ita"},
	{"lt_LT","lit"},
	{"nl_NL","nld"},     /* or 'dut' */
	{"nl_NL","dut"},
	{"no_NO","nor"},
	{"pl_PL","pol"},
	{"pt_PT","por"},
	{"ro_RO","ron"},     /* or 'rum' */
	{"ro_RO","rum"},
	{"ru_RU","rus"},
	{"sk_SK","slk"},     /* or 'slo' */
	{"sk_SK","slo"},
	{"sl_SI","slv"},
	{"sr_YU","srp"},     /* or 'scc' */
	{"sr_YU","scc"},
	{"sv_SE","swe"},
	{"tr_TR","tur"},
	{"ur_IN","urd"}
};

/* search for the presence of language from given EIT event descriptors*/
bool eServiceEvent::loadLanguage(Event *evt, std::string lang, int tsidonid)
{
	bool retval=0;
	for (DescriptorConstIterator desc = evt->getDescriptors()->begin(); desc != evt->getDescriptors()->end(); ++desc)
	{
		switch ((*desc)->getTag())
		{
			case LINKAGE_DESCRIPTOR:
				m_linkage_services.clear();
				break;
			case SHORT_EVENT_DESCRIPTOR:
			{
				const ShortEventDescriptor *sed = (ShortEventDescriptor*)*desc;
				const std::string &cc = sed->getIso639LanguageCode();
				int table=encodingHandler.getCountryCodeDefaultMapping(cc);
				if (lang.empty() || cc == lang)
				{
					m_event_name = convertDVBUTF8(sed->getEventName(), table, tsidonid);
					m_short_description = convertDVBUTF8(sed->getText(), table, tsidonid);
					retval=1;
				}
				break;
			}
			case EXTENDED_EVENT_DESCRIPTOR:
			{
				const ExtendedEventDescriptor *eed = (ExtendedEventDescriptor*)*desc;
				const std::string &cc = eed->getIso639LanguageCode();
				int table=encodingHandler.getCountryCodeDefaultMapping(cc);
				if (lang.empty() || cc == lang)
				{
					m_extended_description += convertDVBUTF8(eed->getText(), table, tsidonid);
					retval=1;
				}
#if 0
				const ExtendedEventList *itemlist = eed->getItems();
				for (ExtendedEventConstIterator it = itemlist->begin(); it != itemlist->end(); ++it)
				{
					m_extended_description += '\n';
					m_extended_description += convertDVBUTF8((*it)->getItemDescription());
					m_extended_description += ' ';
					m_extended_description += convertDVBUTF8((*it)->getItem());
				}
#endif
				break;
			}
			default:
				break;
		}
	}
	if ( retval == 1 )
	{
		for (DescriptorConstIterator desc = evt->getDescriptors()->begin(); desc != evt->getDescriptors()->end(); ++desc)
		{
			switch ((*desc)->getTag())
			{
				case LINKAGE_DESCRIPTOR:
				{
					const LinkageDescriptor  *ld = (LinkageDescriptor*)*desc;
					if ( ld->getLinkageType() == 0xB0 )
					{
						linkage_service s;
						s.onid = ld->getOriginalNetworkId();
						s.tsid = ld->getTransportStreamId();
						s.sid = ld->getServiceId();
						const PrivateDataByteVector *privateData =
							ld->getPrivateDataBytes();
						s.description.assign((const char*)&((*privateData)[0]), privateData->size());
						m_linkage_services.push_back(s);
					}
					break;
				}
			}
		}
	}
	if ( m_extended_description.find(m_short_description) == 0 )
		m_short_description="";
	return retval;
}

RESULT eServiceEvent::parseFrom(Event *evt, int tsidonid)
{
	uint16_t stime_mjd = evt->getStartTimeMjd();
	uint32_t stime_bcd = evt->getStartTimeBcd();
	uint32_t duration = evt->getDuration();
	m_begin = parseDVBtime(
		stime_mjd >> 8,
		stime_mjd&0xFF,
		stime_bcd >> 16,
		(stime_bcd >> 8)&0xFF,
		stime_bcd & 0xFF
	);
	m_duration = fromBCD(duration>>16)*3600+fromBCD(duration>>8)*60+fromBCD(duration);
	std::string country="de_DE";  // TODO use local data here
	for (int i=0; i < MAX_LANG; i++)
		if (country==ISOtbl[i][0])
			if (loadLanguage(evt, ISOtbl[i][1], tsidonid))
				return 0;
	if (loadLanguage(evt, "eng", tsidonid))
		return 0;
	if (loadLanguage(evt, std::string(), tsidonid))
		return 0;
	return 0;
}

std::string eServiceEvent::getBeginTimeString()
{
	tm t;
	localtime_r(&m_begin, &t);
	char tmp[13];
	snprintf(tmp, 13, "%02d.%02d, %02d:%02d",
		t.tm_mday, t.tm_mon+1,
		t.tm_hour, t.tm_min);
	return std::string(tmp, 12);
}

DEFINE_REF(eDebugClass);
