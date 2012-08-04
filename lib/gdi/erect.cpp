#include <lib/gdi/erect.h>
#include <lib/base/eerror.h>

/*****************************************************************************
  eRect member functions
 *****************************************************************************/

eRect::eRect( const ePoint &topLeft, const ePoint &bottomRight )
{
	x1 = topLeft.x();
	y1 = topLeft.y();
	x2 = bottomRight.x();
	y2 = bottomRight.y();
}

eRect eRect::normalize() const
{
	eRect r;
	if ( x2 < x1 ) {				// swap bad x values
	r.x1 = x2;
	r.x2 = x1;
	} else {
	r.x1 = x1;
	r.x2 = x2;
	}
	if ( y2 < y1 ) {				// swap bad y values
	r.y1 = y2;
	r.y2 = y1;
	} else {
	r.y1 = y1;
	r.y2 = y2;
	}
	return r;
}

void eRect::rect( int *x, int *y, int *w, int *h ) const
{
	*x = x1;
	*y = y1;
	*w = x2-x1;
	*h = y2-y1;
}

void eRect::coords( int *xp1, int *yp1, int *xp2, int *yp2 ) const
{
	*xp1 = x1;
	*yp1 = y1;
	*xp2 = x2;
	*yp2 = y2;
}

void eRect::moveTopLeft( const ePoint &p )
{
	x2 += (p.x() - x1);
	y2 += (p.y() - y1);
	x1 = p.x();
	y1 = p.y();
}

void eRect::moveBottomRight( const ePoint &p )
{
	x1 += (p.x() - x2);
	y1 += (p.y() - y2);
	x2 = p.x();
	y2 = p.y();
}

void eRect::moveTopRight( const ePoint &p )
{
	x1 += (p.x() - x2);
	y2 += (p.y() - y1);
	x2 = p.x();
	y1 = p.y();
}

void eRect::moveBottomLeft( const ePoint &p )
{
	x2 += (p.x() - x1);
	y1 += (p.y() - y2);
	x1 = p.x();
	y2 = p.y();
}

void eRect::moveCenter( const ePoint &p )
{
	int w = x2 - x1;
	int h = y2 - y1;
	x1 = (p.x() - w/2);
	y1 = (p.y() - h/2);
	x2 = x1 + w;
	y2 = y1 + h;
}

void eRect::setRect( int x, int y, int w, int h )
{
	x1 = x;
	y1 = y;
	x2 = (x+w);
	y2 = (y+h);
}

void eRect::setCoords( int xp1, int yp1, int xp2, int yp2 )
{
	x1 = xp1;
	y1 = yp1;
	x2 = xp2;
	y2 = yp2;
}

void eRect::setWidth( int w )
{
	x2 = x1 + w;
}

void eRect::setHeight( int h )
{
	y2 = y1 + h;
}

void eRect::setSize( const eSize &s )
{
	x2 = s.width() +x1;
	y2 = s.height()+y1;
}

bool eRect::contains( const ePoint &p) const
{
	return p.x() >= x1 && p.x() < x2 &&
		   p.y() >= y1 && p.y() < y2;
}

bool eRect::contains( const eRect &r) const
{
	return r.x1 >= x1 &&
				 r.x2 <= x2 &&
				 r.y1 >= y1 &&
				 r.y2 <= y2;
}

eRect& eRect::operator|=(const eRect &r)
{
	*this = *this | r;
	return *this;
}

eRect& eRect::operator&=(const eRect &r)
{
	*this = *this & r;
	return *this;
}

eRect eRect::operator|(const eRect &r) const
{
	if ( valid() ) {
	if ( r.valid() ) {
		eRect tmp;
		tmp.setLeft(   MIN( x1, r.x1 ) );
		tmp.setRight(  MAX( x2, r.x2 ) );
		tmp.setTop(	   MIN( y1, r.y1 ) );
		tmp.setBottom( MAX( y2, r.y2 ) );
		return tmp;
	} else {
		return *this;
	}
	} else {
	return r;
	}
}

eRect eRect::unite( const eRect &r ) const
{
	return *this | r;
}

eRect eRect::operator&( const eRect &r ) const
{
	eRect tmp;
	tmp.x1 = MAX( x1, r.x1 );
	tmp.x2 = MIN( x2, r.x2 );
	tmp.y1 = MAX( y1, r.y1 );
	tmp.y2 = MIN( y2, r.y2 );
	return tmp;
}

eRect eRect::intersect( const eRect &r ) const
{
	return *this & r;
}

bool eRect::intersects( const eRect &r ) const
{
	return ( MAX( x1, r.x1 ) < MIN( x2, r.x2 ) &&
		 MAX( y1, r.y1 ) < MIN( y2, r.y2 ) );
}

bool operator==( const eRect &r1, const eRect &r2 )
{
	return r1.x1==r2.x1 && r1.x2==r2.x2 && r1.y1==r2.y1 && r1.y2==r2.y2;
}

bool operator!=( const eRect &r1, const eRect &r2 )
{
	return r1.x1!=r2.x1 || r1.x2!=r2.x2 || r1.y1!=r2.y1 || r1.y2!=r2.y2;
}

void eRect::scale(int x_n, int x_d, int y_n, int y_d) 
{
	ASSERT(x_d); ASSERT(y_d);
	x1 *= x_n; x1 /= x_d; 
	x2 *= x_n; x2 /= x_d; 
	y1 *= y_n; y1 /= y_d; 
	y2 *= y_n; y2 /= y_d; 
}

