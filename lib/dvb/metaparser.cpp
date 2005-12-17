#include <lib/dvb/metaparser.h>
#include <errno.h>

int eDVBMetaParser::parseFile(const std::string &tsname)
{
		/* if it's a PVR channel, recover service id. */
	std::string filename = tsname + ".meta";
		
	FILE *f = fopen(filename.c_str(), "r");
	if (!f)
		return -ENOENT;

	int linecnt = 0;
	
	while (1)
	{
		char line[1024];
		if (!fgets(line, 1024, f))
			break;
		if (*line && line[strlen(line)-1] == '\n')
			line[strlen(line)-1] = 0;

 		if (*line && line[strlen(line)-1] == '\r')
			line[strlen(line)-1] = 0;

		switch (linecnt)
		{
		case 0:
			m_ref = (const eServiceReferenceDVB&)eServiceReference(line);
			break;
		case 1:
			m_name = line;
			break;
		case 2:
			m_description = line;
			break;
		case 3:
			m_time_create = atoi(line);
			break;
		default:
			break;
		}
		++linecnt;
	}
	fclose(f);
	return 0;
}
