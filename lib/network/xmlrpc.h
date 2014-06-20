#ifndef DISABLE_NETWORK

#ifndef __xmlrpc_h_
#define __xmlrpc_h_

#include <asm/types.h>
#include <map>
#include <vector>
#include <xmltree.h>

#include <string>
#include <lib/base/eptrlist.h>
#include <lib/network/httpd.h>

#define INSERT(KEY,VALUE) insert(std::pair<std::string, eXMLRPCVariant*>(KEY,VALUE))

class eXMLRPCVariant
{
	std::map<std::string,eXMLRPCVariant*> *_struct;
	std::vector<eXMLRPCVariant> *_array;
	__s32 *_i4;
	bool *_boolean;
	std::string *_string;
	double *_double;
//	QDateTime *_datetime;
//	QByteArray *_base64;
	void zero();
public:
	eXMLRPCVariant(std::map<std::string,eXMLRPCVariant*> *_struct);
	eXMLRPCVariant(std::vector<eXMLRPCVariant> *_array);
	eXMLRPCVariant(__s32 *_i4);
	eXMLRPCVariant(bool *_boolean);
	eXMLRPCVariant(std::string *_string);
	eXMLRPCVariant(double *_double);
//	eXMLRPCVariant(QDateTime *_datetime);
//	eXMLRPCVariant(QByteArray *_base64);
	eXMLRPCVariant(const eXMLRPCVariant &c);
	~eXMLRPCVariant();

	std::map<std::string,eXMLRPCVariant*> *getStruct();
	std::vector<eXMLRPCVariant> *getArray();
	__s32 *getI4();
	bool *getBoolean();
	std::string *getString();
	double *getDouble();
//	QDateTime *getDatetime();
//	QByteArray *getBase64();

	void toXML(std::string &);
};

class eXMLRPCResponse: public eHTTPDataSource
{
	XMLTreeParser parser;
	std::string result;
	int size;
	int wptr;
	int doCall();
public:
	eXMLRPCResponse(eHTTPConnection *c);
	~eXMLRPCResponse();

	int doWrite(int);
	void haveData(void *data, int len);
};

void xmlrpc_initialize(eHTTPD *httpd);
void xmlrpc_addMethod(const std::string& methodName, int (*)(std::vector<eXMLRPCVariant>&, ePtrList<eXMLRPCVariant>&));
void xmlrpc_fault(ePtrList<eXMLRPCVariant> &res, int faultCode, std::string faultString);
int xmlrpc_checkArgs(const std::string& args, std::vector<eXMLRPCVariant>&, ePtrList<eXMLRPCVariant> &res);

class eHTTPXMLRPCResolver: public iHTTPPathResolver
{
	DECLARE_REF(eHTTPXMLRPCResolver);
public:
	eHTTPXMLRPCResolver();
	eHTTPDataSource *getDataSource(const std::string& request, const std::string& path, eHTTPConnection *conn);
};

#endif

#endif //DISABLE_NETWORK
