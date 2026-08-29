/*
    DABlin PAD/MOT decoder integration for Enigma2.
    Character tables and CRC design adapted from DABlin,
    Copyright (C) 2015-2022 Stefan Pöschel, GPLv3+.
 */

#include <lib/service/dabpadtools.h>

#include <algorithm>


namespace
{
std::string CodepointToUTF8(uint32_t value)
{
	if (value <= 0x7f)
		return std::string(1, static_cast<char>(value));
	if (value <= 0x7ff)
	{
		char text[2] = { static_cast<char>(0xc0 | (value >> 6)),
			static_cast<char>(0x80 | (value & 0x3f)) };
		return std::string(text, sizeof(text));
	}
	if (value >= 0xd800 && value <= 0xdfff)
		return std::string();
	if (value <= 0xffff)
	{
		char text[3] = { static_cast<char>(0xe0 | (value >> 12)),
			static_cast<char>(0x80 | ((value >> 6) & 0x3f)),
			static_cast<char>(0x80 | (value & 0x3f)) };
		return std::string(text, sizeof(text));
	}
	if (value <= 0x10ffff)
	{
		char text[4] = { static_cast<char>(0xf0 | (value >> 18)),
			static_cast<char>(0x80 | ((value >> 12) & 0x3f)),
			static_cast<char>(0x80 | ((value >> 6) & 0x3f)),
			static_cast<char>(0x80 | (value & 0x3f)) };
		return std::string(text, sizeof(text));
	}
	return std::string();
}
}

