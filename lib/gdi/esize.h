#ifndef ESIZE_H
#define ESIZE_H

#define MIN(a,b) (a < b ? a : b)
#define MAX(a,b) (a > b ? a : b)

class eSize
{
public:
	eSize();
	eSize( int w, int h );

	bool isNull()	const;
	bool isEmpty()	const;
	bool isValid()	const;

	int width()	const;
	int height()	const;
	void setWidth( int w );
	void setHeight( int h );
	void transpose();

	eSize expandedTo( const eSize & ) const;
	eSize boundedTo( const eSize & ) const;

	int &rwidth();
	int &rheight();

	eSize &operator+=( const eSize & );
	eSize &operator-=( const eSize & );
	eSize &operator*=( int c );
	eSize &operator*=( double c );
	eSize &operator/=( int c );
	eSize &operator/=( double c );

	friend inline bool	operator==( const eSize &, const eSize & );
	friend inline bool	operator!=( const eSize &, const eSize & );
	friend inline eSize operator+( const eSize &, const eSize & );
	friend inline eSize operator-( const eSize &, const eSize & );
	friend inline eSize operator*( const eSize &, int );
	friend inline eSize operator*( int, const eSize & );
	friend inline eSize operator*( const eSize &, double );
	friend inline eSize operator*( double, const eSize & );
	friend inline eSize operator/( const eSize &, int );
	friend inline eSize operator/( const eSize &, double );

private:
    int wd;
    int ht;
};


/*****************************************************************************
  eSize inline functions
 *****************************************************************************/

inline eSize::eSize()
{ wd = ht = -1; }

inline eSize::eSize( int w, int h )
{ wd=w; ht=h; }

inline bool eSize::isNull() const
{ return wd==0 && ht==0; }

inline bool eSize::isEmpty() const
{ return wd<1 || ht<1; }

inline bool eSize::isValid() const
{ return wd>=0 && ht>=0; }

inline int eSize::width() const
{ return wd; }

inline int eSize::height() const
{ return ht; }

inline void eSize::setWidth( int w )
{ wd=w; }

inline void eSize::setHeight( int h )
{ ht=h; }

inline int &eSize::rwidth()
{ return wd; }

inline int &eSize::rheight()
{ return ht; }

inline eSize &eSize::operator+=( const eSize &s )
{ wd+=s.wd; ht+=s.ht; return *this; }

inline eSize &eSize::operator-=( const eSize &s )
{ wd-=s.wd; ht-=s.ht; return *this; }

inline eSize &eSize::operator*=( int c )
{ wd*=c; ht*=c; return *this; }

inline eSize &eSize::operator*=( double c )
{ wd=(int)(wd*c); ht=(int)(ht*c); return *this; }

inline bool operator==( const eSize &s1, const eSize &s2 )
{ return s1.wd == s2.wd && s1.ht == s2.ht; }

inline bool operator!=( const eSize &s1, const eSize &s2 )
{ return s1.wd != s2.wd || s1.ht != s2.ht; }

inline eSize operator+( const eSize & s1, const eSize & s2 )
{ return eSize(s1.wd+s2.wd, s1.ht+s2.ht); }

inline eSize operator-( const eSize &s1, const eSize &s2 )
{ return eSize(s1.wd-s2.wd, s1.ht-s2.ht); }

inline eSize operator*( const eSize &s, int c )
{ return eSize(s.wd*c, s.ht*c); }

inline eSize operator*( int c, const eSize &s )
{  return eSize(s.wd*c, s.ht*c); }

inline eSize operator*( const eSize &s, double c )
{ return eSize((int)(s.wd*c), (int)(s.ht*c)); }

inline eSize operator*( double c, const eSize &s )
{ return eSize((int)(s.wd*c), (int)(s.ht*c)); }

inline eSize &eSize::operator/=( int c )
{
	wd/=c; ht/=c;
	return *this;
}

inline eSize &eSize::operator/=( double c )
{
	wd=(int)(wd/c); ht=(int)(ht/c);
	return *this;
}

inline eSize operator/( const eSize &s, int c )
{
	return eSize(s.wd/c, s.ht/c);
}

inline eSize operator/( const eSize &s, double c )
{
	return eSize((int)(s.wd/c), (int)(s.ht/c));
}

inline eSize eSize::expandedTo( const eSize & otherSize ) const
{
	return eSize( MAX(wd,otherSize.wd), MAX(ht,otherSize.ht) );
}

inline eSize eSize::boundedTo( const eSize & otherSize ) const
{
	return eSize( MIN(wd,otherSize.wd), MIN(ht,otherSize.ht) );
}

inline void eSize::transpose()
{
	int tmp = wd;
	wd = ht;
	ht = tmp;
}

#endif // ESIZE_H
