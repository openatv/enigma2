#include <lib/dvb/pmtparse.h>
#include <lib/dvb/dvb.h>
#include <dvbsi++/ca_descriptor.h>
#include <dvbsi++/ca_program_map_section.h>
#include <dvbsi++/teletext_descriptor.h>
#include <dvbsi++/descriptor_tag.h>
#include <dvbsi++/iso639_language_descriptor.h>
#include <dvbsi++/stream_identifier_descriptor.h>
#include <dvbsi++/subtitling_descriptor.h>
#include <dvbsi++/teletext_descriptor.h>
#include <dvbsi++/video_stream_descriptor.h>
#include <dvbsi++/registration_descriptor.h>
#include <dvbsi++/simple_application_location_descriptor.h>
#include <dvbsi++/simple_application_boundary_descriptor.h>
#include <dvbsi++/transport_protocol_descriptor.h>

eDVBPMTParser::eDVBPMTParser()
{
	CONNECT(m_PMT.tableReady, eDVBPMTParser::PMTready);
}

void eDVBPMTParser::clearProgramInfo(program &program)
{
	program.videoStreams.clear();
	program.audioStreams.clear();
	program.subtitleStreams.clear();
	program.pcrPid = -1;
	program.pmtPid = -1;
	program.textPid = -1;
	program.aitPid = -1;
	program.dsmccPid = -1;
	program.serviceId = -1;
	program.adapterId = -1;
	program.demuxId = -1;

	program.defaultAudioStream = 0;
	program.defaultSubtitleStream = -1;
}

