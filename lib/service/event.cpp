#include <lib/service/event.h>
#include <lib/dvb_si/eit.h>
#include <lib/dvb_si/short_event_descriptor.h>
#include <lib/dvb_si/descriptor_tag.h>

DEFINE_REF(eServiceEvent);

RESULT eServiceEvent::parseFrom(Event *evt)
{
	m_begin = 0; 	// ich bin FAUL
	m_duration = evt->getDuration();
	
	
	for (DescriptorConstIterator desc = evt->getDescriptors()->begin(); desc != evt->getDescriptors()->end(); ++desc)
	{
		switch ((*desc)->getTag())
		{
		case SHORT_EVENT_DESCRIPTOR:
		{
			const ShortEventDescriptor *sed = (ShortEventDescriptor*)*desc;
			m_event_name = sed->getEventName();
			m_description = sed->getText();
			break;
		}
		}
	}
}
