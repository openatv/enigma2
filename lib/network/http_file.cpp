#include <lib/network/http_file.h>
#include <unistd.h>
#include <fcntl.h>
#include <errno.h>
#include <string>
#include <shadow.h>
#include <pwd.h>

eHTTPFile::eHTTPFile(eHTTPConnection *c, int _fd, int method, const char *mime): eHTTPDataSource(c), method(method)
{
	fd=_fd;
	if (method == methodGET)
	{
		c->local_header["Content-Type"]=std::string(mime);
		size=lseek(fd, 0, SEEK_END);
		char asize[10];
		snprintf(asize, 10, "%d", size);
		lseek(fd, 0, SEEK_SET);
		c->local_header["Content-Length"]=std::string(asize);
	}
	connection->code_descr="OK";
	connection->code=200;
}

int eHTTPFile::doWrite(int bytes)
{
	if (method == methodGET)
	{
		char buff[bytes];
		if (!size)
			return -1;
		int len=bytes;
		if (len>size)
			len=size;
		len=read(fd, buff, len);
		if (len<=0)
			return -1;
		size-=connection->writeBlock(buff, len);
		if (!size)
			return -1;
		else
			return 1;
	} else
		return -1;
}

void eHTTPFile::haveData(void *data, int len)
{
	if (method != methodPUT)
		return;
	::write(fd, data, len);
}

eHTTPFile::~eHTTPFile()
{
	close(fd);
}

eHTTPFilePathResolver::eHTTPFilePathResolver()
{
#warning autodelete removed
}


static char _base64[]="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=";

static int unbase64(eString &dst, const eString string)
{
	dst="";
	char c[4];
	int pos=0;
	unsigned int i=0;
	
	while (1)
	{
		if (i == string.size())
			break;
		char *ch=strchr(_base64, string[i++]);
		if (!ch)
		{
			i++;
			continue;
		}
		c[pos++]=ch-_base64;
		if (pos == 4)
		{
			char d[3];
			d[0]=c[0]<<2;
			d[0]|=c[1]>>4;
			d[1]=c[1]<<4;
			d[1]|=c[2]>>2;
			d[2]=c[2]<<6;
			d[2]|=c[3];
			
			dst+=d[0];
			if (c[2] != 64)
				dst+=d[1];
			if (c[3] != 64)
				dst+=d[2];
			pos=0;
		}
	}
	return pos;
}

int CheckUnixPassword(const char *user, const char *pass)
{
	passwd *pwd=getpwnam(user);
	if (!pwd)
		return -1;
	char *cpwd=pwd->pw_passwd;
	if (pwd && (!strcmp(pwd->pw_passwd, "x")))
	{
		spwd *sp=getspnam(user);
		if (!sp)						// no shadow password defined.
			return -1;
		cpwd=sp->sp_pwdp;
	}
	if (!cpwd)
		return -1;
	if ((*cpwd=='!')||(*cpwd=='*'))		 // disabled user
		return -2;
	char *cres=crypt(pass, cpwd);
	return !!strcmp(cres, cpwd);
}

static int checkAuth(const eString cauth)
{
	eString auth;
	if (cauth.left(6) != "Basic ")
		return -1;
	if (unbase64(auth, cauth.mid(6)))
		return -1;
	eString username=auth.left(auth.find(":"));
	eString password=auth.mid(auth.find(":")+1);
	if (CheckUnixPassword(username.c_str(), password.c_str()))
		return -1;
	return 0;
}

eHTTPDataSource *eHTTPFilePathResolver::getDataSource(eString request, eString path, eHTTPConnection *conn)
{
	int method;
	eDebug("request = %s, path = %s", request.c_str(), path.c_str());
	if (request == "GET")
		method=eHTTPFile::methodGET;
	else if (request == "PUT")
		method=eHTTPFile::methodPUT;
	else
		return new eHTTPError(conn, 405); // method not allowed
	if (path.find("../")!=eString::npos)		// evil hax0r
		return new eHTTPError(conn, 403);
	if (path[0] != '/')		// prepend '/'
		path.insert(0,"/");
	if (path[path.length()-1]=='/')
		path+="index.html";
	
	eHTTPDataSource *data=0;
	for (ePtrList<eHTTPFilePath>::iterator i(translate); i != translate.end(); ++i)
	{
		if (i->root==path.left(i->root.length()))
		{
			eString newpath=i->path+path.mid(i->root.length());
			if (newpath.find('?'))
				newpath=newpath.left(newpath.find('?'));
			eDebug("translated %s to %s", path.c_str(), newpath.c_str());

			if (i->authorized & ((method==eHTTPFile::methodGET)?1:2))
			{
				std::map<std::string, std::string>::iterator i=conn->remote_header.find("Authorization");
				if ((i == conn->remote_header.end()) || checkAuth(i->second))
				{
					conn->local_header["WWW-Authenticate"]="Basic realm=\"dreambox\"";
					return new eHTTPError(conn, 401); // auth req'ed
				}
			}

			int fd=open(newpath.c_str(), (method==eHTTPFile::methodGET)?O_RDONLY:(O_WRONLY|O_CREAT|O_TRUNC), 0644);

			if (fd==-1)
			{
				switch (errno)
				{
				case ENOENT:
					data=new eHTTPError(conn, 404);
					break;
				case EACCES:
					data=new eHTTPError(conn, 403);
					break;
				default:
					data=new eHTTPError(conn, 403); // k.a.
					break;
				}
				break;
			}
			
			eString ext=path.mid(path.rfind('.'));
			const char *mime="text/unknown";
			if ((ext==".html") || (ext==".htm"))
				mime="text/html";
			else if ((ext==".jpeg") || (ext==".jpg"))
				mime="image/jpeg";
			else if (ext==".gif")
				mime="image/gif";
			else if (ext==".css")
				mime="text/css";
			else if (ext==".png")
				mime="image/png";
			else if (ext==".xml")
				mime="text/xml";
			else if (ext==".xsl")
				mime="text/xsl";

			data=new eHTTPFile(conn, fd, method, mime);
			break;
		}
	}
	return data;
}

void eHTTPFilePathResolver::addTranslation(eString path, eString root, int authorized)
{
	if (path[path.length()-1]!='/')
		path+='/';
	if (root[root.length()-1]!='/')
		root+='/';
	translate.push_back(new eHTTPFilePath(path, root, authorized));
}