int eDVBPMTParser::getProgramInfo(program &program)
{
	ePtr<eTable<ProgramMapSection> > ptr;
	int ret = -1;

	clearProgramInfo(program);

	if (!m_PMT.getCurrent(ptr))
	{
		audioStream *prev_audio = 0;
		eDVBTableSpec table_spec;
		ptr->getSpec(table_spec);
		program.pmtPid = table_spec.pid < 0x1fff ? table_spec.pid : -1;
		std::vector<ProgramMapSection*>::const_iterator i;
		for (i = ptr->getSections().begin(); i != ptr->getSections().end(); ++i)
		{
			const ProgramMapSection &pmt = **i;
			int is_hdmv = 0;

			program.serviceId = pmt.getProgramNumber();
			program.pcrPid = pmt.getPcrPid();

			for (DescriptorConstIterator desc = pmt.getDescriptors()->begin();
				desc != pmt.getDescriptors()->end(); ++desc)
			{
				if ((*desc)->getTag() == CA_DESCRIPTOR)
				{
					CaDescriptor *descr = (CaDescriptor*)(*desc);
					program::capid_pair pair;
					pair.caid = descr->getCaSystemId();
					pair.capid = descr->getCaPid();
					program.caids.push_back(pair);
				}
				else if ((*desc)->getTag() == REGISTRATION_DESCRIPTOR)
				{
					RegistrationDescriptor *d = (RegistrationDescriptor*)(*desc);
					if (d->getFormatIdentifier() == 0x48444d56) // HDMV
						is_hdmv = 1;
				}
			}

			ElementaryStreamInfoConstIterator es;
			for (es = pmt.getEsInfo()->begin(); es != pmt.getEsInfo()->end(); ++es)
			{
				int isaudio = 0, isvideo = 0, issubtitle = 0, forced_video = 0, forced_audio = 0, isteletext = 0;
				int streamtype = (*es)->getType();
				videoStream video;
				audioStream audio;
				audio.component_tag=video.component_tag=-1;
				video.type = videoStream::vtMPEG2;
				audio.type = audioStream::atMPEG;
				audio.rdsPid = -1;

				switch (streamtype)
				{
				case 0x1b: // AVC Video Stream (MPEG4 H264)
					video.type = videoStream::vtMPEG4_H264;
					isvideo = 1;
					//break; fall through !!!
				case 0x24: // H265 HEVC
				case 0x27: // H265 HEVC
					if (!isvideo)
					{
						video.type = videoStream::vtH265_HEVC;
						isvideo = 1;
					}
				case 0x10: // MPEG 4 Part 2
					if (!isvideo)
					{
						video.type = videoStream::vtMPEG4_Part2;
						isvideo = 1;
					}
					//break; fall through !!!
				case 0x01: // MPEG 1 video
					if (!isvideo)
						video.type = videoStream::vtMPEG1;
					//break; fall through !!!
				case 0x02: // MPEG 2 video
					isvideo = 1;
					forced_video = 1;
					//break; fall through !!!
				case 0x03: // MPEG 1 audio
				case 0x04: // MPEG 2 audio:
					if (!isvideo) {
						isaudio = 1;
						forced_audio = 1;
					}
					//break; fall through !!!
				case 0x0f: // MPEG 2 AAC
					if (!isvideo && !isaudio)
					{
						isaudio = 1;
						audio.type = audioStream::atAAC;
						forced_audio = 1;
					}
					//break; fall through !!!
				case 0x11: // MPEG 4 AAC
					if (!isvideo && !isaudio)
					{
						isaudio = 1;
						audio.type = audioStream::atAACHE;
						forced_audio = 1;
					}
				case 0x80: // user private ... but bluray LPCM
				case 0xA0: // bluray secondary LPCM
					if (!isvideo && !isaudio && is_hdmv)
					{
						isaudio = 1;
						audio.type = audioStream::atLPCM;
					}
				case 0x81: // user private ... but bluray AC3
				case 0xA1: // bluray secondary AC3
					if (!isvideo && !isaudio)
					{
						isaudio = 1;
						audio.type = audioStream::atAC3;
					}
				case 0x82: // bluray DTS (dvb user private...)
				case 0xA2: // bluray secondary DTS
					if (!isvideo && !isaudio && is_hdmv)
					{
						isaudio = 1;
						audio.type = audioStream::atDTS;
					}
				case 0x85: // bluray DTS-HD HRA(dvb user private...)
				case 0x86: // bluray DTS-HD MA(dvb user private...)
				case 0xA6: // bluray secondary DTS-HD
					if (!isvideo && !isaudio && is_hdmv)
					{
						isaudio = 1;
						audio.type = audioStream::atDTSHD;
					}
				case 0x06: // PES Private
				case 0xEA: // TS_PSI_ST_SMPTE_VC1
				{
					int num_descriptors = 0;
					for (DescriptorConstIterator desc = (*es)->getDescriptors()->begin();
						desc != (*es)->getDescriptors()->end(); ++desc)
					{
						uint8_t tag = (*desc)->getTag();
						/* check descriptors to get the exakt stream type. */
						++num_descriptors;
						if (!forced_video && !forced_audio)
						{
							switch (tag)
							{
							case AUDIO_STREAM_DESCRIPTOR:
								isaudio = 1;
								break;
							case VIDEO_STREAM_DESCRIPTOR:
							{
								isvideo = 1;
								VideoStreamDescriptor *d = (VideoStreamDescriptor*)(*desc);
								if (d->getMpeg1OnlyFlag())
									video.type = videoStream::vtMPEG1;
								break;
							}
							case SUBTITLING_DESCRIPTOR:
							{
								SubtitlingDescriptor *d = (SubtitlingDescriptor*)(*desc);
								const SubtitlingList *list = d->getSubtitlings();
								subtitleStream s;
								s.pid = (*es)->getPid();
								for (SubtitlingConstIterator it(list->begin()); it != list->end(); ++it)
								{
									s.subtitling_type = (*it)->getSubtitlingType();
									switch(s.subtitling_type)
									{
									case 0x10 ... 0x13: // dvb subtitles normal
									case 0x20 ... 0x23: // dvb subtitles hearing impaired
										break;
									default:
										eDebug("[eDVBPMTParser] dvb subtitle %s PID %04x with wrong subtitling type (%02x)... force 0x10!!",
										s.language_code.c_str(), s.pid, s.subtitling_type);
										s.subtitling_type = 0x10;
										break;
									}
									s.composition_page_id = (*it)->getCompositionPageId();
									s.ancillary_page_id = (*it)->getAncillaryPageId();
									std::string language = (*it)->getIso639LanguageCode();
									s.language_code = language;
//								eDebug("[eDVBPMTParser] add dvb subtitle %s PID %04x, type %d, composition page %d, ancillary_page %d", s.language_code.c_str(), s.pid, s.subtitling_type, s.composition_page_id, s.ancillary_page_id);
									issubtitle = 1;
									program.subtitleStreams.push_back(s);
								}
								break;
							}
							case TELETEXT_DESCRIPTOR:
								if (program.textPid == -1)
								{
									subtitleStream s;
									s.subtitling_type = 0x01; // EBU TELETEXT SUBTITLES
									s.pid = program.textPid = (*es)->getPid();
									TeletextDescriptor *d = (TeletextDescriptor*)(*desc);
									isteletext = 1;
									const VbiTeletextList *list = d->getVbiTeletexts();
									std::string language;
									for (VbiTeletextConstIterator it(list->begin()); it != list->end(); ++it)
									{
										switch((*it)->getTeletextType())
										{
										case 0x02: // Teletext subtitle page
										case 0x05: // Teletext subtitle page for hearing impaired pepople
											language = (*it)->getIso639LanguageCode();
											s.language_code = language;
											s.teletext_page_number = (*it)->getTeletextPageNumber();
											s.teletext_magazine_number = (*it)->getTeletextMagazineNumber();
//										eDebug("[eDVBPMTParser] add teletext subtitle %s PID %04x, page number %d, magazine number %d", s.language_code.c_str(), s.pid, s.teletext_page_number, s.teletext_magazine_number);
											program.subtitleStreams.push_back(s);
											issubtitle=1;
										default:
											break;
										}
									}
								}
								break;
							case DTS_DESCRIPTOR:
								isaudio = 1;
								audio.type = audioStream::atDTS;
								break;
							case 0x2B: // TS_PSI_DT_MPEG2_AAC
								isaudio = 1;
								audio.type = audioStream::atAAC; // MPEG2-AAC
								break;
							case 0x1C: // TS_PSI_DT_MPEG4_Audio
							case AAC_DESCRIPTOR:
								isaudio = 1;
								audio.type = audioStream::atAACHE; // MPEG4-AAC
								break;
							case AC3_DESCRIPTOR:
								isaudio = 1;
								audio.type = audioStream::atAC3;
								break;
							case ENHANCED_AC3_DESCRIPTOR:
								isaudio = 1;
								audio.type = audioStream::atDDP;
								break;
							case REGISTRATION_DESCRIPTOR: /* some services don't have a separate AC3 descriptor */
							{
								RegistrationDescriptor *d = (RegistrationDescriptor*)(*desc);
								switch (d->getFormatIdentifier())
								{
								case 0x44545331 ... 0x44545333: // DTS1/DTS2/DTS3
									isaudio = 1;
									audio.type = audioStream::atDTS;
									break;
								case 0x41432d33: // == 'AC-3'
									isaudio = 1;
									audio.type = audioStream::atAC3;
									break;
								case 0x42535344: // == 'BSSD' (LPCM)
									isaudio = 1;
									audio.type = audioStream::atLPCM;
									break;
								case 0x56432d31: // == 'VC-1'
								{
									const AdditionalIdentificationInfoVector *vec = d->getAdditionalIdentificationInfo();
									if (vec->size() > 1 && (*vec)[0] == 0x01) // subdescriptor tag
									{
										if ((*vec)[1] >= 0x90) // profile_level
											video.type = videoStream::vtVC1; // advanced profile
										else
											video.type = videoStream::vtVC1_SM; // simple main
										isvideo = 1;
									}
								}
								case 0x48455643: /*HEVC */
									isvideo = 1;
									video.type = videoStream::vtH265_HEVC;
									break;
								default:
									break;
								}
								break;
							}
							case 0x28: // TS_PSI_DT_AVC
								isvideo = 1;
								video.type = videoStream::vtMPEG4_H264;
								break;
							case 0x1B: // TS_PSI_DT_MPEG4_Video
								isvideo = 1;
								video.type = videoStream::vtMPEG4_Part2;
								break;
							default:
								break;
							}
						}
						switch (tag)
						{
						case ISO_639_LANGUAGE_DESCRIPTOR:
							if (!isvideo)
							{
								const Iso639LanguageList *languages = ((Iso639LanguageDescriptor*)*desc)->getIso639Languages();
								/* use last language code */
								int cnt=0;
								for (Iso639LanguageConstIterator i=languages->begin(); i != languages->end(); ++i)
								{
									std::string language=(*i)->getIso639LanguageCode();
									if ( cnt==0 )
										audio.language_code = language;
									else
										audio.language_code += "/" + language;
									cnt++;
								}
							}
							break;
						case STREAM_IDENTIFIER_DESCRIPTOR:
							audio.component_tag =
								video.component_tag =
									((StreamIdentifierDescriptor*)*desc)->getComponentTag();
							break;
						case CA_DESCRIPTOR:
						{
							CaDescriptor *descr = (CaDescriptor*)(*desc);
							program::capid_pair pair;
							pair.caid = descr->getCaSystemId();
							pair.capid = descr->getCaPid();
							program.caids.push_back(pair);
							break;
						}
						default:
							break;
						}
					}
					if (!num_descriptors && streamtype == 0x06 && prev_audio)
					{
						prev_audio->rdsPid = (*es)->getPid();
						eDebug("[eDVBPMTParser] Rds PID %04x detected ? ! ?", prev_audio->rdsPid);
					}
					prev_audio = 0;
					break;
				}
				case 0x05: /* ITU-T Rec. H.222.0 | ISO/IEC 13818-1 private sections */
				{
					for (DescriptorConstIterator desc = (*es)->getDescriptors()->begin();
						desc != (*es)->getDescriptors()->end(); ++desc)
					{
						switch ((*desc)->getTag())
						{
						case APPLICATION_SIGNALLING_DESCRIPTOR:
							program.aitPid = (*es)->getPid();
							break;
						}
					}
					break;
				}
				case 0x0b: /* ISO/IEC 13818-6 DSM-CC U-N Messages */
				{
					for (DescriptorConstIterator desc = (*es)->getDescriptors()->begin();
						desc != (*es)->getDescriptors()->end(); ++desc)
					{
						switch ((*desc)->getTag())
						{
						case CAROUSEL_IDENTIFIER_DESCRIPTOR:
							program.dsmccPid = (*es)->getPid();
							break;
						case STREAM_IDENTIFIER_DESCRIPTOR:
							break;
						}
					}
					break;
				}
				default:
					break;
				}
				if (isteletext && (isaudio || isvideo))
				{
					eDebug("[eDVBPMTParser] ambiguous streamtype for PID %04x detected.. forced as teletext!", (*es)->getPid());
					continue; // continue with next PID
				}
				else if (issubtitle && (isaudio || isvideo))
					eDebug("[eDVBPMTParser] ambiguous streamtype for PID %04x detected.. forced as subtitle!", (*es)->getPid());
				else if (isaudio && isvideo)
					eDebug("[eDVBPMTParser] ambiguous streamtype for PID %04x detected.. forced as video!", (*es)->getPid());
				if (issubtitle) // continue with next PID
					continue;
				else if (isvideo)
				{
					video.pid = (*es)->getPid();
					program.videoStreams.push_back(video);
				}
				else if (isaudio)
				{
					audio.pid = (*es)->getPid();
					program.audioStreams.push_back(audio);
					prev_audio = &program.audioStreams.back();
				}
				else
					continue;
			}
		}
		ret = 0;
	}
	return ret;
}

