#include <lib/base/buffer.h>
#include <lib/base/eerror.h>
#include <cerrno>
#include <cstdio>
#include <cstring>
#include <unistd.h>

void eIOBuffer::removeblock()
{
	ASSERT(!buffer.empty());
	eIOBufferData &b=buffer.front();
	delete[] b.data;
	buffer.pop_front();
	ptr=0;
}

eIOBuffer::eIOBufferData &eIOBuffer::addblock()
{
	eIOBufferData s;
	s.data=new __u8[allocationsize];
	s.len=0;
	buffer.push_back(s);
	return buffer.back();
}

eIOBuffer::~eIOBuffer()
{
	clear();
}

void eIOBuffer::clear()
{
	while (!buffer.empty())
		removeblock();
}

int eIOBuffer::size() const
{
	int total=0;
	for (std::list<eIOBufferData>::const_iterator i(buffer.begin()); i != buffer.end(); ++i)
		total+=i->len;
	total-=ptr;
	return total;
}

int eIOBuffer::empty() const
{
	return buffer.empty();
}

int eIOBuffer::peek(void *dest, int len) const
{
	__u8 *dst=(__u8*)dest;
	std::list<eIOBufferData>::const_iterator i(buffer.begin());
	int p=ptr;
	int written=0;
	while (len)
	{	
		if (i == buffer.end())
			break;
		int tc=i->len-p;
		if (tc > len)
			tc = len;
	
		memcpy(dst, i->data+p, tc);
		dst+=tc;
		written+=tc;
	
		++i;
		p=0;
			
		len-=tc;
	}
	return written;
}

void eIOBuffer::skip(int len)
{
	while (len)
	{
		ASSERT(! buffer.empty());
		int tn=len;
		if (tn > (buffer.front().len-ptr))
			tn=buffer.front().len-ptr;

		ptr+=tn;
		if (ptr == buffer.front().len)
			removeblock();
		len-=tn;
	}
}

int eIOBuffer::read(void *dest, int len)
{
	__u8 *dst=(__u8*)dest;
	len=peek(dst, len);
	skip(len);
	return len;
}

void eIOBuffer::write(const void *source, int len)
{
	const __u8 *src=(const __u8*)source;
	while (len)
	{
		int tc=len;
		if (buffer.empty() || (allocationsize == buffer.back().len))
			addblock();
		if (tc > allocationsize-buffer.back().len)
			tc=allocationsize-buffer.back().len;
		memcpy(buffer.back().data+buffer.back().len, src, tc);
		src+=tc;
		buffer.back().len+=tc;
		len-=tc;
	}
}

int eIOBuffer::fromfile(int fd, int len)
{
	int re=0;
	while (len)
	{
		int tc=len;
		int r=0;
		if (buffer.empty() || (allocationsize == buffer.back().len))
			addblock();
		if (tc > allocationsize-buffer.back().len)
			tc=allocationsize-buffer.back().len;
		r=::read(fd, buffer.back().data+buffer.back().len, tc);
		buffer.back().len+=r;
		if (r < 0)
		{
			if (errno != EWOULDBLOCK && errno != EBUSY && errno != EINTR)
				eDebug("couldn't read: %m");
		}
		else
		{
			len-=r;
			re+=r;
			if (r != tc)
				break;
		}
	}
	return re;
}

int eIOBuffer::tofile(int fd, int len)
{
	int written=0;
	int w;
	while (len && !buffer.empty())
	{	
		if (buffer.begin() == buffer.end())
			break;
		int tc=buffer.front().len-ptr;
		if (tc > len)
			tc = len;
	
		w=::write(fd, buffer.front().data+ptr, tc);
		if (w < 0)
		{
			if (errno != EWOULDBLOCK && errno != EBUSY && errno != EINTR)
				eDebug("write: %m");
			w=0;
		}
		ptr+=w;
		if (ptr == buffer.front().len)
			removeblock();
		written+=w;	

		len-=w;
		if (tc != w)
			break;
	}
	return written;
}

int eIOBuffer::searchchr(char ch) const
{
	std::list<eIOBufferData>::const_iterator i(buffer.begin());
	int p=ptr;
	int c=0;
	while (1)
	{	
		if (i == buffer.end())
			break;
		while (p < i->len)
		{
			if (i->data[p] == ch)
				return c;
			else
				c++, p++;
		}
		++i;
		p=0;
	}
	return -1;
}

