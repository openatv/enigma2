/*
Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License

Copyright (c) 2024-2025 OpenATV, jbleyel

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:
1. Non-Commercial Use: You may not use the Software or any derivative works
   for commercial purposes without obtaining explicit permission from the
   copyright holder.
2. Share Alike: If you distribute or publicly perform the Software or any
   derivative works, you must do so under the same license terms, and you
   must make the source code of any derivative works available to the
   public.
3. Attribution: You must give appropriate credit to the original author(s)
   of the Software by including a prominent notice in your derivative works.
THE SOFTWARE IS PROVIDED "AS IS," WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE, AND NONINFRINGEMENT. IN NO EVENT SHALL
THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES, OR
OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT, OR OTHERWISE,
ARISING FROM, OUT OF, OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
OTHER DEALINGS IN THE SOFTWARE.

For more details about the CC BY-NC-SA 4.0 License, please visit:
https://creativecommons.org/licenses/by-nc-sa/4.0/
*/

#ifndef __lib_base_profile_h
#define __lib_base_profile_h

#include <map>
#include <string>
#include <fstream>
#include <algorithm>
#include <chrono>

class eProfile
{
public:
	eProfile() : m_profileStart(clock_::now())
	{
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

	void write(const char *checkPoint)
	{
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
};

#endif
