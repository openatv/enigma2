#ifndef __http_file_h
#define __http_file_h

#include "httpd.h"

class eHTTPFile: public eHTTPDataSource
{
	int fd, size;
	const char *mime;
	int method;
public:
	enum { methodGET, methodPUT };
	eHTTPFile(eHTTPConnection *c, int fd, int method, const char *mime);
	~eHTTPFile();
	int doWrite(int);
	void haveData(void *data, int len);
};

class eHTTPFilePathResolver: public eHTTPPathResolver
{
	struct eHTTPFilePath
	{
		std::string path;
		std::string root;
		int authorized; // must be authorized (1 means read, 2 write)
		eHTTPFilePath(std::string path, std::string root, int authorized): path(path), root(root), authorized(authorized)
		{
		}
	};
	ePtrList<eHTTPFilePath> translate;
public:
	eHTTPFilePathResolver();
	eHTTPDataSource *getDataSource(std::string request, std::string path, eHTTPConnection *conn);
	void addTranslation(std::string path, std::string root, int auth);
};

#endif
