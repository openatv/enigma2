#ifndef __lib_service_dabtsadapter_h
#define __lib_service_dabtsadapter_h

#include <cstddef>
#include <cstdint>
#include <functional>
#include <vector>

enum eDABTransport
{
	DAB_TRANSPORT_MPE_EDI,
	DAB_TRANSPORT_TSNI,
	DAB_TRANSPORT_TSNA12,
	DAB_TRANSPORT_TSNA0
};

/*
 * Converts the non-EDI satellite contribution formats to aligned 6144-byte
 * ETI-NI frames. TS parsing and PID filtering remain in eDABWorker.
 */
class eDABTSAdapter
{
public:
	typedef std::function<void(const uint8_t *, size_t)> FrameCallback;

	eDABTSAdapter(eDABTransport transport, const FrameCallback &frameCallback);

	void feedPayload(const uint8_t *payload, size_t length, bool unitStart);
	void reset();

private:
	void feedTSNI(const uint8_t *payload, size_t length, bool unitStart);
	void finishTSNI();
	void feedTSNA(const uint8_t *payload, size_t length);
	void processTSNA();
	bool findE1Sync(size_t &bitPosition, bool &inverted) const;
	uint8_t getAlignedByte(size_t bitPosition) const;
	bool extractE1Frames(size_t bitPosition, size_t count, std::vector<uint8_t> &frames) const;
	int findBlockPhase(const std::vector<uint8_t> &frames) const;
	int findMultiframeBlock(const std::vector<uint8_t> &frames, int phase) const;
	bool validMultiframe(const std::vector<uint8_t> &frames) const;
	bool buildETINI(const std::vector<uint8_t> &frames, std::vector<uint8_t> &eti);
	void compactNAInput();

	eDABTransport m_transport;
	FrameCallback m_frame_callback;
	std::vector<uint8_t> m_tsni_frame;
	bool m_tsni_active;
	std::vector<uint8_t> m_na_input;
	bool m_na_e1_synchronized;
	bool m_na_multiframe_aligned;
	bool m_na_inverted;
	size_t m_na_bit_position;
	bool m_na_even;
};

#endif
