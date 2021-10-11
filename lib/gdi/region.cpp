#include <lib/gdi/erect.h>
#include <lib/gdi/epoint.h>
#include <lib/gdi/region.h>
#include <lib/base/eerror.h>

#undef max
#define max(a,b)  ((a) > (b) ? (a) : (b))
#undef min
#define min(a,b)  ((a) < (b) ? (a) : (b))


/*

	Region code.

	A region is basically a list of rectangles. In this implementation,
	rectangles are ordered by their upper-left position, organized in bands.

	this code stolen from miregion.c out of the X-Window system.
	for implementation details, look into their source.
	This code does all the ugly stuff.

	Thanks go out to ryg, for explaining me this stuff.

*/

gRegion::gRegion(const eRect &rect) : extends(rect)
{
	if (rect.valid() && !rect.empty())
		rects.push_back(rect);
}

gRegion::gRegion() : extends(eRect::emptyRect())
{
}

gRegion::~gRegion()
{
}

int gRegion::do_coalesce(int prevStart, unsigned int curStart)
{
	// Figure out how many rectangles are in the band.
	unsigned int numRects = curStart - prevStart;
	ASSERT(numRects == rects.size() - curStart);
	if (!numRects)
		return curStart;
	std::vector<eRect>::iterator prevBox = rects.begin() + prevStart;
	std::vector<eRect>::const_iterator  curBox = rects.begin() + curStart;

	// The bands may only be coalesced if the bottom of the previous
	// matches the top scanline of the current.
	if (prevBox->y2 != curBox->y1)
		return curStart;

	// Make sure the bands have boxes in the same places. This
	// assumes that boxes have been added in such a way that they
	// cover the most area possible. I.e. two boxes in a band must
	// have some horizontal space between them.

	int y2 = curBox->y2;

	do {
		if ((prevBox->x1 != curBox->x1) || (prevBox->x2 != curBox->x2))
			return curStart;
		++prevBox;
		++curBox;
		--numRects;
	} while ( numRects );

	// The bands may be merged, so set the bottom y of each box
	// in the previous band to the bottom y of the current band.
	numRects = curStart - prevStart;
	do {
		--prevBox;
		prevBox->y2 = y2;
		numRects--;
	} while (numRects);
	rects.resize(rects.size() - (curStart - prevStart));
	return prevStart;
}

void gRegion::appendNonO(std::vector<eRect>::const_iterator r,
			std::vector<eRect>::const_iterator rEnd, int y1, int y2)
{
	int newRects = rEnd - r;
	ASSERT(y1 < y2);
	ASSERT(newRects != 0);
	rects.reserve(rects.size() + newRects);
	do {
		ASSERT(r->x1 < r->x2);
		rects.push_back(eRect(r->x1, y1, r->x2 - r->x1, y2 - y1));
		++r;
	} while (r != rEnd);
}

void gRegion::intersectO(
		std::vector<eRect>::const_iterator r1,
		std::vector<eRect>::const_iterator r1End,
		std::vector<eRect>::const_iterator r2,
		std::vector<eRect>::const_iterator r2End,
		int y1, int y2,
		int &overlap)
{
	int x1, x2;

	ASSERT(y1 < y2);
	ASSERT(r1 != r1End && r2 != r2End);

	do {
		x1 = max(r1->x1, r2->x1);
		x2 = min(r1->x2, r2->x2);

		if (x1 < x2)
			rects.push_back(eRect(x1, y1, x2 - x1, y2 - y1));
		if (r1->x2 == x2)
			++r1;
		if (r2->x2 == x2)
			++r2;
	} while ( (r1 != r1End) && (r2 != r2End));
}

void gRegion::subtractO(
		std::vector<eRect>::const_iterator r1,
		std::vector<eRect>::const_iterator r1End,
		std::vector<eRect>::const_iterator r2,
		std::vector<eRect>::const_iterator r2End,
		int y1, int y2,
		int &overlap)
{
	int x1;
	x1 = r1->x1;

	ASSERT(y1<y2);
	ASSERT(r1 != r1End && r2 != r2End);

	do {
		if (r2->x2 <= x1)
			++r2;
		else if (r2->x1 <= x1) {
			x1 = r2->x2;
			if (x1 >= r1->x2) {
				++r1;
				if (r1 != r1End)
					x1 = r1->x1;
			} else
				++r2;
		} else if (r2->x1 < r1->x2) {
			ASSERT(x1<r2->x1);
			rects.push_back(eRect(x1, y1, r2->x1 - x1, y2 - y1));
			x1 = r2->x2;
			if (x1 >= r1->x2) {
				++r1;
				if (r1 != r1End)
					x1 = r1->x1;
			} else
				++r2;
		} else
		{
			if (r1->x2 > x1)
				rects.push_back(eRect(x1, y1, r1->x2 - x1, y2 - y1));
			++r1;
			if (r1 != r1End)
				x1 = r1->x1;
		}
	} while ((r1 != r1End) && (r2 != r2End));
	while (r1 != r1End)
	{
		ASSERT(x1<r1->x2);
		rects.push_back(eRect(x1, y1, r1->x2 - x1, y2 - y1));
		++r1;
		if (r1 != r1End)
			x1 = r1->x1;
	}
}

