#include <cmath>

/*----------------------------------------------------------------------------*/
double factorial_div( double value, int x)
{
	if(!x)
		return 1;
	else
	{
		while( x > 1)
		{
			value = value / x--;
		}
	}
	return value;
}

/*----------------------------------------------------------------------------*/
double powerd( double x, int y)
{
	int i=0;
	double ans=1.0;

	if(!y)
		return 1.000;
	else
	{
		while( i < y)
		{
			i++;
			ans = ans * x;
		}
	}
	return ans;
}

/*----------------------------------------------------------------------------*/
double SIN( double x)
{
	int i=0;
	int j=1;
	int sign=1;
	double y1 = 0.0;
	double diff = 1000.0;

	if (x < 0.0)
	{
		x = -1 * x;
		sign = -1;
	}

	while ( x > 360.0*M_PI/180)
	{
		x = x - 360*M_PI/180;
	}

	if( x > (270.0 * M_PI / 180) )
	{
		sign = sign * -1;
		x = 360.0*M_PI/180 - x;
	}
	else if ( x > (180.0 * M_PI / 180) )
	{
		sign = sign * -1;
		x = x - 180.0 *M_PI / 180;
	}
	else if ( x > (90.0 * M_PI / 180) )
	{
		x = 180.0 *M_PI / 180 - x;
	}

	while( powerd( diff, 2) > 1.0E-16 )
	{
		i++;
		diff = j * factorial_div( powerd( x, (2*i -1)) ,(2*i -1));
		y1 = y1 + diff;
		j = -1 * j;
	}
	return ( sign * y1 );
}

/*----------------------------------------------------------------------------*/
double COS(double x)
{
	return SIN(90 * M_PI / 180 - x);
}

/*----------------------------------------------------------------------------*/
double ATAN( double x)
{
	int i=0; /* counter for terms in binomial series */
	int j=1; /* sign of nth term in series */
	int k=0;
	int sign = 1; /* sign of the input x */
	double y = 0.0; /* the output */
	double deltay = 1.0; /* the value of the next term in the series */
	double addangle = 0.0; /* used if arctan > 22.5 degrees */

	if (x < 0.0)
	{
		x = -1 * x;
		sign = -1;
	}

	while( x > 0.3249196962 )
	{
		k++;
		x = (x - 0.3249196962) / (1 + x * 0.3249196962);
	}

	addangle = k * 18.0 *M_PI/180;

	while( powerd( deltay, 2) > 1.0E-16 )
	{
		i++;
		deltay = j * powerd( x, (2*i -1)) / (2*i -1);
		y = y + deltay;
		j = -1 * j;
	}
	return (sign * (y + addangle) );
}

double ASIN(double x)
{
	return 2 * ATAN( x / (1 + std::sqrt(1.0 - x*x)));
}

double Radians( double number )
{
	return number*M_PI/180;
}

double Deg( double number )
{
	return number*180/M_PI;
}

double Rev( double number )
{
	return number - std::floor( number / 360.0 ) * 360;
}

#define		f	(1.00 / 298.257) // Earth flattning factor
#define		r_sat	42164.57 // Distance from earth centre to satellite
#define		r_eq	6378.14  // Earth radius

#define		a0	 0.58804392
#define		a1	-0.17941557
#define		a2	 0.29906946E-1
#define		a3	-0.25187400E-2
#define		a4	 0.82622101E-4

double calcElevation( double SatLon, double SiteLat, double SiteLon, int Height_over_ocean = 0 )
{
	double	sinRadSiteLat=SIN(Radians(SiteLat)),
		cosRadSiteLat=COS(Radians(SiteLat)),

		Rstation = r_eq / ( std::sqrt( 1.00 - f*(2.00-f)*sinRadSiteLat*sinRadSiteLat ) ),

		Ra = (Rstation+Height_over_ocean)*cosRadSiteLat,
		Rz= Rstation*(1.00-f)*(1.00-f)*sinRadSiteLat,

		alfa_rx=r_sat*COS(Radians(SatLon-SiteLon)) - Ra,
		alfa_ry=r_sat*SIN(Radians(SatLon-SiteLon)),
		alfa_rz=-Rz,

		alfa_r_north=-alfa_rx*sinRadSiteLat + alfa_rz*cosRadSiteLat,
		alfa_r_zenith=alfa_rx*cosRadSiteLat + alfa_rz*sinRadSiteLat,

		den = alfa_r_north*alfa_r_north+alfa_ry*alfa_ry,
		El_geometric = 90.0,

		x,
		refraction,
		El_observed = 0.00;

	if (den > 0.0)
		El_geometric=Deg(ATAN( alfa_r_zenith/std::sqrt(den)));

	x = std::fabs(El_geometric+0.589);
	refraction=std::fabs(a0 + (a1 + (a2 + (a3 + a4 * x) * x) * x) * x);

	if (El_geometric > 10.2)
		El_observed = El_geometric+0.01617*(COS(Radians(std::fabs(El_geometric)))/SIN(Radians(std::fabs(El_geometric))) );
	else
		El_observed = El_geometric+refraction;

	if (alfa_r_zenith < -3000)
		El_observed=-99;

	return El_observed;
}

double calcAzimuth(double SatLon, double SiteLat, double SiteLon, int Height_over_ocean=0)
{
	double	sinRadSiteLat=SIN(Radians(SiteLat)),
		cosRadSiteLat=COS(Radians(SiteLat)),

		Rstation = r_eq / ( std::sqrt( 1 - f*(2-f)*sinRadSiteLat*sinRadSiteLat ) ),
		Ra = (Rstation+Height_over_ocean)*cosRadSiteLat,
		Rz = Rstation*(1-f)*(1-f)*sinRadSiteLat,

		alfa_rx = r_sat*COS(Radians(SatLon-SiteLon)) - Ra,
		alfa_ry = r_sat*SIN(Radians(SatLon-SiteLon)),
		alfa_rz = -Rz,
		alfa_r_north = -alfa_rx*sinRadSiteLat + alfa_rz*cosRadSiteLat,
		Azimuth;

	if (alfa_r_north < 0)
		Azimuth = 180+Deg(ATAN(alfa_ry/alfa_r_north));
	else if (alfa_r_north > 0)
		Azimuth = Rev(360+Deg(ATAN(alfa_ry/alfa_r_north)));
	else
		Azimuth = 0.00;
	return Azimuth;
}

double calcDeclination( double SiteLat, double Azimuth, double Elevation)
{
	return Deg( ASIN( SIN(Radians(Elevation)) * SIN(Radians(SiteLat)) +
			COS(Radians(Elevation)) * COS(Radians(SiteLat)) +
			COS(Radians(Azimuth))
			)
		);
}

double calcSatHourangle( double SatLon, double SiteLat, double SiteLon )
{
	double	Azimuth=calcAzimuth(SatLon, SiteLat, SiteLon ),
		Elevation=calcElevation( SatLon, SiteLat, SiteLon ),

		a = - COS(Radians(Elevation)) * SIN(Radians(Azimuth)),
		b = SIN(Radians(Elevation)) * COS(Radians(SiteLat)) -
			COS(Radians(Elevation)) * SIN(Radians(SiteLat)) * COS(Radians(Azimuth)),

// Works for all azimuths (northern & southern hemisphere)
		returnvalue = 180 + Deg(ATAN(a/b));

	if ( Azimuth > 270 )
	{
		returnvalue += 180;
		if (returnvalue>360)
			returnvalue = 720 - returnvalue;
	}

	if ( Azimuth < 90 )
		returnvalue = ( 180 - returnvalue );

	return returnvalue;
}
