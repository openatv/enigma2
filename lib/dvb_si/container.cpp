/*
 * $Id: container.cpp,v 1.1 2003-10-17 15:36:37 tmbinc Exp $
 *
 * (C) 2002-2003 Andreas Oberritter <obi@saftware.de>
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
 *
 */

#include <lib/dvb_si/ac3_descriptor.h>
#include <lib/dvb_si/ancillary_data_descriptor.h>
#include <lib/dvb_si/announcement_support_descriptor.h>
#include <lib/dvb_si/application_signalling_descriptor.h>
#include <lib/dvb_si/audio_stream_descriptor.h>
#include <lib/dvb_si/bouquet_name_descriptor.h>
#include <lib/dvb_si/ca_descriptor.h>
#include <lib/dvb_si/ca_identifier_descriptor.h>
#include <lib/dvb_si/ca_system_descriptor.h>
#include <lib/dvb_si/cable_delivery_system_descriptor.h>
#include <lib/dvb_si/cell_frequency_link_descriptor.h>
#include <lib/dvb_si/cell_list_descriptor.h>
#include <lib/dvb_si/component_descriptor.h>
#include <lib/dvb_si/container.h>
#include <lib/dvb_si/content_descriptor.h>
#include <lib/dvb_si/country_availability_descriptor.h>
#include <lib/dvb_si/data_broadcast_descriptor.h>
#include <lib/dvb_si/data_broadcast_id_descriptor.h>
#include <lib/dvb_si/extended_event_descriptor.h>
#include <lib/dvb_si/frequency_list_descriptor.h>
#include <lib/dvb_si/iso639_language_descriptor.h>
#include <lib/dvb_si/linkage_descriptor.h>
#include <lib/dvb_si/local_time_offset_descriptor.h>
#include <lib/dvb_si/mosaic_descriptor.h>
#include <lib/dvb_si/multilingual_bouquet_name_descriptor.h>
#include <lib/dvb_si/multilingual_component_descriptor.h>
#include <lib/dvb_si/multilingual_network_name_descriptor.h>
#include <lib/dvb_si/multilingual_service_name_descriptor.h>
#include <lib/dvb_si/network_name_descriptor.h>
#include <lib/dvb_si/nvod_reference_descriptor.h>
#include <lib/dvb_si/parental_rating_descriptor.h>
#include <lib/dvb_si/pdc_descriptor.h>
#include <lib/dvb_si/private_data_specifier_descriptor.h>
#include <lib/dvb_si/satellite_delivery_system_descriptor.h>
#include <lib/dvb_si/service_descriptor.h>
#include <lib/dvb_si/service_list_descriptor.h>
#include <lib/dvb_si/service_move_descriptor.h>
#include <lib/dvb_si/short_event_descriptor.h>
#include <lib/dvb_si/stream_identifier_descriptor.h>
#include <lib/dvb_si/stuffing_descriptor.h>
#include <lib/dvb_si/subtitling_descriptor.h>
#include <lib/dvb_si/target_background_grid_descriptor.h>
#include <lib/dvb_si/telephone_descriptor.h>
#include <lib/dvb_si/teletext_descriptor.h>
#include <lib/dvb_si/terrestrial_delivery_system_descriptor.h>
#include <lib/dvb_si/time_shifted_service_descriptor.h>
#include <lib/dvb_si/vbi_data_descriptor.h>
#include <lib/dvb_si/vbi_teletext_descriptor.h>
#include <lib/dvb_si/video_stream_descriptor.h>
#include <lib/dvb_si/video_window_descriptor.h>
#include <lib/dvb_si/descriptor_tag.h>

DescriptorContainer::~DescriptorContainer(void)
{
	for (DescriptorIterator i = descriptorVector.begin(); i != descriptorVector.end(); ++i)
		delete *i;
}