#define MERGERECT(r)                                        \
{                                                           \
	if (r->x1 <= x2) {                                        \
		/* Merge with current rectangle */                      \
		if (r->x1 < x2) overlap = 1;                            \
		if (x2 < r->x2) x2 = r->x2;                             \
	} else {                                                  \
		/* Add current rectangle, start new one */              \
		rects.push_back(eRect(x1, y1, x2 - x1, y2 - y1));       \
		x1 = r->x1;                                             \
		x2 = r->x2;                                             \
	}                                                         \
	++r;                                                      \
}

void gRegion::mergeO(
		std::vector<eRect>::const_iterator r1,
		std::vector<eRect>::const_iterator r1End,
		std::vector<eRect>::const_iterator r2,
		std::vector<eRect>::const_iterator r2End,
		int y1, int y2,
		int &overlap)
{
	int x1, x2;

	ASSERT(y1 < y2);
	ASSERT(r1 != r1End && r2 != r2End);

	if (r1->x1 < r2->x1)
	{
		x1 = r1->x1;
		x2 = r1->x2;
		++r1;
	} else {
		x1 = r2->x1;
		x2 = r2->x2;
		++r2;
	}

	while (r1 != r1End && r2 != r2End)
		if (r1->x1 < r2->x1) MERGERECT(r1) else MERGERECT(r2);

	if (r1 != r1End)
	{
		do {
			MERGERECT(r1);
		} while (r1 != r1End);
	} else if (r2 != r2End)
	{
		do {
			MERGERECT(r2);
		} while (r2 != r2End);
	}
	rects.push_back(eRect(x1, y1, x2 - x1, y2 - y1));
}

void gRegion::regionOp(const gRegion &reg1, const gRegion &reg2, int opcode, int &overlap)
{
	std::vector<eRect>::const_iterator r1, r1End, r2, r2End, r1BandEnd, r2BandEnd;
	int prevBand;
	int r1y1, r2y1;
	int curBand, ytop, top, bot;

	r1    = reg1.rects.begin();
	r1End = reg1.rects.end();
	r2    = reg2.rects.begin();
	r2End = reg2.rects.end();

	int newSize  = reg1.rects.size();
	int numRects = reg2.rects.size();
	ASSERT(r1 != r1End);
	ASSERT(r2 != r2End);

	if (numRects > newSize)
		newSize = numRects;
	newSize <<= 1;

	rects.reserve(newSize);

	int ybot = min(r1->y1, r2->y1);
	prevBand = 0;
	do {
		ASSERT(r1 != r1End);
		ASSERT(r2 != r2End);
		FindBand(r1, r1BandEnd, r1End, r1y1);
		FindBand(r2, r2BandEnd, r2End, r2y1);
		if (r1y1 < r2y1) {
			if (opcode & 1) {
				top = max(r1y1, ybot);
				bot = min(r1->y2, r2y1);
				if (top != bot) {
					curBand = rects.size();
					appendNonO(r1, r1BandEnd, top, bot);
					coalesce(prevBand, curBand);
				}
			}
			ytop = r2y1;
		} else if (r2y1 < r1y1) {
			if (opcode & 2) {
				top = max(r2y1, ybot);
				bot = min(r2->y2, r1y1);
				if (top != bot) {
					curBand = rects.size();
					appendNonO(r2, r2BandEnd, top, bot);
					coalesce(prevBand, curBand);
				}
			}
			ytop = r1y1;
		} else
			ytop = r1y1;
		ybot = min(r1->y2, r2->y2);
		if (ybot > ytop) {
			curBand = rects.size();
			switch (opcode)
			{
			case OP_INTERSECT:
				intersectO(r1, r1BandEnd, r2, r2BandEnd, ytop, ybot, overlap);
				break;
			case OP_SUBTRACT:
				subtractO(r1, r1BandEnd, r2, r2BandEnd, ytop, ybot, overlap);
				break;
			case OP_UNION:
				mergeO(r1, r1BandEnd, r2, r2BandEnd, ytop, ybot, overlap);
				break;
			default:
				ASSERT(0);
				break;
			}
			coalesce(prevBand, curBand);
		}
		if (r1->y2 == ybot) r1 = r1BandEnd;
		if (r2->y2 == ybot) r2 = r2BandEnd;
	} while (r1 != r1End && r2 != r2End);
	if ((r1 != r1End) && (opcode & 1)) {
		FindBand(r1, r1BandEnd, r1End, r1y1);
		curBand = rects.size();
		appendNonO(r1, r1BandEnd, max(r1y1, ybot), r1->y2);
		coalesce(prevBand, curBand);
		AppendRegions(r1BandEnd, r1End);
	} else if ((r2 != r2End) && (opcode & 2)) {
		FindBand(r2, r2BandEnd, r2End, r2y1);
		curBand = rects.size();
		appendNonO(r2, r2BandEnd, max(r2y1, ybot), r2->y2);
		coalesce(prevBand, curBand);
		AppendRegions(r2BandEnd, r2End);
	}

	extends = eRect();

	for (unsigned int a = 0; a<rects.size(); ++a)
		extends = extends | rects[a];
	if (!extends.valid())
		extends = eRect::emptyRect();
}

