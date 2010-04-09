#ifndef __lib_base_etpm_h
#define __lib_base_etpm_h

#include <lib/base/object.h>
#include <lib/python/python.h>

#ifndef SWIG
#define TPMD_SOCKET "/var/run/tpmd_socket"
#endif

class eTPM: public Object, public iObject
{
	DECLARE_REF(eTPM);
#ifndef SWIG
	int fd;
	unsigned char level2_cert[210];
	unsigned char level3_cert[210];
	bool level2_cert_read;
	bool level3_cert_read;

	enum tpmd_cmd {
		TPMD_CMD_RESERVED		= 0x0000,
		TPMD_CMD_GET_DATA		= 0x0001,
		TPMD_CMD_APDU			= 0x0002,
		TPMD_CMD_COMPUTE_SIGNATURE	= 0x0003,
		TPMD_CMD_APP_CERT		= 0x0004,
	};

	bool send_cmd(enum tpmd_cmd cmd, const void *data, unsigned int len);
	void *recv_cmd(unsigned int *tag, unsigned int *len);
	void parse_data(const unsigned char *data, unsigned int datalen);

#endif
public:
	eTPM();
	~eTPM();

	enum cert_type {
		TPMD_DT_LEVEL2_CERT = 0x04,
		TPMD_DT_LEVEL3_CERT = 0x05
	};
	PyObject *getCert(cert_type type);
	PyObject *challenge(PyObject *rnd);
};

#endif // __lib_base_etpm_h
