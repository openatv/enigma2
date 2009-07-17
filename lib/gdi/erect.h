#ifndef ERECT_H
#define ERECT_H

#include <lib/gdi/esize.h>
#include <lib/gdi/epoint.h>


// x2 = x1 + width  (AND NOT, NEVER, NEVER EVER +1 or -1 !!!!)

class eRect // rectangle class
{
	friend class gRegion;
public:
			/* eRect() constructs an INVALID rectangle. */
	eRect()	{ x1 = y1 = 0; x2 = y2 = -1; }
	eRect( const ePoint &topleft, const ePoint &bottomright );

	// we use this contructor very often... do it inline...
	eRect( const ePoint &topleft, const eSize &size )
	{
		x1 = topleft.x();
		y1 = topleft.y();
		x2 = (x1+size.width());
		y2 = (y1+size.height());
	}

	eRect( int left, int top, int width, int height );

	bool empty()	const;
	bool valid()	const;
	eRect normalize()	const;

	int left()	const;
	int top()	const;
	int right()	const;
	int  bottom()	const;
	int &rLeft();
	int &rTop();
	int &rRight();
	int &rBottom();

	int x() const;
	int y() const;
	void setLeft( int pos );
	void setTop( int pos );
	void setRight( int pos );
	void setBottom( int pos );
	void setX( int x );
	void setY( int y );

	ePoint topLeft()	 const;
	ePoint bottomRight() const;
	ePoint topRight()	 const;
	ePoint bottomLeft()	 const;

		/* the sole intention of these functions
		   is to allow painting frames without 
		   messing around with the coordinates.
		   they point to the last pixel included
		   in the rectangle (which means that 1 is
		   subtracted from the right and bottom 
		   coordinates  */
	ePoint topLeft1()	 const;
	ePoint bottomRight1() const;
	ePoint topRight1()	 const;
	ePoint bottomLeft1()	 const;
	ePoint center()	 const;

	void rect( int *x, int *y, int *w, int *h ) const;
	void coords( int *x1, int *y1, int *x2, int *y2 ) const;

	void moveTopLeft( const ePoint &p );
	void moveBottomRight( const ePoint &p );
	void moveTopRight( const ePoint &p );
	void moveBottomLeft( const ePoint &p );
	void moveCenter( const ePoint &p );

	void moveBy( int dx, int dy )
	{
		x1 += dx;
		y1 += dy;
		x2 += dx;
		y2 += dy;
	}

	void moveBy(ePoint r)
	{
		x1 += r.x();
		y1 += r.y();
		x2 += r.x();
		y2 += r.y();
	}

	void setRect( int x, int y, int w, int h );
	void setCoords( int x1, int y1, int x2, int y2 );

	eSize size()	const;
	int width()	const;
	int height()	const;
	void setWidth( int w );
	void setHeight( int h );
	void setSize( const eSize &s );

	eRect operator|(const eRect &r) const;
	eRect operator&(const eRect &r) const;
 	eRect& operator|=(const eRect &r);
 	eRect& operator&=(const eRect &r);

	bool contains( const ePoint &p) const;
	bool contains( int x, int y) const;
	bool contains( const eRect &r) const;
	eRect unite( const eRect &r ) const;
	eRect intersect( const eRect &r ) const;
	bool intersects( const eRect &r ) const;

	friend bool operator==( const eRect &, const eRect & );
	friend bool operator!=( const eRect &, const eRect & );
	
	static eRect emptyRect() { return eRect(0, 0, 0, 0); }
	static eRect invalidRect() { return eRect(); }
	
	void scale(int x_n, int x_d, int y_n, int y_d);
	
private:
	int x1;
	int y1;
	int x2;
	int y2;
};

bool operator==( const eRect &, const eRect & );
bool operator!=( const eRect &, const eRect & );


/*****************************************************************************
  eRect inline member functions
 *****************************************************************************/

inline eRect::eRect( int left, int top, int width, int height )
{
	x1 = left;
	y1 = top;
	x2 = left+width;
	y2 = top+height;
}

inline bool eRect::empty() const
{ return x1 >= x2 || y1 >= y2; }

inline bool eRect::valid() const
{ return x1 <= x2 && y1 <= y2; }

inline int eRect::left() const
{ return x1; }

inline int eRect::top() const
{ return y1; }

inline int eRect::right() const
{ return x2; }

inline int eRect::bottom() const
{ return y2; }

inline int &eRect::rLeft()
{ return x1; }

inline int & eRect::rTop()
{ return y1; }

inline int & eRect::rRight()
{ return x2; }

inline int & eRect::rBottom()
{ return y2; }

inline int eRect::x() const
{ return x1; }

inline int eRect::y() const
{ return y1; }

inline void eRect::setLeft( int pos )
{ x1 = pos; }

inline void eRect::setTop( int pos )
{ y1 = pos; }

inline void eRect::setRight( int pos )
{ x2 = pos; }

inline void eRect::setBottom( int pos )
{ y2 = pos; }

inline void eRect::setX( int x )
{ x1 = x; }

inline void eRect::setY( int y )
{ y1 = y; }

inline ePoint eRect::topLeft() const
{ return ePoint(x1, y1); }

inline ePoint eRect::bottomRight() const
{ return ePoint(x2, y2); }

inline ePoint eRect::topRight() const
{ return ePoint(x2, y1); }

inline ePoint eRect::bottomLeft() const
{ return ePoint(x1, y2); }

inline ePoint eRect::topLeft1() const
{ return ePoint(x1, y1); }

inline ePoint eRect::bottomRight1() const
{ return ePoint(x2-1, y2-1); }

inline ePoint eRect::topRight1() const
{ return ePoint(x2-1, y1); }

inline ePoint eRect::bottomLeft1() const
{ return ePoint(x1, y2-1); }

inline ePoint eRect::center() const
{ return ePoint((x1+x2)/2, (y1+y2)/2); }

inline int eRect::width() const
{ return  x2 - x1; }

inline int eRect::height() const
{ return  y2 - y1; }

inline eSize eRect::size() const
{ return eSize(x2-x1, y2-y1); }

inline bool eRect::contains( int x, int y) const
{
	return (x >= x1) && (x < x2) && (y >= y1) && (y < y2);
}

#endif // eRect_H