void gRegion::intersect(const gRegion &r1, const gRegion &r2)
{
		/* in case one region is empty, the resulting regions is empty, too. */
	if (r1.rects.empty())
	{
		*this = r1;
		return;
	}
	if (r2.rects.empty())
	{
		*this = r2;
		return;
	}
	if (r1 == r2)
	{
		*this = r1;
		return;
	}
	int overlap;
	// TODO: handle trivial reject
	regionOp(r1, r2, OP_INTERSECT, overlap);
}

void gRegion::subtract(const gRegion &r1, const gRegion &r2)
{
	if (r1.rects.empty() || r2.rects.empty())
	{
		*this = r1;
		return;
	}
	int overlap;
	// TODO: handle trivial reject
	regionOp(r1, r2, OP_SUBTRACT, overlap);
}

void gRegion::merge(const gRegion &r1, const gRegion &r2)
{
	if (r1.rects.empty())
	{
		*this = r2;
		return;
	}
	if (r2.rects.empty())
	{
		*this = r1;
		return;
	}
	if (r1 == r2)
	{
		*this = r1;
		return;
	}
	int overlap;
	// TODO: handle trivial reject
	regionOp(r1, r2, OP_UNION, overlap);
}

gRegion gRegion::operator&(const gRegion &r2) const
{
	gRegion res;
	res.intersect(*this, r2);
	return res;
}

gRegion gRegion::operator-(const gRegion &r2) const
{
	gRegion res;
	res.subtract(*this, r2);
	return res;
}

gRegion gRegion::operator|(const gRegion &r2) const
{
	gRegion res;
	res.merge(*this, r2);
	return res;
}

gRegion &gRegion::operator&=(const gRegion &r2)
{
	gRegion res;
	res.intersect(*this, r2);
	return *this = res;
}

gRegion &gRegion::operator-=(const gRegion &r2)
{
	gRegion res;
	res.subtract(*this, r2);
	return *this = res;
}

gRegion &gRegion::operator|=(const gRegion &r2)
{
	gRegion res;
	res.merge(*this, r2);
	return *this = res;
}

void gRegion::moveBy(ePoint offset)
{
	extends.moveBy(offset);
	unsigned int i;
	for (i=0; i<rects.size(); ++i)
		rects[i].moveBy(offset);
}

void gRegion::scale(int x_n, int x_d, int y_n, int y_d)
{
	unsigned int i;
	for (i=0; i<rects.size(); ++i)
		rects[i].scale(x_n, x_d, y_n, y_d);
}

bool operator == (const gRegion &r1, const gRegion &r2)
{
	if (r1.rects.size() != r2.rects.size()) return false;

	for (unsigned int i = 0; i < r1.rects.size(); i++)
	{
		if (r1.rects[i] != r2.rects[i])
		{
			return false;
		}
	}
	return true;
}

bool operator != (const gRegion &r1, const gRegion &r2)
{
	if (r1.rects.size() != r2.rects.size()) return true;

	for (unsigned int i = 0; i < r1.rects.size(); i++)
	{
		if (r1.rects[i] != r2.rects[i])
		{
			return true;
		}
	}
	return false;
}
