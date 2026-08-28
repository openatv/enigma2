#include <lib/service/dabtsadapter.h>

#include <algorithm>
#include <cstring>

namespace
{
constexpr size_t ETI_NI_SIZE = 6144;
constexpr size_t E1_FRAME_SIZE = 32;
constexpr size_t E1_FRAME_BITS = E1_FRAME_SIZE * 8;
constexpr size_t FRAMES_PER_BLOCK = 8;
constexpr size_t BLOCKS_PER_SUPERFRAME = 8;
constexpr size_t SUPERFRAMES_PER_MULTIFRAME = 3;
constexpr size_t FRAMES_PER_MULTIFRAME = FRAMES_PER_BLOCK * BLOCKS_PER_SUPERFRAME * SUPERFRAMES_PER_MULTIFRAME;
constexpr size_t DEINTERLEAVE_ROWS = 8;
constexpr size_t DEINTERLEAVE_COLUMNS = 240;
constexpr uint8_t E1_SYNC = 0x1b;
constexpr uint8_t E1_SYNC_MASK = 0x7f;
}

eDABTSAdapter::eDABTSAdapter(eDABTransport transport, const FrameCallback &frameCallback)
	: m_transport(transport), m_frame_callback(frameCallback), m_tsni_active(false),
	  m_na_e1_synchronized(false), m_na_multiframe_aligned(false), m_na_inverted(false),
	  m_na_bit_position(0), m_na_even(true)
{
	m_tsni_frame.reserve(ETI_NI_SIZE);
	m_na_input.reserve(ETI_NI_SIZE * 2);
}

void eDABTSAdapter::reset()
{
	m_tsni_frame.clear();
	m_tsni_active = false;
	m_na_input.clear();
	m_na_e1_synchronized = false;
	m_na_multiframe_aligned = false;
	m_na_inverted = false;
	m_na_bit_position = 0;
	m_na_even = true;
}

void eDABTSAdapter::feedPayload(const uint8_t *payload, size_t length, bool unitStart)
{
	if (!payload || !length)
		return;
	if (m_transport == DAB_TRANSPORT_TSNI)
		feedTSNI(payload, length, unitStart);
	else if (m_transport == DAB_TRANSPORT_TSNA12)
	{
		if (length > 12)
			feedTSNA(payload + 12, length - 12);
	}
	else if (m_transport == DAB_TRANSPORT_TSNA0)
		feedTSNA(payload, length);
}

void eDABTSAdapter::feedTSNI(const uint8_t *payload, size_t length, bool unitStart)
{
	if (unitStart)
	{
		finishTSNI();
		/* ETI-NA(V.11) uses one framing byte at every PUSI. The following
		 * byte is FCT, whose parity selects the missing ETI-NI sync word. */
		if (length < 2)
			return;
		++payload;
		--length;
		m_tsni_frame.clear();
		m_tsni_frame.push_back(0xff);
		if (payload[0] & 1)
		{
			m_tsni_frame.push_back(0xf8);
			m_tsni_frame.push_back(0xc5);
			m_tsni_frame.push_back(0x49);
		}
		else
		{
			m_tsni_frame.push_back(0x07);
			m_tsni_frame.push_back(0x3a);
			m_tsni_frame.push_back(0xb6);
		}
		m_tsni_active = true;
	}
	if (!m_tsni_active || length > ETI_NI_SIZE - m_tsni_frame.size())
	{
		if (m_tsni_active)
		{
			m_tsni_frame.clear();
			m_tsni_active = false;
		}
		return;
	}
	m_tsni_frame.insert(m_tsni_frame.end(), payload, payload + length);
}

void eDABTSAdapter::finishTSNI()
{
	if (!m_tsni_active)
		return;
	if (m_tsni_frame.size() >= 8 && m_tsni_frame.size() <= ETI_NI_SIZE)
	{
		m_tsni_frame.resize(ETI_NI_SIZE, 0x55);
		if (m_frame_callback)
			m_frame_callback(m_tsni_frame.data(), m_tsni_frame.size());
	}
	m_tsni_frame.clear();
	m_tsni_active = false;
}

void eDABTSAdapter::feedTSNA(const uint8_t *payload, size_t length)
{
	if (!length)
		return;
	m_na_input.insert(m_na_input.end(), payload, payload + length);
	processTSNA();
	/* A clean stream needs less than two ETI multiframes buffered. Bound a
	 * permanently unsynchronisable input without growing the worker. */
	if (m_na_input.size() > ETI_NI_SIZE * 8)
	{
		m_na_input.erase(m_na_input.begin(), m_na_input.end() - ETI_NI_SIZE * 2);
		m_na_e1_synchronized = false;
		m_na_multiframe_aligned = false;
		m_na_bit_position = 0;
	}
}

uint8_t eDABTSAdapter::getAlignedByte(size_t bitPosition) const
{
	const size_t bytePosition = bitPosition >> 3;
	const unsigned shift = bitPosition & 7;
	if (!shift)
		return m_na_input[bytePosition];
	return static_cast<uint8_t>((m_na_input[bytePosition] << shift) |
		(m_na_input[bytePosition + 1] >> (8 - shift)));
}

