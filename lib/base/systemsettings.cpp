int flushSize = 512 * 1024;
int demuxSize = 8 * 188 * 1024;

int getFlushSize(void)
{
	return flushSize;
}
void setFlushSize(int size)
{
	if (size >= 0)
	{
		flushSize = size;
	}
}

int getDemuxSize(void)
{
	return demuxSize;
}

void setDemuxSize(int size)
{
	if ((size >= 2*188*1024) && (size < 16*188*1024))
	{
		demuxSize = size;
	}
}

