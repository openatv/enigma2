#include <lib/base/cachedtssource.h>

static const unsigned int CACHE_SIZE = 32*1024;

DEFINE_REF(eCachedSource);

eCachedSource::eCachedSource(ePtr<iTsSource>& source)
	: iTsSource(source->getPacketSize())
	, m_source(source)
	, m_cache_buffer((char*)malloc(CACHE_SIZE))
	, m_cache_offset(0)
	, m_cache_bytes(0)
{
}

eCachedSource::~eCachedSource()
{
	free(m_cache_buffer);
}

ssize_t eCachedSource::read(off_t offset, void *buf, size_t count)
{
	/* Not quite optimal, but just enough to read bit more efficient than tiny 188 byte chunks */
	if (count >= CACHE_SIZE)
		return m_source->read(offset, buf, count);
	if ((offset < m_cache_offset) || (offset+count >= m_cache_offset + m_cache_bytes))
	{
		/* Update the cache */
		ssize_t bytes = m_source->read(offset, m_cache_buffer, CACHE_SIZE);
		if (bytes <= 0)
			return bytes;
		if ((size_t)bytes < count)
			count = bytes; /* probably past EOF */
		m_cache_offset = offset;
		m_cache_bytes = bytes;
	}
	unsigned int cache_index = offset - m_cache_offset;
	memcpy(buf, m_cache_buffer + cache_index, count);
	return count;
}

int eCachedSource::valid()
{
	return (m_cache_buffer != NULL) && m_source->valid();
}

off_t eCachedSource::length()
{
	return m_source->length();
}

off_t eCachedSource::offset()
{
	return m_cache_offset;
}
