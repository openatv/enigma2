#include <sys/select.h>
#include <unistd.h>
#include <string.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <sys/ioctl.h>

#include <lib/base/eerror.h>
#include <lib/base/init.h>
#include <lib/base/init_num.h>
#include <lib/base/wrappers.h>
#include <lib/base/cfile.h>
#include <lib/nav/core.h>
#include <lib/dvb/encoder.h>
#include <lib/dvb/pmt.h>
#include <lib/service/service.h>

DEFINE_REF(eEncoder);

eEncoder *eEncoder::instance = NULL;

eEncoder *eEncoder::getInstance()
{
	return instance;
}

eEncoder::eEncoder()
{
	int decoder_index;
	ePtr<iServiceHandler> service_center;
	eNavigation *navigation_instance;

	instance = this;
	eServiceCenter::getInstance(service_center);

	if(service_center)
	{
		bcm_encoder = bool(CFile("/dev/bcm_enc0", "r"));

		/*
		 * The Broadcom transcoding engine does not transfer the data to the encoder
		 * itself, so we need to start a thread to do that. Therefore there is no
		 * use to connect a (valid) decoder device. Even more it won't work because
		 * we can't open de encoder when more than two (main, PiP) decoders are in
		 * use. The encoder is reported as "busy" then. That's why we use dummy values
		 * here (4 onwards).
		 *
		 * OTOH the "xtrend" transcoding engine has the video decoder connected to
		 * the selected encoder internally. So we need to use the right decoder,
		 * connected to the selected encoder. This is usually 2 -> 0, 3 -> 1.
		 */

		for(int index = 0; index < 4; index++) // increase this if machines appear with more than 4 encoding engines
		{
			char filename[64];

			snprintf(filename, sizeof(filename), "/proc/stb/encoder/%d/decoder", index);

			if (CFile::parseInt(&decoder_index, filename) < 0)
				break;

			if(bcm_encoder)
				decoder_index = index + 4;

			if((navigation_instance = new eNavigation(service_center, decoder_index)) == nullptr)
				break;

			encoder.push_back(EncoderContext(index, decoder_index, navigation_instance));
		}
	}
}

eEncoder::~eEncoder()
{
	for(int encoder_index = 0; encoder_index < (int)encoder.size(); encoder_index++)
	{
		encoder[encoder_index].state = EncoderContext::state_destroyed;
		encoder[encoder_index].navigation_instance = nullptr; /* apparently we're not allowed to delete */
	}

	instance = nullptr;
}

