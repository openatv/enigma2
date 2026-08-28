/*
    DABlin PAD/MOT decoder integration for Enigma2.
    Character tables and CRC design adapted from DABlin,
    Copyright (C) 2015-2022 Stefan Pöschel, GPLv3+.
 */
#ifndef __lib_service_dabpadtools_h
#define __lib_service_dabpadtools_h

#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>

namespace DABlinPAD
{

class StringTools
{
	static size_t UTF8CharsLen(const std::string &s, size_t chars);
public:
	static std::string UTF8Substr(const std::string &s, size_t pos, size_t count);
};

class CharsetTools
{
	static const char *no_char;
	static const char *ebu_values_0x00_to_0x1F[];
	static const char *ebu_values_0x7B_to_0xFF[];
	static std::string ConvertCharEBUToUTF8(uint8_t value);
public:
	static std::string ConvertTextToUTF8(const uint8_t *data, size_t len, int charset,
		bool mot, std::string *charset_name);
};

class CalcCRC
{
	bool initial_invert;
	bool final_invert;
	uint16_t gen_polynom;
	uint16_t crc_lut[256];
	void FillLUT();
public:
	CalcCRC(bool initial_invert, bool final_invert, uint16_t gen_polynom);
	uint16_t Calc(const uint8_t *data, size_t len);
	void Initialize(uint16_t &crc);
	void ProcessByte(uint16_t &crc, uint8_t data);
	void Finalize(uint16_t &crc);

	static CalcCRC CalcCRC_CRC16_CCITT;
	static CalcCRC CalcCRC_CRC16_IBM;
	static CalcCRC CalcCRC_FIRE_CODE;
	static size_t CRCLen;
};

}

#endif