namespace DABlinPAD
{

size_t StringTools::UTF8CharsLen(const std::string &s, size_t chars)
{
	size_t result;
	for (result = 0; result < s.size(); ++result)
	{
		if ((s[result] & 0xc0) != 0x80)
		{
			if (!chars)
				break;
			--chars;
		}
	}
	return result;
}

std::string StringTools::UTF8Substr(const std::string &s, size_t pos, size_t count)
{
	std::string result = s;
	result.erase(0, UTF8CharsLen(result, pos));
	result.erase(UTF8CharsLen(result, count));
	return result;
}

const char* CharsetTools::no_char = "";
const char* CharsetTools::ebu_values_0x00_to_0x1F[] = {
		no_char , "\u0118", "\u012E", "\u0172", "\u0102", "\u0116", "\u010E", "\u0218", "\u021A", "\u010A", no_char , no_char , "\u0120", "\u0139" , "\u017B", "\u0143",
		"\u0105", "\u0119", "\u012F", "\u0173", "\u0103", "\u0117", "\u010F", "\u0219", "\u021B", "\u010B", "\u0147", "\u011A", "\u0121", "\u013A", "\u017C", no_char
};
const char* CharsetTools::ebu_values_0x7B_to_0xFF[] = {
		/* starting some chars earlier than 0x80 -----> */                                                            "\u00AB", "\u016F", "\u00BB", "\u013D", "\u0126",
		"\u00E1", "\u00E0", "\u00E9", "\u00E8", "\u00ED", "\u00EC", "\u00F3", "\u00F2", "\u00FA", "\u00F9", "\u00D1", "\u00C7", "\u015E", "\u00DF", "\u00A1", "\u0178",
		"\u00E2", "\u00E4", "\u00EA", "\u00EB", "\u00EE", "\u00EF", "\u00F4", "\u00F6", "\u00FB", "\u00FC", "\u00F1", "\u00E7", "\u015F", "\u011F", "\u0131", "\u00FF",
		"\u0136", "\u0145", "\u00A9", "\u0122", "\u011E", "\u011B", "\u0148", "\u0151", "\u0150", "\u20AC", "\u00A3", "\u0024", "\u0100", "\u0112", "\u012A", "\u016A",
		"\u0137", "\u0146", "\u013B", "\u0123", "\u013C", "\u0130", "\u0144", "\u0171", "\u0170", "\u00BF", "\u013E", "\u00B0", "\u0101", "\u0113", "\u012B", "\u016B",
		"\u00C1", "\u00C0", "\u00C9", "\u00C8", "\u00CD", "\u00CC", "\u00D3", "\u00D2", "\u00DA", "\u00D9", "\u0158", "\u010C", "\u0160", "\u017D", "\u00D0", "\u013F",
		"\u00C2", "\u00C4", "\u00CA", "\u00CB", "\u00CE", "\u00CF", "\u00D4", "\u00D6", "\u00DB", "\u00DC", "\u0159", "\u010D", "\u0161", "\u017E", "\u0111", "\u0140",
		"\u00C3", "\u00C5", "\u00C6", "\u0152", "\u0177", "\u00DD", "\u00D5", "\u00D8", "\u00DE", "\u014A", "\u0154", "\u0106", "\u015A", "\u0179", "\u0164", "\u00F0",
		"\u00E3", "\u00E5", "\u00E6", "\u0153", "\u0175", "\u00FD", "\u00F5", "\u00F8", "\u00FE", "\u014B", "\u0155", "\u0107", "\u015B", "\u017A", "\u0165", "\u0127"
};

std::string CharsetTools::ConvertCharEBUToUTF8(const uint8_t value) {
	// convert via LUT
	if(value <= 0x1F)
		return ebu_values_0x00_to_0x1F[value];
	if(value >= 0x7B)
		return ebu_values_0x7B_to_0xFF[value - 0x7B];

	// convert by hand (avoiding a LUT with mostly 1:1 mapping)
	switch(value) {
	case 0x24:
		return "\u0142";
	case 0x5C:
		return "\u016E";
	case 0x5E:
		return "\u0141";
	case 0x60:
		return "\u0104";
	}

	// leave untouched
	return std::string(1, static_cast<char>(value));
}


std::string CharsetTools::ConvertTextToUTF8(const uint8_t *data, size_t len, int charset,
	bool mot, std::string *charset_name)
{
	/* UCS-2 is two bytes per character, so the control characters have to be
	 * dropped as code points. Removing single bytes would shift everything
	 * that follows. */
	if (charset == 6 && !mot)
	{
		if (charset_name)
			*charset_name = "UCS-2BE";
		std::string result;
		for (size_t i = 0; i + 1 < len; i += 2)
		{
			const unsigned value = (static_cast<unsigned>(data[i]) << 8) | data[i + 1];
			if (value == 0x00 || value == 0x0a || value == 0x0b || value == 0x1f)
				continue;
			result += CodepointToUTF8(value);
		}
		return result;
	}
	std::vector<uint8_t> cleaned;
	for (size_t i = 0; i < len; ++i)
	{
		switch (data[i])
		{
		case 0x00:
		case 0x0a:
		case 0x0b:
		case 0x1f:
			break;
		default:
			cleaned.push_back(data[i]);
		}
	}
	if (charset == 0)
	{
		if (charset_name)
			*charset_name = "EBU Latin based";
		std::string result;
		for (std::vector<uint8_t>::const_iterator it = cleaned.begin(); it != cleaned.end(); ++it)
			result += ConvertCharEBUToUTF8(*it);
		return result;
	}
	if (charset == 4 && mot)
	{
		if (charset_name)
			*charset_name = "ISO-8859-1";
		std::string result;
		for (std::vector<uint8_t>::const_iterator it = cleaned.begin(); it != cleaned.end(); ++it)
			result += CodepointToUTF8(*it);
		return result;
	}
	if (charset == 15)
	{
		if (charset_name)
			*charset_name = "UTF-8";
		return cleaned.empty() ? std::string() :
			std::string(reinterpret_cast<const char *>(&cleaned[0]), cleaned.size());
	}
	return std::string();
}

CalcCRC CalcCRC::CalcCRC_CRC16_CCITT(true, true, 0x1021);
CalcCRC CalcCRC::CalcCRC_CRC16_IBM(true, false, 0x8005);
CalcCRC CalcCRC::CalcCRC_FIRE_CODE(false, false, 0x782f);
size_t CalcCRC::CRCLen = 2;

CalcCRC::CalcCRC(bool initialInvert, bool finalInvert, uint16_t polynomial)
	: initial_invert(initialInvert), final_invert(finalInvert), gen_polynom(polynomial)
{
	FillLUT();
}

void CalcCRC::FillLUT()
{
	for (int value = 0; value < 256; ++value)
	{
		uint16_t crc = static_cast<uint16_t>(value << 8);
		for (int bit = 0; bit < 8; ++bit)
			crc = static_cast<uint16_t>((crc & 0x8000) ? (crc << 1) ^ gen_polynom : crc << 1);
		crc_lut[value] = crc;
	}
}

void CalcCRC::Initialize(uint16_t &crc)
{
	crc = initial_invert ? 0xffff : 0;
}

void CalcCRC::ProcessByte(uint16_t &crc, uint8_t data)
{
	crc = static_cast<uint16_t>((crc << 8) ^ crc_lut[(crc >> 8) ^ data]);
}

void CalcCRC::Finalize(uint16_t &crc)
{
	if (final_invert)
		crc = static_cast<uint16_t>(~crc);
}

uint16_t CalcCRC::Calc(const uint8_t *data, size_t len)
{
	uint16_t crc;
	Initialize(crc);
	for (size_t i = 0; i < len; ++i)
		ProcessByte(crc, data[i]);
	Finalize(crc);
	return crc;
}

}
