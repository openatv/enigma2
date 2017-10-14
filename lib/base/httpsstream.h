#ifndef __lib_base_httpsstream_h
#define __lib_base_httpsstream_h

#include <string>
#include <lib/base/ebase.h>
#include <lib/base/itssource.h>
#include <lib/base/thread.h>

#include <openssl/bio.h>
#include <openssl/ssl.h>
#include <openssl/err.h>

class eHttpsStream: public iTsSource, public sigc::trackable, public eThread
{
	DECLARE_REF(eHttpsStream);

	int streamSocket;
	enum { BUSY, CONNECTED, FAILED } connectionStatus;
	bool isChunked;
	size_t currentChunkSize;
	std::string streamUrl;
	std::string authorizationData;
	char partialPkt[192];
	size_t partialPktSz;
	char* tmpBuf;
	size_t tmpBufSize;

	int openUrl(const std::string &url, std::string &newurl);
	void thread();
	ssize_t httpChunkedRead(void *buf, size_t count);
	ssize_t syncNextRead(void *buf, ssize_t count);

	/* iTsSource */
	ssize_t read(off_t offset, void *buf, size_t count);
	off_t length();
	off_t offset();
	int valid();
	bool isStream() { return true; };

	/* OpenSSL More Info https://wiki.openssl.org/index.php/SSL/TLS_Client */
	SSL_CTX *ctx;
	SSL *ssl;
	SSL_CTX* initCTX();
	void showCerts(SSL *ssl);
	ssize_t SSL_writeAll(SSL *ssl, const void *buf, size_t count);
	ssize_t SSL_singleRead(SSL *ssl, void *buf, size_t count);
	ssize_t SSL_readLine(SSL *ssl, char** buffer, size_t* bufsize);
public:
	eHttpsStream();
	~eHttpsStream();
	int open(const char *url);
	int close();
};

#endif
