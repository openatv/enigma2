#ifndef DISABLE_NETWORK

#include <lib/network/xmlrpc.h>
#include <lib/base/estring.h>


static std::map<std::string, int (*)(std::vector<eXMLRPCVariant>&, ePtrList<eXMLRPCVariant>&)> rpcproc;

void eXMLRPCVariant::zero()
{
	_struct=0;
	_array=0;
	_i4=0;
	_boolean=0;
	_string=0;
	_double=0;
//	_datetime=0;
//	_base64=0;
}

eXMLRPCVariant::eXMLRPCVariant(std::map<std::string,eXMLRPCVariant*> *__struct)
{
	zero();
	_struct=__struct;
}

eXMLRPCVariant::eXMLRPCVariant(std::vector<eXMLRPCVariant> *__array)
{
	zero();
	_array=__array;
}

eXMLRPCVariant::eXMLRPCVariant(__s32 *__i4)
{
	zero();
	_i4=__i4;
}

eXMLRPCVariant::eXMLRPCVariant(bool *__boolean)
{
	zero();
	_boolean=__boolean;
}

eXMLRPCVariant::eXMLRPCVariant(std::string *__string)
{
	zero();
	_string=__string;
}

eXMLRPCVariant::eXMLRPCVariant(double *__double)
{
	zero();
	_double=__double;
}

/*eXMLRPCVariant::eXMLRPCVariant(QDateTime *__datetime)
{
	zero();
	_datetime=__datetime;
} */

/*eXMLRPCVariant::eXMLRPCVariant(QByteArray *__base64)
{
	zero();
	_base64=__base64;
} */

eXMLRPCVariant::eXMLRPCVariant(const eXMLRPCVariant &c)
{
	zero();
	if (c._i4)
		_i4=new int(*c._i4);
	if (c._boolean)
		_boolean=new bool(*c._boolean);
	if (c._string)
		_string=new std::string(*c._string);
	if (c._double)
		_double=new double(*c._double);
	// datetime, base64
	if (c._struct)
	{
		_struct=new std::map<std::string,eXMLRPCVariant*>;
		for (std::map<std::string,eXMLRPCVariant*>::iterator b(c._struct->begin()); b != c._struct->end(); ++b)
			_struct->insert(std::pair<std::string,eXMLRPCVariant*>(b->first, new eXMLRPCVariant(*b->second)));
	}
	if (c._array)
		_array = new std::vector<eXMLRPCVariant>(*c._array);
}

eXMLRPCVariant::~eXMLRPCVariant()
{
	if (_struct)
	{
		for (std::map<std::string,eXMLRPCVariant*>::iterator i(_struct->begin()); i != _struct->end(); ++i)
			delete i->second;

		delete _struct;
	}
	if (_array)
		delete _array;
	if (_i4)
		delete _i4;
	if (_boolean)
		delete _boolean;
	if (_string)
		delete _string;
	if (_double)
		delete _string;
/*	if (_datetime)
		delete _datetime;*/
/*	if (_base64)
		delete _base64;*/
}

std::map<std::string,eXMLRPCVariant*> *eXMLRPCVariant::getStruct()
{
	return _struct;
}

std::vector<eXMLRPCVariant> *eXMLRPCVariant::getArray()
{
	return _array;
}

__s32 *eXMLRPCVariant::getI4()
{
	return _i4;
}

bool *eXMLRPCVariant::getBoolean()
{
	return _boolean;
}

std::string *eXMLRPCVariant::getString()
{
	return _string;
}

double *eXMLRPCVariant::getDouble()
{
	return _double;
}

/*QDateTime *eXMLRPCVariant::getDatetime()
{
	return _datetime;
} */

/*QByteArray *eXMLRPCVariant::getBase64()
{
	return _base64;
} */

void eXMLRPCVariant::toXML(std::string &result)
{
	if (getArray())
	{
		static std::string s1("<value><array><data>");
		result+=s1;
		for (unsigned int i=0; i<getArray()->size(); i++)
		{
			static std::string s("  ");
			result+=s;
			(*getArray())[i].toXML(result);
			static std::string s1("\n");
			result+=s1;
		}
		static std::string s2("</data></array></value>\n");
		result+=s2;
	} else if (getStruct())
	{
		static std::string s1("<value><struct>");
		result+=s1;
		for (std::map<std::string,eXMLRPCVariant*>::iterator i(_struct->begin()); i != _struct->end(); ++i)
		{
			static std::string s1("  <member><name>");
			result+=s1;
			result+=i->first;
			static std::string s2("</name>");
			result+=s2;
			i->second->toXML(result);
			static std::string s3("</member>\n");
			result+=s3;
		}
		static std::string s2("</struct></value>\n");
		result+=s2;
	} else if (getI4())
	{
		static std::string s1("<value><i4>");
		result+=s1;
		result+=getNum(*getI4());
		static std::string s2("</i4></value>");
		result+=s2;
	} else if (getBoolean())
	{
		static std::string s0("<value><boolean>0</boolean></value>");
		static std::string s1("<value><boolean>1</boolean></value>");
		result+=(*getBoolean())?s1:s0;
	} else if (getString())
	{
		static std::string s1("<value><string>");
		static std::string s2("</string></value>");
		result+=s1;
		result+=*getString();
		result+=s2;
	} else if (getDouble())
	{
//		result+=std::string().sprintf("<value><double>%lf</double></value>", *getDouble());
#warning double support removed
	}	else
		eFatal("[eXMLRPCVariant] couldn't append");
}