bool eDABTSAdapter::findE1Sync(size_t startBit, size_t &bitPosition, bool &inverted) const
{
	const size_t spacing = E1_FRAME_SIZE * 2 * 8;
	const size_t samples = 8;
	const size_t requiredBits = (samples - 1) * spacing + 8;
	const size_t availableBits = m_na_input.size() * 8;
	if (availableBits < requiredBits)
		return false;
	// Skip candidates the caller already rejected, otherwise they are found again.
	for (size_t start = startBit; start + requiredBits <= availableBits; ++start)
	{
		const uint8_t first = getAlignedByte(start) & E1_SYNC_MASK;
		if (first != E1_SYNC && first != (E1_SYNC ^ E1_SYNC_MASK))
			continue;
		const bool candidateInverted = first != E1_SYNC;
		bool match = true;
		for (size_t sample = 1; sample < samples; ++sample)
		{
			uint8_t value = getAlignedByte(start + sample * spacing) & E1_SYNC_MASK;
			if (candidateInverted)
				value ^= E1_SYNC_MASK;
			if (value != E1_SYNC)
			{
				match = false;
				break;
			}
		}
		if (match)
		{
			bitPosition = start;
			inverted = candidateInverted;
			return true;
		}
	}
	return false;
}

bool eDABTSAdapter::extractE1Frames(size_t bitPosition, size_t count, std::vector<uint8_t> &frames) const
{
	const size_t requiredBits = count * E1_FRAME_BITS;
	if (bitPosition + requiredBits > m_na_input.size() * 8)
		return false;
	frames.resize(count * E1_FRAME_SIZE);
	for (size_t byte = 0; byte < frames.size(); ++byte)
	{
		uint8_t value = getAlignedByte(bitPosition + byte * 8);
		frames[byte] = m_na_inverted ? static_cast<uint8_t>(value ^ 0xff) : value;
	}
	return true;
}

int eDABTSAdapter::findBlockPhase(const std::vector<uint8_t> &frames) const
{
	for (int phase = 0; phase < static_cast<int>(FRAMES_PER_BLOCK); ++phase)
	{
		int lastBlock = -1;
		int lastSuperframe = -1;
		int block = 0;
		for (; block < static_cast<int>(BLOCKS_PER_SUPERFRAME * 2); ++block)
		{
			const size_t frame = static_cast<size_t>(phase) + static_cast<size_t>(block) * FRAMES_PER_BLOCK;
			if ((frame + 1) * E1_FRAME_SIZE > frames.size())
				break;
			const uint8_t management = frames[frame * E1_FRAME_SIZE + 1];
			const int blockNumber = (management >> 5) & 7;
			const int superframeNumber = (management >> 3) & 3;
			if (!block)
			{
				lastBlock = blockNumber;
				lastSuperframe = superframeNumber;
				continue;
			}
			const bool nextBlock = superframeNumber == lastSuperframe && blockNumber == ((lastBlock + 1) & 7);
			const bool nextSuperframe = blockNumber == 0 &&
				(superframeNumber == ((lastSuperframe + 1) & 3) || (lastSuperframe == 2 && superframeNumber == 0));
			if (!nextBlock && !nextSuperframe)
				break;
			lastBlock = blockNumber;
			lastSuperframe = superframeNumber;
		}
		if (block == static_cast<int>(BLOCKS_PER_SUPERFRAME * 2))
			return phase;
	}
	return -1;
}

int eDABTSAdapter::findMultiframeBlock(const std::vector<uint8_t> &frames, int phase) const
{
	for (int block = 0; block < static_cast<int>(BLOCKS_PER_SUPERFRAME * SUPERFRAMES_PER_MULTIFRAME); ++block)
	{
		const size_t frame = static_cast<size_t>(phase) + static_cast<size_t>(block) * FRAMES_PER_BLOCK;
		if ((frame + 1) * E1_FRAME_SIZE > frames.size())
			break;
		const uint8_t management = frames[frame * E1_FRAME_SIZE + 1];
		if (((management >> 5) & 7) == 0 && ((management >> 3) & 3) == 0)
			return block;
	}
	return -1;
}

bool eDABTSAdapter::validMultiframe(const std::vector<uint8_t> &frames) const
{
	if (frames.size() != FRAMES_PER_MULTIFRAME * E1_FRAME_SIZE)
		return false;
	for (size_t block = 0; block < BLOCKS_PER_SUPERFRAME * SUPERFRAMES_PER_MULTIFRAME; ++block)
	{
		const uint8_t management = frames[block * FRAMES_PER_BLOCK * E1_FRAME_SIZE + 1];
		if (((management >> 5) & 7) != static_cast<int>(block % BLOCKS_PER_SUPERFRAME) ||
			((management >> 3) & 3) != static_cast<int>(block / BLOCKS_PER_SUPERFRAME))
			return false;
	}
	return true;
}