DEFINE_REF(eDVBPMTParser::eStreamData);

eDVBPMTParser::eStreamData::eStreamData(eDVBPMTParser::program &program)
{
	for (std::vector<eDVBPMTParser::videoStream>::const_iterator i(program.videoStreams.begin()); i != program.videoStreams.end(); ++i)
		videoStreams.push_back(i->pid);
	for (std::vector<eDVBPMTParser::audioStream>::const_iterator i(program.audioStreams.begin()); i != program.audioStreams.end(); ++i)
		audioStreams.push_back(i->pid);
	for (std::vector<eDVBPMTParser::subtitleStream>::const_iterator i(program.subtitleStreams.begin()); i != program.subtitleStreams.end(); ++i)
		subtitleStreams.push_back(i->pid);
	pcrPid = program.pcrPid;
	pmtPid = program.pmtPid;
	textPid = program.textPid;
	aitPid = program.aitPid;
	adapterId = program.adapterId;
	demuxId = program.demuxId;
	serviceId = program.serviceId;
	for (std::list<eDVBPMTParser::program::capid_pair>::const_iterator it(program.caids.begin()); it != program.caids.end(); ++it)
	{
		caIds.push_back(it->caid);
		ecmPids.push_back(it->capid);
	}
}

RESULT eDVBPMTParser::eStreamData::getAllPids(std::vector<int> &result) const
{
	int pid;
	getVideoPids(result);
	getAudioPids(result);
	getSubtitlePids(result);
	if (getPcrPid(pid) >= 0) result.push_back(pid);
	if (getPatPid(pid) >= 0) result.push_back(pid);
	if (getPmtPid(pid) >= 0) result.push_back(pid);
	if (getTxtPid(pid) >= 0) result.push_back(pid);
	if (getAitPid(pid) >= 0) result.push_back(pid);
	return 0;
}

