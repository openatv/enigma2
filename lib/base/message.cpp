#include <lib/base/message.h>
#include <unistd.h>
#include <lib/base/eerror.h>

eMessagePump::eMessagePump(int mt): content(1024*1024), ismt(mt)
{
	pipe(fd);
}

eMessagePump::~eMessagePump()
{	
	if (ismt)
		content.lock(); // blocks until all messages are processed.
	close(fd[0]);
	close(fd[1]);
}

int eMessagePump::send(const void *data, int len)
{
	if (ismt)
		content.lock(len);
	return ::write(fd[1], data, len)<0;
}

int eMessagePump::recv(void *data, int len)
{
	unsigned char*dst=(unsigned char*)data;
	while (len)
	{
		if (ismt)
			content.unlock(len);
		int r=::read(fd[0], dst, len);
		if (r<0)
			return r;
		dst+=r;
		len-=r;
	}
	return 0;
}

int eMessagePump::getInputFD() const
{
	return fd[1];
}

int eMessagePump::getOutputFD() const
{
	return fd[0];
}
