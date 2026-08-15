#ifndef __DVB_ENCODER_H_
#define __DVB_ENCODER_H_

#include <vector>
#include <string>

#include <lib/nav/core.h>
#include <lib/dvb/streamserver.h>

class eEncoder
{
	private:

		DECLARE_REF(eEncoder);

		enum
		{
			IOCTL_BROADCOM_SET_VPID_MIPS = 1,
			IOCTL_BROADCOM_SET_VPID_ARM = 11,
			IOCTL_BROADCOM_SET_APID_MIPS = 2,
			IOCTL_BROADCOM_SET_APID_ARM = 12,
			IOCTL_BROADCOM_SET_PMTPID_MIPS = 3,
			IOCTL_BROADCOM_SET_PMTPID_ARM = 13,
			IOCTL_BROADCOM_START_TRANSCODING = 100,
			IOCTL_BROADCOM_STOP_TRANSCODING = 200,
		};

		class EncoderContext : public eThread
		{
			public:

				enum Backend
				{
					backend_proc,
					backend_bcm,
					backend_dreamsource,
					backend_amlogic_avc,
				};

				EncoderContext(eNavigation *navigation_instance_normal_in, eNavigation *navigation_instance_alternative_in)
				{
					file_fd = -1;
					encoder_fd = -1;
					output_fd = -1;
					backend = backend_proc;
					state = state_idle;
					navigation_instance = nullptr;
					navigation_instance_normal = navigation_instance_normal_in;
					navigation_instance_alternative = navigation_instance_alternative_in;
					stream_thread = nullptr;
					bitrate = 0;
					width = 0;
					height = 0;
					framerate = 0;
					interlaced = 0;
					aspectratio = 0;
					program_number = 1;
					input_mode = eStreamServer::INPUT_MODE_LIVE;
				}

				Backend backend;
				int encoder_fd;
				int file_fd;
				int output_fd;
				eDVBRecordStreamThread *stream_thread;
				int bitrate;
				int width;
				int height;
				int framerate;
				int interlaced;
				int aspectratio;
				int program_number;
				int input_mode;
				std::string vcodec;
				std::string acodec;

				enum
				{
					state_idle,
					state_wait_pmt,
					state_running,
					state_finishing,
					state_destroyed,
				} state;

				eNavigation *navigation_instance;
				eNavigation *navigation_instance_normal;
				eNavigation *navigation_instance_alternative;

				void thread(void);
				void threadDreamSource(void);
#ifdef DREAMNEXTGEN
				void threadAmlogicAvc(void);
#endif
		};

		std::vector<EncoderContext> encoder;
		bool bcm_encoder;
		bool dreamsource_encoder;
#ifdef DREAMNEXTGEN
		bool amlogic_avc_encoder;
#endif
		ePtr<eConnection> m_nav_event_connection_0;
		ePtr<eConnection> m_nav_event_connection_1;

		static eEncoder *instance;

		void navigation_event_0(int);
		void navigation_event_1(int);
		void navigation_event(int, int);

	public:

		eEncoder();
		~eEncoder();

		int allocateEncoder(const std::string &serviceref, int &buffersize, int bitrate, int width, int height, int framerate, int interlaced, int aspectratio,
				const std::string &vcodec = "", const std::string &acodec = "");
		int allocateHDMIEncoder(const std::string &serviceref, int &buffersize,
				int bitrate = 0, int width = 0, int height = 0, int framerate = 0, int interlaced = -1, int aspectratio = -1,
				const std::string &vcodec = "", const std::string &acodec = "");
		void freeEncoder(int encoderfd);
		int getUsedEncoderCount();

		static eEncoder *getInstance();
};

#endif /* __DVB_ENCODER_H_ */
