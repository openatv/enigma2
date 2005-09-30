#include <lib/service/event.h>
#include <lib/base/estring.h>
#include <dvbsi++/event_information_section.h>
#include <dvbsi++/short_event_descriptor.h>
#include <dvbsi++/descriptor_tag.h>

DEFINE_REF(eServiceEvent);

RESULT eServiceEvent::parseFrom(Event *evt)
{
	m_begin = 0; 	// ich bin FAUL
	m_duration = (evt->getDuration() & 0xFF) + ((evt->getDuration() >> 8) & 0xFF) * 60 + ((evt->getDuration() >> 16) & 0xFF) * 24 * 60;
	
	for (DescriptorConstIterator desc = evt->getDescriptors()->begin(); desc != evt->getDescriptors()->end(); ++desc)
	{
		switch ((*desc)->getTag())
		{
		case SHORT_EVENT_DESCRIPTOR:
		{
			const ShortEventDescriptor *sed = (ShortEventDescriptor*)*desc;
			m_event_name = convertDVBUTF8(sed->getEventName());
			m_description = convertDVBUTF8(sed->getText());
			break;
		}
		}
	}
	return 0;
}

DEFINE_REF(eDebugClass);
