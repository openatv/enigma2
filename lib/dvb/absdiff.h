#ifndef __ABSDIFF__
#define __ABSDIFF__

static inline unsigned int absdiff(unsigned int a, unsigned int b)
{
	return a < b ? (b - a) : (a - b);
}

#endif // __ABSDIFF__
