#include <lib/dvb/metaparser.h>
#include <lib/base/eerror.h>
#include <errno.h>

eDVBMetaParser::eDVBMetaParser()
{
	m_time_create = 0;
	m_data_ok = 0;
}

int eDVBMetaParser::parseFile(const std::string &basename)
{
		/* first, try parsing the .meta file */
	if (!parseMeta(basename))
		return 0;
	
		/* otherwise, use recordings.epl */
	return parseRecordings(basename);
}

int eDVBMetaParser::parseMeta(const std::string &tsname)
{
		/* if it's a PVR channel, recover service id. */
	std::string filename = tsname + ".meta";
		
	FILE *f = fopen(filename.c_str(), "r");
	if (!f)
		return -ENOENT;

	int linecnt = 0;
	
	m_time_create = 0;
	
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
			m_ref = eServiceReferenceDVB(line);
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
		case 4:
			m_tags = line;
			break;
		default:
			break;
		}
		++linecnt;
	}
	fclose(f);
	m_data_ok = 1;
	return 0;
}

int eDVBMetaParser::parseRecordings(const std::string &filename)
{
	std::string::size_type slash = filename.rfind('/');
	if (slash == std::string::npos)
		return -1;
	
	std::string recordings = filename.substr(0, slash) + "/recordings.epl";
	
	FILE *f = fopen(recordings.c_str(), "r");
	if (!f)
	{
//		eDebug("no recordings.epl found: %s: %m", recordings.c_str());
		return -1;
	}
	
	std::string description;
	eServiceReferenceDVB ref;
	
//	eDebug("parsing recordings.epl..");
	
	while (1)
	{
		char line[1024];
		if (!fgets(line, 1024, f))
			break;
		
		if (strlen(line))
			line[strlen(line)-1] = 0;
		
		if (strlen(line) && line[strlen(line)-1] == '\r')
			line[strlen(line)-1] = 0;
		
		if (!strncmp(line, "#SERVICE: ", 10))
			ref = eServiceReferenceDVB(line + 10);
		if (!strncmp(line, "#DESCRIPTION: ", 14))
			description = line + 14;

		if ((line[0] == '/') && (ref.path == filename))
		{
//			eDebug("hit! ref %s descr %s", m_ref.toString().c_str(), m_name.c_str());
			m_ref = ref;
			m_name = description;
			m_description = "";
			m_time_create = 0;
			
			m_data_ok = 1;
			fclose(f);
			return 0;
		}
	}
	fclose(f);
	return -1;
}

int eDVBMetaParser::updateMeta(const std::string &tsname)
{
	if (!m_data_ok)	
		return -1;
	std::string filename = tsname + ".meta";

	FILE *f = fopen(filename.c_str(), "w");
	if (!f)
		return -ENOENT;
	fprintf(f, "%s\n%s\n%s\n%d\n%s\n", m_ref.toString().c_str(), m_name.c_str(), m_description.c_str(), m_time_create, m_tags.c_str());
	fclose(f);
	return 0;
}
