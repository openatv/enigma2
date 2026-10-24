#ifndef __lib_service_dabsdrcontrol_h
#define __lib_service_dabsdrcontrol_h

#include <cstdint>
#include <cstdio>
#include <string>
#include <utility>

/* SELECT stops the old programme; READY is the output-drain barrier.
 * START then allows the new programme to produce audio and metadata.
 * Generations make delayed replies harmless during rapid consecutive zaps. */
class eDABSDRControl
{
public:
	void select(uint32_t serviceId, const std::string &cachePrefix, uint64_t now)
	{
		++m_generation;
		char command[80];
		snprintf(command, sizeof(command), "SELECT %llu %x ",
			static_cast<unsigned long long>(m_generation), serviceId);
		m_command = command + cachePrefix + "\n";
		m_phase = AwaitingReady;
		m_deadline = now + 2000;
	}

	bool ready(const std::string &generation, uint64_t now)
	{
		if (m_phase != AwaitingReady || generation != std::to_string(m_generation))
			return false;
		m_phase = AwaitingStart;
		m_command = "START " + generation + "\n";
		m_deadline = now + 2000;
		return true;
	}

	bool started(const std::string &generation, uint64_t now)
	{
		if (m_phase != AwaitingStart || generation != std::to_string(m_generation))
			return false;
		m_phase = Playing;
		m_deadline = now + 4000;
		return true;
	}

	void audioReceived() { if (m_phase == Playing) m_deadline = 0; }
	void fail() { m_phase = Failed; m_command.clear(); m_deadline = 0; }
	bool expired(uint64_t now)
	{
		if (!m_deadline || now < m_deadline)
			return false;
		fail();
		return true;
	}
	bool muted() const { return m_phase != Idle && m_phase != Playing; }
	bool failed() const { return m_phase == Failed; }
	uint64_t generation() const { return m_generation; }
	std::string takeCommand() { return std::exchange(m_command, std::string()); }

private:
	enum Phase { Idle, AwaitingReady, AwaitingStart, Playing, Failed };
	Phase m_phase = Idle;
	uint64_t m_generation = 0;
	uint64_t m_deadline = 0;
	std::string m_command;
};

#endif
