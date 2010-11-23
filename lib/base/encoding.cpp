#include <cstdio>
#include <cstdlib>
#include <lib/base/encoding.h>
#include <lib/base/eerror.h>
#include <lib/base/eenv.h>

eDVBTextEncodingHandler encodingHandler;  // the one and only instance

inline char toupper(char c)
{
	switch (c)
	{
		case 'a' ... 'z':
			return c-32;
	}
	return c;
}

eDVBTextEncodingHandler::eDVBTextEncodingHandler()
{
	std::string file = eEnv::resolve("${datadir}/enigma2/encoding.conf");
	FILE *f = fopen(file.c_str(), "rt");
	if (f)
	{
		char *line = (char*) malloc(256);
		size_t bufsize=256;
		char countrycode[256];
		while( getline(&line, &bufsize, f) != -1 )
		{
			if ( line[0] == '#' )
				continue;
			int tsid, onid, encoding;
			if ( (sscanf( line, "0x%x 0x%x ISO8859-%d", &tsid, &onid, &encoding ) == 3 )
					||(sscanf( line, "%d %d ISO8859-%d", &tsid, &onid, &encoding ) == 3 ) )
				m_TransponderDefaultMapping[(tsid<<16)|onid]=encoding;
			else if ( sscanf( line, "%s ISO8859-%d", countrycode, &encoding ) == 2 )
			{
				m_CountryCodeDefaultMapping[countrycode]=encoding;
				countrycode[0]=toupper(countrycode[0]);
				countrycode[1]=toupper(countrycode[1]);
				countrycode[2]=toupper(countrycode[2]);
				m_CountryCodeDefaultMapping[countrycode]=encoding;
			}
			else if ( (sscanf( line, "0x%x 0x%x ISO%d", &tsid, &onid, &encoding ) == 3 && encoding == 6397 )
					||(sscanf( line, "%d %d ISO%d", &tsid, &onid, &encoding ) == 3 && encoding == 6397 ) )
				m_TransponderDefaultMapping[(tsid<<16)|onid]=0;
			else if ( sscanf( line, "%s ISO%d", countrycode, &encoding ) == 2 && encoding == 6397 )
			{
				m_CountryCodeDefaultMapping[countrycode]=0;
				countrycode[0]=toupper(countrycode[0]);
				countrycode[1]=toupper(countrycode[1]);
				countrycode[2]=toupper(countrycode[2]);
				m_CountryCodeDefaultMapping[countrycode]=0;
			}
			else if ( (sscanf( line, "0x%x 0x%x", &tsid, &onid ) == 2 )
					||(sscanf( line, "%d %d", &tsid, &onid ) == 2 ) )
				m_TransponderUseTwoCharMapping.insert((tsid<<16)|onid);
			else
				eDebug("couldn't parse %s", line);
		}
		fclose(f);
		free(line);
	}
	else
		eDebug("[eDVBTextEncodingHandler] couldn't open %s !", file.c_str());
}

void eDVBTextEncodingHandler::getTransponderDefaultMapping(int tsidonid, int &table)
{
	std::map<int, int>::iterator it =
		m_TransponderDefaultMapping.find(tsidonid);
	if ( it != m_TransponderDefaultMapping.end() )
		table = it->second;
}

bool eDVBTextEncodingHandler::getTransponderUseTwoCharMapping(int tsidonid)
{
	return m_TransponderUseTwoCharMapping.find(tsidonid) != m_TransponderUseTwoCharMapping.end();
}

int eDVBTextEncodingHandler::getCountryCodeDefaultMapping( const std::string &country_code )
{
	std::map<std::string, int>::iterator it =
		m_CountryCodeDefaultMapping.find(country_code);
	if ( it != m_CountryCodeDefaultMapping.end() )
		return it->second;
	return 1;  // ISO8859-1 / Latin1
}
