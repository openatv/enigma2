#ifndef __lib_gdi_region_h
#define __lib_gdi_region_h

#include <lib/base/object.h>
#include <lib/gdi/erect.h>
#include <vector>

class gRegion
{
private:
	inline void FindBand(
			std::vector<eRect>::const_iterator r,
			std::vector<eRect>::const_iterator &rBandEnd,
			std::vector<eRect>::const_iterator rEnd,
			int &ry1)
	{
		ry1 = r->y1;
		rBandEnd = r+1;
		while ((rBandEnd != rEnd) && (rBandEnd->y1 == ry1))
			rBandEnd++;
	}

	inline void AppendRegions(
		std::vector<eRect>::const_iterator r,
		std::vector<eRect>::const_iterator rEnd)
	{
		rects.insert(rects.end(), r, rEnd);
	}

	int do_coalesce(int prevStart, unsigned int curStart);
	inline void coalesce(int &prevBand, unsigned int curBand)
	{
		if (curBand - prevBand == rects.size() - curBand) {
			prevBand = do_coalesce(prevBand, curBand);
		} else {
			prevBand = curBand;
		}
	};
	void appendNonO(std::vector<eRect>::const_iterator r,
			std::vector<eRect>::const_iterator rEnd, int y1, int y2);

	void intersectO(
			std::vector<eRect>::const_iterator r1,
			std::vector<eRect>::const_iterator r1End,
			std::vector<eRect>::const_iterator r2,
			std::vector<eRect>::const_iterator r2End,
			int y1, int y2,
			int &overlap);
	void subtractO(
			std::vector<eRect>::const_iterator r1,
			std::vector<eRect>::const_iterator r1End,
			std::vector<eRect>::const_iterator r2,
			std::vector<eRect>::const_iterator r2End,
			int y1, int y2,
			int &overlap);
	void mergeO(
			std::vector<eRect>::const_iterator r1,
			std::vector<eRect>::const_iterator r1End,
			std::vector<eRect>::const_iterator r2,
			std::vector<eRect>::const_iterator r2End,
			int y1, int y2,
			int &overlap);
	void regionOp(const gRegion &reg1, const gRegion &reg2, int opcode, int &overlap);
public:
	std::vector<eRect> rects;
	eRect extends;

	enum
	{
			// note: bit 0 and bit 1 have special meanings
		OP_INTERSECT = 0,
		OP_SUBTRACT  = 1,
		OP_UNION     = 3
	};

	gRegion(const eRect &rect);
	gRegion();
	virtual ~gRegion();

	gRegion operator&(const gRegion &r2) const;
	gRegion operator-(const gRegion &r2) const;
	gRegion operator|(const gRegion &r2) const;
	gRegion &operator&=(const gRegion &r2);
	gRegion &operator-=(const gRegion &r2);
	gRegion &operator|=(const gRegion &r2);

	friend bool operator == (const gRegion &, const gRegion &);
	friend bool operator != (const gRegion &, const gRegion &);

	void intersect(const gRegion &r1, const gRegion &r2);
	void subtract(const gRegion &r1, const gRegion &r2);
	void merge(const gRegion &r1, const gRegion &r2);

	void moveBy(ePoint offset);

	bool empty() const { return extends.empty(); }
	bool valid() const { return extends.valid(); }

	static gRegion invalidRegion() { return gRegion(eRect::invalidRect()); }

	void scale(int x_n, int x_d, int y_n, int y_d);
};

bool operator == (const gRegion &, const gRegion &);
bool operator != (const gRegion &, const gRegion &);

#endif