int eEncoder::allocateEncoder(const std::string &serviceref, int &buffersize,
		int bitrate, int width, int height, int framerate, int interlaced, int aspectratio,
		const std::string &vcodec, const std::string &acodec)
{
	static const char fileref[] = "1:0:1:0:0:0:0:0:0:0:";
	int encoder_index;
	char filename[128];
	std::string source_file;

	eDebug("[eEncoder] allocateEncoder serviceref=%s bitrate=%d width=%d height=%d vcodec=%s acodec=%s",
			serviceref.c_str(), bitrate, width, height, vcodec.c_str(), acodec.c_str());

	// extract file path from serviceref, this is needed for Broadcom transcoding
	if(serviceref.compare(0, sizeof(fileref) - 1, std::string(fileref), 0, std::string::npos) == 0)
		source_file = serviceref.substr(sizeof(fileref) - 1, std::string::npos);

	eDebug("[allocateEncoder] serviceref: %s", serviceref.c_str());
	eDebug("[allocateEncoder] serviceref substr: %s", serviceref.substr(0, sizeof(fileref) - 1).c_str());
	eDebug("[allocateEncoder] source_file: \"%s\"", source_file.c_str());

	for(encoder_index = 0; encoder_index < (int)encoder.size(); encoder_index++)
		if(encoder[encoder_index].state == EncoderContext::state_idle)
			break;

	if(encoder_index >= (int)encoder.size())
	{
		eWarning("[eEncoder] no encoders free");
		return(-1);
	}

	snprintf(filename, sizeof(filename), "/proc/stb/encoder/%d/bitrate", encoder_index);
	CFile::writeInt(filename, bitrate);

	snprintf(filename, sizeof(filename), "/proc/stb/encoder/%d/width", encoder_index);
	CFile::writeInt(filename, width);

	snprintf(filename, sizeof(filename), "/proc/stb/encoder/%d/height", encoder_index);
	CFile::writeInt(filename, height);

	snprintf(filename, sizeof(filename), "/proc/stb/encoder/%d/framerate", encoder_index);
	CFile::writeInt(filename, framerate);

	snprintf(filename, sizeof(filename), "/proc/stb/encoder/%d/interlaced", encoder_index);
	CFile::writeInt(filename, interlaced);

	snprintf(filename, sizeof(filename), "/proc/stb/encoder/%d/aspectratio", encoder_index);
	CFile::writeInt(filename, aspectratio);

	if(!vcodec.empty())
	{
		snprintf(filename, sizeof(filename), "/proc/stb/encoder/%d/vcodec_choices", encoder_index);
		if (CFile::contains_word(filename, vcodec))
		{
			snprintf(filename, sizeof(filename), "/proc/stb/encoder/%d/vcodec", encoder_index);
			CFile::write(filename, vcodec.c_str());
		}
	}

	if(!acodec.empty())
	{
		snprintf(filename, sizeof(filename), "/proc/stb/encoder/%d/acodec_choices", encoder_index);
		if (CFile::contains_word(filename, acodec))
		{
			snprintf(filename, sizeof(filename), "/proc/stb/encoder/%d/acodec", encoder_index);
			CFile::write(filename, acodec.c_str());
		}
	}

	snprintf(filename, sizeof(filename), "/proc/stb/encoder/%d/apply", encoder_index);
	CFile::writeInt(filename, 1);

	if(encoder[encoder_index].navigation_instance->playService(serviceref) < 0)
	{
		eWarning("[eEncoder] navigation->playservice failed");
		return(-1);
	}

	if(!source_file.empty() && ((encoder[encoder_index].file_fd = open(source_file.c_str(), O_RDONLY, 0)) < 0))
	{
		eWarning("[eEncoder] open source file failed");
		return(-1);
	}

	snprintf(filename, sizeof(filename), "/dev/%s%d", bcm_encoder ? "bcm_enc" : "encoder", encoder_index);

	if((encoder[encoder_index].encoder_fd = open(filename, bcm_encoder ? O_RDWR : O_RDONLY)) < 0)
	{
		eWarning("[eEncoder] open encoder failed");
		return(-1);
	}

	if(bcm_encoder)
	{
		buffersize = 188 * 256; /* broadcom magic value */
		encoder[encoder_index].state = EncoderContext::state_wait_pmt;

		switch(encoder_index)
		{
			case(0):
			{
				encoder[encoder_index].navigation_instance->connectEvent(sigc::mem_fun(*this, &eEncoder::navigation_event_0), m_nav_event_connection_0);
				break;
			}

			case(1):
			{
				encoder[encoder_index].navigation_instance->connectEvent(sigc::mem_fun(*this, &eEncoder::navigation_event_1), m_nav_event_connection_1);
				break;
			}

			default:
			{
				eWarning("[eEncoder] only encoder 0 and encoder 1 implemented");
				break;
			}
		}
	}
	else
	{
		buffersize = -1;
		encoder[encoder_index].state = EncoderContext::state_running;
	}

	return(encoder[encoder_index].encoder_fd);
}

void eEncoder::freeEncoder(int encoderfd)
{
	int encoder_index;
	ePtr<iPlayableService> service;
	ePtr<iTapService> tservice;

	if(encoderfd < 0)
	{
		eWarning("[eEncoder] trying to release incorrect encoder %d", encoderfd);
		return;
	}

	for(encoder_index = 0; encoder_index < (int)encoder.size(); encoder_index++)
		if(encoder[encoder_index].encoder_fd == encoderfd)
			break;

	if(encoder_index >= (int)encoder.size())
	{
		eWarning("[eEncoder] encoder with fd=%d not found", encoderfd);
		return;
	}

	switch(encoder[encoder_index].state)
	{
		case(EncoderContext::state_idle):
		case(EncoderContext::state_finishing):
		case(EncoderContext::state_destroyed):
		{
			eWarning("[eEncoder] trying to release inactive encoder %d fd=%d, state=%d", encoder_index, encoderfd, encoder[encoder_index].state);
			return;
		}
	}

	if(encoder[encoder_index].stream_thread != nullptr)
	{
		encoder[encoder_index].stream_thread->stop();
		delete encoder[encoder_index].stream_thread;
		encoder[encoder_index].stream_thread = nullptr;
	}

	encoder[encoder_index].state = EncoderContext::state_finishing;
	encoder[encoder_index].kill();

	encoder[encoder_index].navigation_instance->getCurrentService(service);
	service->tap(tservice);
	tservice->stopTapToFD();

	encoder[encoder_index].navigation_instance->stopService();

	close(encoder[encoder_index].encoder_fd);
	close(encoder[encoder_index].file_fd);
	encoder[encoder_index].encoder_fd = -1;
	encoder[encoder_index].file_fd = -1;

	encoder[encoder_index].state = EncoderContext::state_idle;
}

