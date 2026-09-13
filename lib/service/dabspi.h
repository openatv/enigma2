#ifndef __lib_service_dabspi_h
#define __lib_service_dabspi_h

#include <cstddef>
#include <cstdint>
#include <ctime>
#include <string>
#include <vector>

/* A programme event decoded from the binary DAB SPI representation defined
 * by ETSI TS 102 371.  One PI object normally covers one service and one day,
 * but serviceIds remains a vector because a scope may name several bearers. */
struct eDABSPIEvent
{
	std::vector<uint32_t> serviceIds;
	uint16_t ensembleId = 0;
	time_t start = 0;
	int duration = 0;
	uint32_t shortId = 0;
	std::string title;
	std::string shortDescription;
	std::string longDescription;
};

class eDABSPIDecoder
{
public:
	bool decodeData(const uint8_t *data, size_t length, uint16_t fallbackEnsembleId,
		std::vector<eDABSPIEvent> &events, std::string &error);
	bool decodeFile(const std::string &path, uint16_t fallbackEnsembleId,
		std::vector<eDABSPIEvent> &events, std::string &error);
};

#endif