bool eDABTSAdapter::buildETINI(const std::vector<uint8_t> &frames, std::vector<uint8_t> &eti)
{
	if (!validMultiframe(frames))
		return false;
	std::vector<uint8_t> deinterleaved(DEINTERLEAVE_ROWS * DEINTERLEAVE_COLUMNS * SUPERFRAMES_PER_MULTIFRAME);
	for (size_t superframe = 0; superframe < SUPERFRAMES_PER_MULTIFRAME; ++superframe)
	{
		const uint8_t *input = frames.data() + superframe * E1_FRAME_SIZE * FRAMES_PER_BLOCK * BLOCKS_PER_SUPERFRAME;
		uint8_t *output = deinterleaved.data() + superframe * DEINTERLEAVE_ROWS * DEINTERLEAVE_COLUMNS;
		size_t inputPosition = 0;
		for (size_t column = 0; column < DEINTERLEAVE_COLUMNS; ++column)
		{
			for (size_t row = 0; row < DEINTERLEAVE_ROWS; ++row)
			{
				if (!(inputPosition % 16))
					++inputPosition;
				if (inputPosition >= E1_FRAME_SIZE * FRAMES_PER_BLOCK * BLOCKS_PER_SUPERFRAME)
					return false;
				output[column + row * DEINTERLEAVE_COLUMNS] = input[inputPosition++];
			}
		}
	}

	const uint8_t management = frames[E1_FRAME_SIZE * FRAMES_PER_BLOCK + 1];
	const bool longProtection = management & 0x02;
	const size_t rowPayload = longProtection ? 226 : 235;
	eti.assign(ETI_NI_SIZE, 0x55);
	eti[0] = 0xff;
	eti[1] = m_na_even ? 0x07 : 0xf8;
	eti[2] = m_na_even ? 0x3a : 0xc5;
	eti[3] = m_na_even ? 0xb6 : 0x49;
	m_na_even = !m_na_even;
	size_t outputPosition = 4;
	for (size_t row = 0; row < DEINTERLEAVE_ROWS * SUPERFRAMES_PER_MULTIFRAME; ++row)
	{
		const uint8_t *source = deinterleaved.data() + row * DEINTERLEAVE_COLUMNS;
		if ((row % DEINTERLEAVE_ROWS) < 2)
		{
			size_t readPosition = 0;
			while (readPosition < rowPayload)
			{
				size_t copy = 29;
				if (readPosition + copy > rowPayload)
					copy = rowPayload > readPosition + 1 ? rowPayload - readPosition - 1 : 0;
				++readPosition; // Skip the M-basis management byte.
				if (outputPosition + copy > eti.size() || readPosition + copy > DEINTERLEAVE_COLUMNS)
					return false;
				memcpy(eti.data() + outputPosition, source + readPosition, copy);
				outputPosition += copy;
				readPosition += copy;
			}
		}
		else
		{
			if (outputPosition + rowPayload > eti.size())
				return false;
			memcpy(eti.data() + outputPosition, source, rowPayload);
			outputPosition += rowPayload;
		}
	}
	return true;
}

void eDABTSAdapter::compactNAInput()
{
	const size_t bytes = m_na_bit_position >> 3;
	if (bytes && (bytes >= 4096 || bytes == m_na_input.size()))
	{
		m_na_input.erase(m_na_input.begin(), m_na_input.begin() + bytes);
		m_na_bit_position &= 7;
	}
}

void eDABTSAdapter::processTSNA()
{
	for (;;)
	{
		if (!m_na_e1_synchronized)
		{
			size_t syncPosition = 0;
			bool inverted = false;
			if (!findE1Sync(m_na_bit_position, syncPosition, inverted))
				return;
			m_na_bit_position = syncPosition;
			m_na_inverted = inverted;
			m_na_e1_synchronized = true;
			m_na_multiframe_aligned = false;
		}

		if (!m_na_multiframe_aligned)
		{
			std::vector<uint8_t> searchFrames;
			if (!extractE1Frames(m_na_bit_position, FRAMES_PER_MULTIFRAME + FRAMES_PER_BLOCK, searchFrames))
				return;
			const int phase = findBlockPhase(searchFrames);
			const int block = phase >= 0 ? findMultiframeBlock(searchFrames, phase) : -1;
			if (phase < 0 || block < 0)
			{
				++m_na_bit_position;
				m_na_e1_synchronized = false;
				compactNAInput();
				continue;
			}
			m_na_bit_position += (static_cast<size_t>(phase) + static_cast<size_t>(block) * FRAMES_PER_BLOCK) * E1_FRAME_BITS;
			m_na_multiframe_aligned = true;
		}

		std::vector<uint8_t> frames;
		if (!extractE1Frames(m_na_bit_position, FRAMES_PER_MULTIFRAME, frames))
			return;
		std::vector<uint8_t> eti;
		if (!buildETINI(frames, eti))
		{
			++m_na_bit_position;
			m_na_e1_synchronized = false;
			m_na_multiframe_aligned = false;
			compactNAInput();
			continue;
		}
		if (m_frame_callback)
			m_frame_callback(eti.data(), eti.size());
		m_na_bit_position += FRAMES_PER_MULTIFRAME * E1_FRAME_BITS;
		compactNAInput();
	}
}
