#ifndef __src_lib_base_buffer_h
#define __src_lib_base_buffer_h

#include <asm/types.h>
#include <list>

/**
 * IO buffer.
 */
class eIOBuffer
{
	int allocationsize;
	struct eIOBufferData
	{
		__u8 *data;
		int len;
	};
	std::list<eIOBufferData> buffer;
	void removeblock();
	eIOBufferData &addblock();
	int ptr;
public:
	eIOBuffer(int allocationsize): allocationsize(allocationsize), ptr(0)
	{
	}
	~eIOBuffer();
	int size() const;
	int empty() const;
	void clear();
	int peek(void *dest, int len) const;
	void skip(int len);
	int read(void *dest, int len);
	void write(const void *source, int len);
	int fromfile(int fd, int len);
	int tofile(int fd, int len);

	int searchchr(char ch) const;
};

#endif
