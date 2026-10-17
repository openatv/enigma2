#include <lib/dvb/warmstart.h>
#include <lib/dvb/frontend.h>
#include <lib/base/eenv.h>
#include <lib/base/eerror.h>

#include <algorithm>
#include <chrono>
#include <cstdint>
#include <cstdio>
#include <fstream>
#include <iomanip>
#include <map>
#include <sstream>
#include <sys/stat.h>
#include <unistd.h>

namespace
{
struct Profile
{
	std::string device, signature, service;
	int voltage = 0;
	int bootTime = 0;
};

std::map<eDVBFrontend *, Profile> prepared;
Profile lastTuned;
eDVBFrontend *poweredFrontend = nullptr;
bool closeDeferred = false;
std::chrono::steady_clock::time_point poweredAt;

std::string cachePath()
{
	return eEnv::resolve("${sysconfdir}/enigma2/dvb-warmstart");
}

bool readSettings(std::map<std::string, std::string> &settings)
{
	std::ifstream input(eEnv::resolve("${sysconfdir}/enigma2/settings"));
	std::string line;
	while (std::getline(input, line))
	{
		auto equal = line.find('=');
		if (equal != std::string::npos)
			settings[line.substr(0, equal)] = line.substr(equal + 1);
	}
	return input.eof() && !settings.empty();
}

std::string startService(std::map<std::string, std::string> &settings)
{
	if (!settings["config.servicelist.startupservice"].empty())
		return settings["config.servicelist.startupservice"];
	return settings[settings["config.servicelist.lastmode"] == "radio" ? "config.radio.lastservice" : "config.tv.lastservice"];
}

std::string nimIdentity(const std::string &sockets)
{
	std::istringstream input(sockets);
	std::string result, section, line;
	auto append = [&]() {
		// Multitype drivers report the currently selected mode as Type.
		// Keep the supported modes and physical identity, not that runtime state.
		if (section.find("\n\tMode ") != std::string::npos)
		{
			auto type = section.find("\n\tType:");
			if (type != std::string::npos)
				section.erase(type, section.find('\n', type + 1) - type);
		}
		result += section;
		section.clear();
	};
	while (std::getline(input, line))
	{
		if (line.compare(0, 11, "NIM Socket ") == 0)
			append();
		section += line + '\n';
	}
	append();
	return result;
}

bool signature(std::string &result)
{
	std::map<std::string, std::string> settings;
	if (!readSettings(settings))
		return false;
	// Include a cache generation and compilation stamp along with the saved
	// configuration to invalidate profiles when their interpretation changes.
	std::string data = "DVB pre-power 2 " __DATE__ " " __TIME__ "\n";
	for (const auto &entry : settings)
		if (entry.first.compare(0, 12, "config.Nims.") == 0 || entry.first.compare(0, 11, "config.sec.") == 0)
			data += entry.first + "=" + entry.second + "\n";
	for (const char *path : {"/proc/bus/nim_sockets", "/proc/stb/info/model", "/proc/version"})
	{
		std::ifstream input(eEnv::resolve(path));
		if (!input)
			return false;
		std::string identity((std::istreambuf_iterator<char>(input)), std::istreambuf_iterator<char>());
		data += std::string(path) == "/proc/bus/nim_sockets" ? nimIdentity(identity) : identity;
		data += '\n';
	}
	uint64_t hash = UINT64_C(14695981039346656037);
	for (unsigned char value : data)
	{
		hash ^= value;
		hash *= UINT64_C(1099511628211);
	}
	std::ostringstream output;
	output << std::hex << hash;
	result = output.str();
	return true;
}
}

bool eDVBWarmStart::load(std::string &device, int &voltage)
{
	const std::string path = cachePath();
	std::ifstream input(path);
	// Consume once. A failed startup must not repeatedly replay the same file.
	::unlink(path.c_str());
	if (!input || !::access((path + ".disabled").c_str(), F_OK))
		return false;
	std::string magic, currentSignature, trailing;
	Profile profile;
	std::map<std::string, std::string> settings;
	if (!(input >> magic >> std::quoted(profile.device) >> profile.voltage >> profile.bootTime >> profile.signature >> std::quoted(profile.service))
		|| (input >> trailing) || magic != "E2DVBPOWER1" || profile.bootTime <= 0 || profile.bootTime > 15000
		|| (profile.voltage != iDVBFrontend::voltage13 && profile.voltage != iDVBFrontend::voltage13_5)
		|| !signature(currentSignature) || profile.signature != currentSignature || !readSettings(settings)
		|| (!settings["config.usage.shutdownOK"].empty() && settings["config.usage.shutdownOK"] != "True") || settings["config.misc.firstrun"] != "False"
		|| (!settings["config.usage.boot_action"].empty() && settings["config.usage.boot_action"] != "normal")
		|| profile.service.empty() || profile.service != startService(settings))
	{
		eDebug("[DVBWarmStart] cache rejected; using normal SEC startup");
		return false;
	}
	device = profile.device;
	voltage = profile.voltage;
	return true;
}