void DescriptorContainer::descriptor(const uint8_t * const buffer)
{
	switch (buffer[0]) {
	case VIDEO_STREAM_DESCRIPTOR:
		descriptorVector.push_back(new VideoStreamDescriptor(buffer));
		break;

	case AUDIO_STREAM_DESCRIPTOR:
		descriptorVector.push_back(new AudioStreamDescriptor(buffer));
		break;

	case TARGET_BACKGROUND_GRID_DESCRIPTOR:
		descriptorVector.push_back(new TargetBackgroundGridDescriptor(buffer));
		break;

	case VIDEO_WINDOW_DESCRIPTOR:
		descriptorVector.push_back(new VideoWindowDescriptor(buffer));
		break;

	case CA_DESCRIPTOR:
		descriptorVector.push_back(new CaDescriptor(buffer));
		break;

	case ISO_639_LANGUAGE_DESCRIPTOR:
		descriptorVector.push_back(new Iso639LanguageDescriptor(buffer));
		break;

	case NETWORK_NAME_DESCRIPTOR:
		descriptorVector.push_back(new NetworkNameDescriptor(buffer));
		break;

	case SERVICE_LIST_DESCRIPTOR:
		descriptorVector.push_back(new ServiceListDescriptor(buffer));
		break;

	case STUFFING_DESCRIPTOR:
		descriptorVector.push_back(new StuffingDescriptor(buffer));
		break;

	case SATELLITE_DELIVERY_SYSTEM_DESCRIPTOR:
		descriptorVector.push_back(new SatelliteDeliverySystemDescriptor(buffer));
		break;

	case CABLE_DELIVERY_SYSTEM_DESCRIPTOR:
		descriptorVector.push_back(new CableDeliverySystemDescriptor(buffer));
		break;

	case VBI_DATA_DESCRIPTOR:
		descriptorVector.push_back(new VbiDataDescriptor(buffer));
		break;

	case VBI_TELETEXT_DESCRIPTOR:
		descriptorVector.push_back(new VbiTeletextDescriptor(buffer));
		break;

	case BOUQUET_NAME_DESCRIPTOR:
		descriptorVector.push_back(new BouquetNameDescriptor(buffer));
		break;

	case SERVICE_DESCRIPTOR:
		descriptorVector.push_back(new ServiceDescriptor(buffer));
		break;

	case COUNTRY_AVAILABILITY_DESCRIPTOR:
		descriptorVector.push_back(new CountryAvailabilityDescriptor(buffer));
		break;

	case LINKAGE_DESCRIPTOR:
		descriptorVector.push_back(new LinkageDescriptor(buffer));
		break;

	case NVOD_REFERENCE_DESCRIPTOR:
		descriptorVector.push_back(new NvodReferenceDescriptor(buffer));
		break;

	case TIME_SHIFTED_SERVICE_DESCRIPTOR:
		descriptorVector.push_back(new TimeShiftedServiceDescriptor(buffer));
		break;

	case SHORT_EVENT_DESCRIPTOR:
		descriptorVector.push_back(new ShortEventDescriptor(buffer));
		break;

	case EXTENDED_EVENT_DESCRIPTOR:
		descriptorVector.push_back(new ExtendedEventDescriptor(buffer));
		break;

	case COMPONENT_DESCRIPTOR:
		descriptorVector.push_back(new ComponentDescriptor(buffer));
		break;

	case MOSAIC_DESCRIPTOR:
		descriptorVector.push_back(new MosaicDescriptor(buffer));
		break;

	case STREAM_IDENTIFIER_DESCRIPTOR:
		descriptorVector.push_back(new StreamIdentifierDescriptor(buffer));
		break;

	case CA_IDENTIFIER_DESCRIPTOR:
		descriptorVector.push_back(new CaIdentifierDescriptor(buffer));
		break;

	case CONTENT_DESCRIPTOR:
		descriptorVector.push_back(new ContentDescriptor(buffer));
		break;

	case PARENTAL_RATING_DESCRIPTOR:
		descriptorVector.push_back(new ParentalRatingDescriptor(buffer));
		break;

	case TELETEXT_DESCRIPTOR:
		descriptorVector.push_back(new TeletextDescriptor(buffer));
		break;

	case TELEPHONE_DESCRIPTOR:
		descriptorVector.push_back(new TelephoneDescriptor(buffer));
		break;

	case LOCAL_TIME_OFFSET_DESCRIPTOR:
		descriptorVector.push_back(new LocalTimeOffsetDescriptor(buffer));
		break;

	case SUBTITLING_DESCRIPTOR:
		descriptorVector.push_back(new SubtitlingDescriptor(buffer));
		break;

	case TERRESTRIAL_DELIVERY_SYSTEM_DESCRIPTOR:
		descriptorVector.push_back(new TerrestrialDeliverySystemDescriptor(buffer));
		break;

	case MULTILINGUAL_NETWORK_NAME_DESCRIPTOR:
		descriptorVector.push_back(new MultilingualNetworkNameDescriptor(buffer));
		break;

	case MULTILINGUAL_BOUQUET_NAME_DESCRIPTOR:
		descriptorVector.push_back(new MultilingualBouquetNameDescriptor(buffer));
		break;

	case MULTILINGUAL_SERVICE_NAME_DESCRIPTOR:
		descriptorVector.push_back(new MultilingualServiceNameDescriptor(buffer));
		break;

	case MULTILINGUAL_COMPONENT_DESCRIPTOR:
		descriptorVector.push_back(new MultilingualComponentDescriptor(buffer));
		break;

	case PRIVATE_DATA_SPECIFIER_DESCRIPTOR:
		descriptorVector.push_back(new PrivateDataSpecifierDescriptor(buffer));
		break;

	case SERVICE_MOVE_DESCRIPTOR:
		descriptorVector.push_back(new ServiceMoveDescriptor(buffer));
		break;

	case FREQUENCY_LIST_DESCRIPTOR:
		descriptorVector.push_back(new FrequencyListDescriptor(buffer));
		break;

	case DATA_BROADCAST_DESCRIPTOR:
		descriptorVector.push_back(new DataBroadcastDescriptor(buffer));
		break;

	case CA_SYSTEM_DESCRIPTOR:
		descriptorVector.push_back(new CaSystemDescriptor(buffer));
		break;

	case DATA_BROADCAST_ID_DESCRIPTOR:
		descriptorVector.push_back(new DataBroadcastIdDescriptor(buffer));
		break;

	case PDC_DESCRIPTOR:
		descriptorVector.push_back(new PdcDescriptor(buffer));
		break;

	case AC3_DESCRIPTOR:
		descriptorVector.push_back(new Ac3Descriptor(buffer));
		break;

	case ANCILLARY_DATA_DESCRIPTOR:
		descriptorVector.push_back(new AncillaryDataDescriptor(buffer));
		break;

	case CELL_LIST_DESCRIPTOR:
		descriptorVector.push_back(new CellListDescriptor(buffer));
		break;

	case CELL_FREQUENCY_LINK_DESCRIPTOR:
		descriptorVector.push_back(new CellFrequencyLinkDescriptor(buffer));
		break;

	case ANNOUNCEMENT_SUPPORT_DESCRIPTOR:
		descriptorVector.push_back(new AnnouncementSupportDescriptor(buffer));
		break;

	case APPLICATION_SIGNALLING_DESCRIPTOR:
		descriptorVector.push_back(new ApplicationSignallingDescriptor(buffer));
		break;

	default:
		descriptorVector.push_back(new Descriptor(buffer));
		break;
	}
}

const DescriptorVector *DescriptorContainer::getDescriptors(void) const
{
	return &descriptorVector;
}

