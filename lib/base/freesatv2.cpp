/* 
FreeSat Huffman decoder for VDR
Copyright (C) 2008  DOM http://www.rst38.org.uk/vdr/
Port to C++ / Enigma 2
Copyright (C) 2008  Martin Croome

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
*/

#include "freesatv2.h"

freesatHuffmanDecoder::freesatHuffmanDecoder() : m_tablesLoaded(false)
{
	memset(m_tables, 0, sizeof(m_tables));
}

freesatHuffmanDecoder::~freesatHuffmanDecoder()
{
	int	i, j;
	huffTableEntry *currentEntry, *nextEntry;
	for ( j = 0 ; j < 2; j++ )
	{ 
		for ( i = 0 ; i < 256; i++ ) 
		{
			currentEntry = m_tables[j][i];
			while ( currentEntry != NULL )
			{
				nextEntry = currentEntry->nextEntry;
				delete currentEntry;
				currentEntry = nextEntry;
			}
			m_tables[j][i] = NULL;
		}
	}
}

void freesatHuffmanDecoder::loadTables()
{
	if (! m_tablesLoaded )
	{
		eDebug("[FREESAT] Load tables");
		loadFile(1, TABLE1_FILENAME);
		loadFile(2, TABLE2_FILENAME);
		m_tablesLoaded = true;
	}
}


/** \brief Convert a textual character description into a value
*
*  \param str - Encoded (in someway) string
*
*  \return Raw character
*/
static unsigned char resolveChar(char *str)
{
	if (str[1] == 0) return str[0];

	if ( strcmp(str,"ESCAPE") == 0 )
	{
		return ESCAPE;
	}
	else if ( strcmp(str,"STOP") == 0 )
	{
		return STOP;
	}
	else if ( strcmp(str,"START") == 0 )
	{
		return START;
	}
	else
	{
		int val;
		if ( sscanf(str,"0x%02x", &val) == 1 )
		{
			return val;
		}
	}
	return str[0];
}


/** \brief Decode a binary string into a value
*
*  \param binary - Binary string to decode
*
*  \return Decoded value
*/
static unsigned long decodeBinary(char *binary)
{
	unsigned long mask = 0x80000000;
	unsigned long val = 0;
	size_t i, len = strlen(binary);

	for ( i = 0; i < len; i++ )
	{
		if ( binary[i] == '1' )
		{
			val |= mask;
		}
		mask >>= 1;
	}
	return val;
}

/** \brief Load an individual freesat data file
*
*  \param tableid   - Table id that should be loaded
*  \param filename  - Filename to load
*/
void freesatHuffmanDecoder::loadFile(int tableid, char *filename)
{
	char     buf[1024];
	char    *from, *to, *binary;
	FILE    *fp;

	tableid--;

	if ( ( fp = fopen(filename,"r") ) != NULL )
	{
		eDebug("[FREESAT] Loading table %d Filename <%s>",tableid + 1, filename);

		while ( fgets(buf,sizeof(buf),fp) != NULL )
		{
			from = binary = to = NULL;
			int elems = sscanf(buf,"%a[^:]:%a[^:]:%a[^:]:", &from, &binary, &to);
			if ( elems == 3 )
			{
				int bin_len = strlen(binary);
				int from_char = resolveChar(from);
				char to_char = resolveChar(to);
				unsigned long bin = decodeBinary(binary);

				// Add entry to end of bucket
				huffTableEntry **pCurrent = &m_tables[tableid][from_char];
				while ( *pCurrent != NULL )
				{
					pCurrent = &((*pCurrent)->nextEntry);
				}
				*pCurrent = new huffTableEntry(bin, bin_len, to_char, NULL);
			}
			free(from);
			free(to);
			free(binary);
		}
		fclose(fp);
	}
	else
	{
		eDebug("[FREESAT] Cannot load <%s> for table %d",filename,tableid + 1);
	}
}


/** \brief Decode an EPG string as necessary
*
*  \param src - Possibly encoded string
*  \param size - Size of the buffer
*
*  \retval NULL - Can't decode
*  \return A decoded string
*/
std::string freesatHuffmanDecoder::decode(const unsigned char *src, size_t size)
{
	std::string uncompressed;
	int tableid;

	loadTables();

	if (src[0] == 0x1f && (src[1] == 1 || src[1] == 2))
	{
		unsigned value = 0, byte = 2, bit = 0;
		int lastch = START;

		tableid = src[1] - 1;
		while (byte < 6 && byte < size)
		{
			value |= src[byte] << ((5-byte) * 8);
			byte++;
		}

		do
		{
			int found = 0;
			unsigned bitShift = 0;
			if (lastch == ESCAPE)
			{
				char nextCh = (value >> 24) & 0xff;
				found = 1;
				// Encoded in the next 8 bits.
				// Terminated by the first ASCII character.
				bitShift = 8;
				if ((nextCh & 0x80) == 0)
					lastch = nextCh;
				uncompressed.append(&nextCh, 1);
			}
			else
			{
				huffTableEntry * currentEntry = m_tables[tableid][lastch];
				while ( currentEntry != NULL )
				{
					unsigned mask = 0, maskbit = 0x80000000;
					short kk;
					for ( kk = 0; kk < currentEntry->bits; kk++)
					{
						mask |= maskbit;
						maskbit >>= 1;
					}
					if ((value & mask) == currentEntry->value)
					{
						char nextCh = currentEntry->next;
						bitShift = currentEntry->bits;
						if (nextCh != STOP && nextCh != ESCAPE)
						{
							uncompressed.append(&nextCh, 1);
						}
						found = 1;
						lastch = nextCh;
						break;
					}
					currentEntry = currentEntry->nextEntry;
				}
			}
			if (found)
			{
				// Shift up by the number of bits.
				unsigned b;
				for ( b = 0; b < bitShift; b++)
				{
					value = (value << 1) & 0xfffffffe;
					if (byte < size)
						value |= (src[byte] >> (7-bit)) & 1;
					if (bit == 7)
					{
						bit = 0;
						byte++;
					}
					else bit++;
				}
			}
			else
			{
				eDebug("[FREESAT] Missing table %d entry: <%s>", tableid + 1, uncompressed.c_str());
				return uncompressed;
			}
		} while (lastch != STOP && value != 0);
	}
	return uncompressed;
}