void eDVBWarmStart::powered(eDVBFrontend &frontend)
{
	poweredFrontend = &frontend;
	closeDeferred = false;
	poweredAt = std::chrono::steady_clock::now();
	eDebug("[DVBWarmStart] pre-powered %s before Python startup", frontend.getDeviceName().c_str());
}

void eDVBWarmStart::voltageOff(eDVBFrontend &frontend)
{
	if (poweredFrontend == &frontend)
		poweredFrontend = nullptr;
}

int eDVBWarmStart::remaining(eDVBFrontend &frontend, int bootTime)
{
	if (poweredFrontend != &frontend)
		return 0;
	// The normal tune now owns the input and its complete SEC sequence.
	poweredFrontend = nullptr;
	auto elapsed = std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now() - poweredAt).count();
	int remaining = static_cast<int>(std::max<int64_t>(0, static_cast<int64_t>(bootTime) - elapsed));
	eDebug("[DVBWarmStart] frontend %d powered for %lld ms, remaining boot wait %d ms", frontend.getDVBID(), static_cast<long long>(elapsed), remaining);
	return remaining;
}

bool eDVBWarmStart::deferClose(eDVBFrontend &frontend)
{
	if (poweredFrontend != &frontend || closeDeferred)
		return false;
	// The initial idle timer may already be due when the main loop starts.
	// Allow the deferred first service to claim this input, once only.
	closeDeferred = true;
	return true;
}

void eDVBWarmStart::prepare(eDVBFrontend &frontend, eDVBFrontend &secFrontend, bool eligible, int voltage, int bootTime)
{
	prepared.erase(&frontend);
	if (!eligible || frontend.is_simulate() || bootTime <= 0 || bootTime > 15000)
		return;
	Profile profile;
	profile.device = secFrontend.getDeviceName();
	// USB/remote tuners need their own hotplug and power handling.
	if (profile.device.compare(0, 26, "/dev/dvb/adapter0/frontend") != 0 || !signature(profile.signature))
		return;
	profile.voltage = voltage;
	profile.bootTime = bootTime;
	prepared[&frontend] = profile;
}

void eDVBWarmStart::tuned(eDVBFrontend &frontend, const std::string &service)
{
	auto entry = prepared.find(&frontend);
	lastTuned = entry == prepared.end() || frontend.getCurrentType() != iDVBFrontend::feSatellite ? Profile() : entry->second;
	lastTuned.service = service;
}

void eDVBWarmStart::save(int exitCode)
{
	const std::string path = cachePath();
	std::string currentSignature;
	std::map<std::string, std::string> settings;
	if ((exitCode != 1 && exitCode != 2 && exitCode != 3 && exitCode != 45) || lastTuned.device.empty()
		|| !signature(currentSignature) || lastTuned.signature != currentSignature || !readSettings(settings)
		|| (!settings["config.usage.shutdownOK"].empty() && settings["config.usage.shutdownOK"] != "True") || lastTuned.service != startService(settings))
	{
		::unlink(path.c_str());
		return;
	}
	const std::string temporary = path + ".tmp";
	std::ofstream output(temporary, std::ios::trunc);
	output << "E2DVBPOWER1\n" << std::quoted(lastTuned.device) << '\n' << lastTuned.voltage << '\n'
		<< lastTuned.bootTime << '\n' << lastTuned.signature << '\n' << std::quoted(lastTuned.service) << '\n';
	output.close();
	if (!output.fail() && !::chmod(temporary.c_str(), 0600) && !::rename(temporary.c_str(), path.c_str()))
		eDebug("[DVBWarmStart] saved Unicable power profile for %s", lastTuned.device.c_str());
	else
		::unlink(temporary.c_str());
}
