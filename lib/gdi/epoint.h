#ifndef EPOINT_H
#define EPOINT_H

#ifndef ABS
#define ABS(x) ( x>0 ? x : -x )
#endif

class ePoint
{
public:
	ePoint();
	ePoint( int xpos, int ypos );

	bool   isNull()	const;

	int	   x()		const;
	int	   y()		const;
	void   setX( int x );
	void   setY( int y );

	int manhattanLength() const;

	int &rx();
	int &ry();

	ePoint &operator+=( const ePoint &p );
	ePoint &operator-=( const ePoint &p );
	ePoint &operator*=( int c );
	ePoint &operator*=( double c );
	ePoint &operator/=( int c );
	ePoint &operator/=( double c );

	friend inline bool	 operator==( const ePoint &, const ePoint & );
	friend inline bool	 operator!=( const ePoint &, const ePoint & );
	friend inline ePoint operator+( const ePoint &, const ePoint & );
	friend inline ePoint operator+( const ePoint &, const eSize & );
	friend inline ePoint operator-( const ePoint &, const ePoint & );
	friend inline ePoint operator-( const ePoint &, const eSize & );
	friend inline ePoint operator*( const ePoint &, int );
	friend inline ePoint operator*( int, const ePoint & );
	friend inline ePoint operator*( const ePoint &, double );
	friend inline ePoint operator*( double, const ePoint & );
	friend inline ePoint operator-( const ePoint & );
	friend inline ePoint operator/( const ePoint &, int );
	friend inline ePoint operator/( const ePoint &, double );
private:
	int xp;
	int yp;
};


inline int ePoint::manhattanLength() const
{
	return ABS(x())+ABS(y());
}


/*****************************************************************************
  ePoint inline functions
 *****************************************************************************/

inline ePoint::ePoint()
{ xp=0; yp=0; }

inline ePoint::ePoint( int xpos, int ypos )
{ xp=(int)xpos; yp=(int)ypos; }

inline bool ePoint::isNull() const
{ return xp == 0 && yp == 0; }

inline int ePoint::x() const
{ return xp; }

inline int ePoint::y() const
{ return yp; }

inline void ePoint::setX( int x )
{ xp = (int)x; }

inline void ePoint::setY( int y )
{ yp = (int)y; }

inline int &ePoint::rx()
{ return xp; }

inline int &ePoint::ry()
{ return yp; }

inline ePoint &ePoint::operator+=( const ePoint &p )
{ xp+=p.xp; yp+=p.yp; return *this; }

inline ePoint &ePoint::operator-=( const ePoint &p )
{ xp-=p.xp; yp-=p.yp; return *this; }

inline ePoint &ePoint::operator*=( int c )
{ xp*=(int)c; yp*=(int)c; return *this; }

inline ePoint &ePoint::operator*=( double c )
{ xp=(int)(xp*c); yp=(int)(yp*c); return *this; }

inline bool operator==( const ePoint &p1, const ePoint &p2 )
{ return p1.xp == p2.xp && p1.yp == p2.yp; }

inline bool operator!=( const ePoint &p1, const ePoint &p2 )
{ return p1.xp != p2.xp || p1.yp != p2.yp; }

inline ePoint operator+( const ePoint &p1, const ePoint &p2 )
{ return ePoint(p1.xp+p2.xp, p1.yp+p2.yp); }

inline ePoint operator-( const ePoint &p1, const ePoint &p2 )
{ return ePoint(p1.xp-p2.xp, p1.yp-p2.yp); }

inline ePoint operator+( const ePoint &p1, const eSize &p2 )
{ return ePoint(p1.xp+p2.width(), p1.yp+p2.height()); }

inline ePoint operator-( const ePoint &p1, const eSize &p2 )
{ return ePoint(p1.xp-p2.width(), p1.yp-p2.height()); }

inline ePoint operator*( const ePoint &p, int c )
{ return ePoint(p.xp*c, p.yp*c); }

inline ePoint operator*( int c, const ePoint &p )
{ return ePoint(p.xp*c, p.yp*c); }

inline ePoint operator*( const ePoint &p, double c )
{ return ePoint((int)(p.xp*c), (int)(p.yp*c)); }

inline ePoint operator*( double c, const ePoint &p )
{ return ePoint((int)(p.xp*c), (int)(p.yp*c)); }

inline ePoint operator-( const ePoint &p )
{ return ePoint(-p.xp, -p.yp); }

inline ePoint &ePoint::operator/=( int c )
{
	xp/=(int)c;
	yp/=(int)c;
	return *this;
}

inline ePoint &ePoint::operator/=( double c )
{
	xp=(int)(xp/c);
	yp=(int)(yp/c);
	return *this;
}

inline ePoint operator/( const ePoint &p, int c )
{
	return ePoint(p.xp/c, p.yp/c);
}

inline ePoint operator/( const ePoint &p, double c )
{
	return ePoint((int)(p.xp/c), (int)(p.yp/c));
}


#endif // EPOINT_H