int eEncoder::getUsedEncoderCount()
{
	int count = 0;

	for(int encoder_index = 0; encoder_index < (int)encoder.size(); encoder_index++)
	{
		switch(encoder[encoder_index].state)
		{
			case(EncoderContext::state_running):
			case(EncoderContext::state_wait_pmt):
			{
				count++;
				break;
			}
		}
	}

	return(count);
}

void eEncoder::navigation_event(int encoder_index, int event)
{
	eDebug("[eEncoder] navigation event: %d %d", encoder_index, event);

	if((encoder_index < 0) || (encoder_index >= (int)encoder.size()))
		return;

	if(event == eDVBServicePMTHandler::eventTuned)
	{
		eDebug("[eEncoder] navigation event tuned: %d %d", encoder_index, event);

		if(encoder[encoder_index].state == EncoderContext::state_wait_pmt)
		{
			ePtr<iPlayableService> service;
			ePtr<iTapService> tservice;
			ePtr<iServiceInformation> info;
			std::vector<int> pids;

			encoder[encoder_index].navigation_instance->getCurrentService(service);
			service->info(info);

			int vpid = info->getInfo(iServiceInformation::sVideoPID);
			int apid = info->getInfo(iServiceInformation::sAudioPID);
			int pmtpid = info->getInfo(iServiceInformation::sPMTPID);

			if((vpid > 0) && (apid > 0) && (pmtpid > 0))
			{
				eDebug("[eEncoder] info complete: %d, %d, %d", vpid, apid, pmtpid);

				pids.push_back(pmtpid);
				pids.push_back(vpid);
				pids.push_back(apid);

				if(encoder[encoder_index].file_fd < 0)
				{
					service->tap(tservice);

					if(tservice == nullptr)
					{
						eWarning("[eEncoder] tap service failed");
						freeEncoder(encoder[encoder_index].encoder_fd);
						return;
					}

					tservice->startTapToFD(encoder[encoder_index].encoder_fd, pids);
				}
				else
				{
					if(encoder[encoder_index].stream_thread != nullptr)
					{
						eWarning("[eEncoder] datapump already running");
						return;
					}

					encoder[encoder_index].stream_thread = new eDVBRecordStreamThread(188, -1, true);

					encoder[encoder_index].stream_thread->setTargetFD(encoder[encoder_index].encoder_fd);
					encoder[encoder_index].stream_thread->start(encoder[encoder_index].file_fd);
				}

				if(ioctl(encoder[encoder_index].encoder_fd, IOCTL_BROADCOM_SET_PMTPID_MIPS, pmtpid) ||
						ioctl(encoder[encoder_index].encoder_fd, IOCTL_BROADCOM_SET_VPID_MIPS, vpid) ||
						ioctl(encoder[encoder_index].encoder_fd, IOCTL_BROADCOM_SET_APID_MIPS, apid))
				{
					eDebug("[eEncoder] set ioctl(mips) failed");

					if(ioctl(encoder[encoder_index].encoder_fd, IOCTL_BROADCOM_SET_PMTPID_ARM, pmtpid) ||
							ioctl(encoder[encoder_index].encoder_fd, IOCTL_BROADCOM_SET_VPID_ARM, vpid) ||
							ioctl(encoder[encoder_index].encoder_fd, IOCTL_BROADCOM_SET_APID_ARM, apid))
					{
						eWarning("[eEncoder] set ioctl(arm) failed too, giving up");
						freeEncoder(encoder[encoder_index].encoder_fd);
						return;
					}
				}

				encoder[encoder_index].state = EncoderContext::state_running;
				encoder[encoder_index].run();
			}
		}
	}
}

void eEncoder::navigation_event_0(int event)
{
	navigation_event(0, event);
}

void eEncoder::navigation_event_1(int event)
{
	navigation_event(1, event);
}

void eEncoder::EncoderContext::thread(void)
{
	hasStarted();

	if(ioctl(encoder_fd, IOCTL_BROADCOM_START_TRANSCODING, 0))
		eWarning("[eEncoder] thread encoder failed");
}

eAutoInitPtr<eEncoder> init_eEncoder(eAutoInitNumbers::service + 1, "Encoders");
