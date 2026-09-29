/*
Copyright (c) 2024-2025 OpenATV, jbleyel

This code may be used commercially. Attribution must be given to the original author.
Licensed under GPLv2.
*/

#ifndef __lib_base_profile_h
#define __lib_base_profile_h

#include <map>
#include <string>
#include <fstream>
#include <algorithm>
#include <chrono>
#include <cstring>
#include <string_view>
#include <sys/socket.h>
#include <sys/un.h>

/* ORM started by enigma2.sh, learns here how far the start came. */
#define ORM_SOCKET "/var/run/enigma2-orm.socket"
/* Like STABLE_SECONDS of ORM: it takes over a crash until this long after ready. */
#define ORM_STABLE_SECONDS 60

class eProfile
{
public:
	eProfile() : m_profileStart(clock_::now())
	{
		m_ormFd = socket(AF_UNIX, SOCK_DGRAM | SOCK_CLOEXEC, 0);
		m_ormAddress.sun_family = AF_UNIX;
		strncpy(m_ormAddress.sun_path, ORM_SOCKET, sizeof(m_ormAddress.sun_path) - 1);

		std::string fileName = "/var/local/profile";
		std::ifstream f(fileName.c_str());

		if (f.good())
		{
			std::string line;
			char checkPoint[200];
			float value;
			while (f.good())
			{
				std::getline(f, line);
				if (std::sscanf(line.c_str(), "%f\t%[^\n]", &value, checkPoint) == 2)
				{
					m_profileData[std::string(checkPoint)] = value;
					m_totalTime = value;
				}
			}
			f.close();
		}

		m_handle = fopen(fileName.c_str(), "w");
	}

	static eProfile &getInstance()
	{
		static eProfile m_instance;
		return m_instance;
	}

	/* Returns false when ORM does not listen. */
	static bool notify(std::string_view message)
	{
		if (m_ormFd < 0)
			return false;
		if (sendto(m_ormFd, message.data(), message.size(), MSG_DONTWAIT | MSG_NOSIGNAL, (const struct sockaddr *)&m_ormAddress, sizeof(m_ormAddress)) < 0)
			return false;
		if (message == "ready")
			m_ormReady = std::chrono::steady_clock::now();
		return true;
	}

	/* A crash before ready or shortly after it is a failed start, ORM shows it instead of the blue screen. */
	static bool ormTakesOver()
	{
		return m_ormReady == std::chrono::steady_clock::time_point() ||
			std::chrono::steady_clock::now() - m_ormReady < std::chrono::seconds(ORM_STABLE_SECONDS);
	}

	void write(const char *checkPoint)
	{
		notify(std::string("step ") + checkPoint);
		if (m_handle)
		{
			double nowDiff = std::chrono::duration<double, std::milli>(clock_::now() - m_profileStart).count();
			std::map<std::string, float>::iterator it = m_profileData.find(std::string(checkPoint));
			float nowDiffFloat = (float)nowDiff / 1000;
			fprintf(m_handle, "%f\t%s\n", nowDiffFloat, checkPoint);
			if (m_noproc)
				return;
			if (it != m_profileData.end())
			{

				int percentage = 50;
				float timeStamp = it->second;
				if (m_totalTime > 0)
				{
					percentage = (timeStamp * 50 / m_totalTime) + 50;
				}
				FILE *f;

#ifdef PROFILE1 // "classm", "axodin", "axodinc", "starsatlx", "evo", "genius", "galaxym6"
				f = fopen("/dev/dbox/oled0", "w");
#elif PROFILE2 // 'gb800solo', 'gb800se', 'gb800seplus', 'gbultrase'
				f = fopen("/dev/mcu", "w");
#elif PROFILE3 // "osmini", "spycatmini", "osminiplus", "spycatminiplus"
				f = fopen("/proc/progress", "w");
#elif PROFILE4 // "xpeedlx3", "sezammarvel", "atemionemesis"
				f = fopen("/proc/vfd", "w");
#else
				f = fopen("/proc/progress", "w");
#endif

				if (f)
				{

#ifdef PROFILE1 // "classm", "axodin", "axodinc", "starsatlx", "evo", "genius", "galaxym6"
					fprintf(f, "%d", percentage);
#elif PROFILE2 // 'gb800solo', 'gb800se', 'gb800seplus', 'gbultrase'
					fprintf(f, "%d  \n", percentage);
#elif PROFILE3 // "osmini", "spycatmini", "osminiplus", "spycatminiplus"
					fprintf(f, "%d", percentage);
#elif PROFILE4 // "xpeedlx3", "sezammarvel", "atemionemesis"
					fprintf(f, "Loading %d%% ", percentage);
#else
					fprintf(f, "%d \n", percentage);
#endif
					fclose(f);
				}
				else
				{
					m_noproc = true;
				}
			}
		}
	}

	void close()
	{
		if (m_handle)
		{
			fclose(m_handle);
			m_handle = nullptr;
		}
	}

private:
	typedef std::chrono::high_resolution_clock clock_;
	std::chrono::time_point<clock_> m_profileStart;
	std::map<std::string, float> m_profileData;
	float m_totalTime = 1;
	bool m_noproc = false;
	FILE *m_handle;
	static inline int m_ormFd = -1;
	static inline std::chrono::steady_clock::time_point m_ormReady;
	static inline struct sockaddr_un m_ormAddress = {};
};

#endif