RESULT eDVBPMTParser::eStreamData::getVideoPids(std::vector<int> &result) const
{
	for (unsigned int i = 0; i < videoStreams.size(); i++)
	{
		result.push_back(videoStreams[i]);
	}
	return 0;
}

RESULT eDVBPMTParser::eStreamData::getAudioPids(std::vector<int> &result) const
{
	for (unsigned int i = 0; i < audioStreams.size(); i++)
	{
		result.push_back(audioStreams[i]);
	}
	return 0;
}

RESULT eDVBPMTParser::eStreamData::getSubtitlePids(std::vector<int> &result) const
{
	for (unsigned int i = 0; i < subtitleStreams.size(); i++)
	{
		result.push_back(subtitleStreams[i]);
	}
	return 0;
}

RESULT eDVBPMTParser::eStreamData::getPmtPid(int &result) const
{
	result = pmtPid;
	return 0;
}

RESULT eDVBPMTParser::eStreamData::getPatPid(int &result) const
{
	result = 0;
	return 0;
}

RESULT eDVBPMTParser::eStreamData::getPcrPid(int &result) const
{
	result = pcrPid;
	return 0;
}

RESULT eDVBPMTParser::eStreamData::getTxtPid(int &result) const
{
	result = textPid;
	return 0;
}

RESULT eDVBPMTParser::eStreamData::getAitPid(int &result) const
{
	result = aitPid;
	return 0;
}

RESULT eDVBPMTParser::eStreamData::getServiceId(int &result) const
{
	result = serviceId;
	return 0;
}

RESULT eDVBPMTParser::eStreamData::getAdapterId(int &result) const
{
	result = adapterId;
	return 0;
}

RESULT eDVBPMTParser::eStreamData::getDemuxId(int &result) const
{
	result = demuxId;
	return 0;
}

RESULT eDVBPMTParser::eStreamData::getCaIds(std::vector<int> &caids, std::vector<int> &ecmpids) const
{
	for (unsigned int i = 0; (i < caIds.size()) && (i < ecmPids.size()); i++)
	{
		caids.push_back(caIds[i]);
		ecmpids.push_back(ecmPids[i]);
	}
	return 0;
}