static eXMLRPCVariant *fromXML(XMLTreeNode *n)
{
	if (strcmp(n->GetType(), "value"))
		return 0;
	n=n->GetChild();
	const char *data=n->GetData();
	if (!data)
		data="";
	if ((!strcmp(n->GetType(), "i4")) || (!strcmp(n->GetType(), "int")))
		return new eXMLRPCVariant(new int(atoi(data)));
	else if (!strcmp(n->GetType(), "boolean"))
		return new eXMLRPCVariant(new bool(atoi(data)));
	else if (!strcmp(n->GetType(), "string"))
		return new eXMLRPCVariant(new std::string(data));
	else if (!strcmp(n->GetType(), "double"))
		return new eXMLRPCVariant(new double(atof(data)));
	else if (!strcmp(n->GetType(), "struct")) {
		std::map<std::string,eXMLRPCVariant*> *s=new std::map<std::string,eXMLRPCVariant*>;
		for (n=n->GetChild(); n; n=n->GetNext())
		{
			if (strcmp(data, "member"))
			{
				delete s;
				return 0;
			}
			std::string name("");
			eXMLRPCVariant *value;
			for (XMLTreeNode *v=n->GetChild(); v; v=v->GetNext())
			{
				if (!strcmp(v->GetType(), "name"))
					name=std::string(v->GetData());
				else if (!strcmp(v->GetType(), "value"))
					value=fromXML(v);
			}
			if ((!value) || name.empty())
			{
				delete s;
				return 0;
			}
			s->INSERT(name,value);
		}
		return new eXMLRPCVariant(s);
	} else if (!strcmp(n->GetType(), "array"))
	{
		ePtrList<eXMLRPCVariant> l;
		#warning autodelete removed
//		l.setAutoDelete(true);
		n=n->GetChild();
		if (strcmp(data, "data"))
			return 0;
		for (n=n->GetChild(); n; n=n->GetNext())
			if (!strcmp(n->GetType(), "value"))
			{
				eXMLRPCVariant *value=fromXML(n);
				if (!value)
					return 0;
				l.push_back(value);
			}

		return new eXMLRPCVariant( l.getVector() );
	}
	eDebug("[eXMLRPCVariant] couldn't convert %s", n->GetType());
	return 0;
}

eXMLRPCResponse::eXMLRPCResponse(eHTTPConnection *c):
	eHTTPDataSource(c), parser("ISO-8859-1")
{
	// size etc. setzen aber erst NACH data-phase
	connection->localstate=eHTTPConnection::stateWait;
}

eXMLRPCResponse::~eXMLRPCResponse()
{
}

int eXMLRPCResponse::doCall()
{
	eDebug("[eXMLRPCResponse] doing call");
	result="";
		// get method name
	std::string methodName("");

	if (connection->remote_header["Content-Type"]!="text/xml")
	{
		eDebug("[eXMLRPCResponse] remote header failure (%s != text/xml)", (connection->remote_header["Content-Type"]).c_str());
		return -3;
	}

	XMLTreeNode *methodCall=parser.RootNode();
	if (!methodCall)
	{
		eDebug("[eXMLRPCResponse] empty xml");
		return -1;
	}
	if (strcmp(methodCall->GetType(), "methodCall"))
	{
		eDebug("[eXMLRPCResponse] no methodCall found");
		return -2;
	}

	ePtrList<eXMLRPCVariant> params;
//	params.setAutoDelete(true);
#warning params autodelete remove

	for (XMLTreeNode *c=methodCall->GetChild(); c; c=c->GetNext())
	{
		if (!strcmp(c->GetType(), "methodName"))
			methodName=std::string(c->GetData());
		else if (!strcmp(c->GetType(), "params"))
		{
			for (XMLTreeNode *p=c->GetChild(); p; p=p->GetNext())
				if (!strcmp(p->GetType(), "param"))
					params.push_back(fromXML(p->GetChild()));
		} else
		{
			eDebug("[eXMLRPCResponse] unknown stuff found");
			return 0;
		}
	}

	if (methodName.empty())
	{
		eDebug("[eXMLRPCResponse] no methodName found!");
		return -3;
	}

	eDebug("[eXMLRPCResponse] methodName: %s", methodName.c_str() );

	result="<?xml version=\"1.0\"?>\n"
		"<methodResponse>";

	ePtrList<eXMLRPCVariant> ret;
//	ret.setAutoDelete(true);
#warning autodelete removed

	int (*proc)(std::vector<eXMLRPCVariant>&, ePtrList<eXMLRPCVariant> &)=rpcproc[methodName];
	int fault;

	std::vector<eXMLRPCVariant>* v = params.getVector();

	if (!proc)
	{
		fault=1;
		xmlrpc_fault(ret, -1, "called method not present");
	} else
		fault=proc( *v , ret);

	delete v;

	eDebug("[eXMLRPCResponse] converting to text...");

	if (fault)
	{
		result+="<fault>\n";
		ret.current()->toXML(result);
		result+="</fault>\n";
	} else
	{
		result+="<params>\n";
		for (ePtrList<eXMLRPCVariant>::iterator i(ret); i != ret.end(); ++i)
		{
			result+="<param>";
			i->toXML(result);
			result+="</param>";
		}
		result+="</params>";
	}
	result+="</methodResponse>";
	char buffer[10];
	snprintf(buffer, 10, "%d", size=result.length());
	wptr=0;
	connection->local_header["Content-Type"]="text/xml";
	connection->local_header["Content-Length"]=buffer;
	connection->code=200;
	connection->code_descr="OK";
	connection->localstate=eHTTPConnection::stateResponse;
	return 0;
}

