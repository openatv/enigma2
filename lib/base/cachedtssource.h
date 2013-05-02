#ifndef __lib_base_cachedtssource_h
#define __lib_base_cachedtssource_h

#include <lib/base/itssource.h>

class eCachedSource: public iTsSource
{
	DECLARE_REF(eCachedSource);
public:
	eCachedSource(ePtr<iTsSource>& source);
	~eCachedSource();

	// iTsSource
	ssize_t read(off_t offset, void *buf, size_t count);
	off_t length();
	off_t offset();
	int valid();
	bool isStream() { return m_source->isStream(); };
private:
	ePtr<iTsSource> m_source;
	char* m_cache_buffer;
	off_t m_cache_offset;
	unsigned int m_cache_bytes;
};

#endif
