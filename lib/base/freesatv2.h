#ifndef FREESAT_H
#define FREESAT_H

#include <stdlib.h>
#include <unistd.h>
#include <string>

struct huffTableEntry;

class freesatHuffmanDecoder
{
private:
	huffTableEntry *m_tables[2][256];
public:
	freesatHuffmanDecoder();
	~freesatHuffmanDecoder();
	std::string decode(const unsigned char *src, size_t size);
};
#endif