int eXMLRPCResponse::doWrite(int hm)
{
	int tw=size-wptr;
	if (tw>hm)
		tw=hm;
	if (tw<=0)
		return -1;
	connection->writeBlock(result.c_str()+wptr, tw);
	wptr+=tw;
	return size > wptr ? 1 : -1;
}

void eXMLRPCResponse::haveData(void *data, int len)
{
	if (result)
		return;
	int err=0;

	if (!parser.Parse((char*)data, len, !len))
	{
		char temp[len+1];
		temp[len]=0;
		memcpy(temp, data, len);
		eDebug("[eXMLRPCResponse] %s: %s", temp, parser.ErrorString(parser.GetErrorCode()));
		err=1;
	}

	if ((!err) && (!len))
		err=doCall();

	if (err)
	{
		connection->code=400;
		connection->code_descr="Bad request";
		char buffer[10];
		snprintf(buffer, 10, "%d", size=result.length());
		wptr=0;
		connection->local_header["Content-Type"]="text/html";
		connection->local_header["Content-Length"]=buffer;
		result.sprintf("XMLRPC error %d\n", err);
		connection->localstate=eHTTPConnection::stateResponse;
	}
}

void xmlrpc_initialize(eHTTPD *httpd)
{
	httpd->addResolver(new eHTTPXMLRPCResolver);
}

void xmlrpc_addMethod(const std::string& methodName, int (*proc)(std::vector<eXMLRPCVariant>&, ePtrList<eXMLRPCVariant>&))
{
	rpcproc[methodName]=proc;
}

void xmlrpc_fault(ePtrList<eXMLRPCVariant> &res, int faultCode, std::string faultString)
{
	std::map<std::string,eXMLRPCVariant*> *s=new std::map<std::string,eXMLRPCVariant*>;
	s->INSERT("faultCode", new eXMLRPCVariant(new __s32(faultCode)));
	s->INSERT("faultString", new eXMLRPCVariant(new std::string(faultString)));
	res.push_back(new eXMLRPCVariant(s));
}

int xmlrpc_checkArgs(const std::string& args, std::vector<eXMLRPCVariant> &parm, ePtrList<eXMLRPCVariant> &res)
{
	if (parm.size() != args.length())
	{
	 	xmlrpc_fault(res, -500, std::string().sprintf("parameter count mismatch (found %d, expected %d)", parm.size(), args.length()));
		return 1;
	}

	for (unsigned int i=0; i<args.length(); i++)
	{
		switch (args[i])
		{
		case 'i':
			if (parm[i].getI4())
				continue;
			break;
		case 'b':
			if (parm[i].getBoolean())
				continue;
			break;
		case 's':
			if (parm[i].getString())
				continue;
			break;
		case 'd':
			if (parm[i].getDouble())
				continue;
			break;
/*		case 't':
			if (parm[i].getDatetime())
				continue;
			break;
		case '6':
			if (parm[i].getBase64())
				continue;
			break;*/
		case '$':
			if (parm[i].getStruct())
				continue;
			break;
		case 'a':
			if (parm[i].getArray())
				continue;
			break;
		}
		xmlrpc_fault(res, -501, std::string().sprintf("parameter type mismatch, expected %c as #%d", args[i], i));
		return 1;
	}
	return 0;
}

eHTTPXMLRPCResolver::eHTTPXMLRPCResolver()
{
}

eHTTPDataSource *eHTTPXMLRPCResolver::getDataSource(const std::string& request, const std::string& path, eHTTPConnection *conn)
{
	if ((path=="/RPC2") && (request=="POST"))
		return new eXMLRPCResponse(conn);
	if ((path=="/SID2") && (request=="POST"))
		return new eXMLRPCResponse(conn);
	return 0;
}

#endif //DISABLE_NETWORK
