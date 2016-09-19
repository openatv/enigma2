#ifndef __lib_base_idatasource_h
#define __lib_base_idatasource_h

#include <lib/base/object.h>

class iTsSource: public iObject
{
protected:
	unsigned int packetSize;

public:
	iTsSource(unsigned int packetsize = 188) : packetSize(packetsize) {}

	/* NOTE: you must be able to handle short reads! */
	virtual ssize_t read(off_t offset, void *buf, size_t count)=0; /* NOTE: this is what you in normal case have to use!! */

	/* Fetch the length, without side-effects like seeking */
	virtual off_t length()=0;
	virtual int valid()=0;
	virtual off_t offset() = 0;
	virtual bool isStream() { return false; }
	unsigned int getPacketSize() const { return packetSize; }
};

#endif
