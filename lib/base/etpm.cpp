#include <sys/socket.h>
#include <fcntl.h>
#include <stdbool.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <sys/un.h>
#include <unistd.h>
#include <openssl/bn.h>
#include <openssl/sha.h>
#include <lib/base/eerror.h>

#include "etpm.h"

eTPM::eTPM()
{
	struct sockaddr_un addr;
	unsigned char buf[8];
	unsigned int tag;
	size_t len;
	unsigned char *val;

	level2_cert_read = level3_cert_read = false;

	addr.sun_family = AF_UNIX;
	strcpy(addr.sun_path, TPMD_SOCKET);

	fd = socket(PF_UNIX, SOCK_STREAM, 0);
	if (fd < 0)
	{
		eDebug("[eTPM] socket error");
		return;
	}

	if (connect(fd, (const struct sockaddr *)&addr, SUN_LEN(&addr)) < 0)
	{
		eDebug("[eTPM] connect error");
		return;
	}

	buf[0] = TPMD_DT_LEVEL2_CERT;
	buf[1] = TPMD_DT_LEVEL3_CERT;
	if (!send_cmd(TPMD_CMD_GET_DATA, buf, 2))
	{
		return;
	}

	val = (unsigned char*)recv_cmd(&tag, &len);
	if (val == NULL)
	{
		return;
	}

	parse_data(val, len);
	free(val);
}

eTPM::~eTPM()
{

}

bool eTPM::send_cmd(enum tpmd_cmd cmd, const void *data, size_t len)
{
	unsigned char buf[len + 4];

	buf[0] = (cmd >> 8) & 0xff;
	buf[1] = (cmd >> 0) & 0xff;
	buf[2] = (len >> 8) & 0xff;
	buf[3] = (len >> 0) & 0xff;
	memcpy(&buf[4], data, len);

	if (write(fd, buf, sizeof(buf)) != (ssize_t)sizeof(buf))
	{
		fprintf(stderr, "%s: incomplete write\n", __func__);
		return false;
	}

	return true;
}

void* eTPM::recv_cmd(unsigned int *tag, size_t *len)
{
	unsigned char buf[4];
	void *val;

	if (read(fd, buf, 4) != 4)
	{
		fprintf(stderr, "%s: incomplete read\n", __func__);
		return NULL;
	}

	*tag = (buf[0] << 8) | buf[1];
	*len = (buf[2] << 8) | buf[3];

	val = malloc(*len);
	if (val == NULL)
		return NULL;

	ssize_t rd = read(fd, val, *len);
	if (rd < 0)
	{
		perror("eTPM::recv_cmd read");
		free(val);
	}
        else if ((size_t)rd != *len) {
		fprintf(stderr, "%s: incomplete read\n", __func__);
		free(val);
		return NULL;
	}

	return val;
}

void eTPM::parse_data(const unsigned char *data, size_t datalen)
{
	unsigned int i;
	unsigned int tag;
	unsigned int len;
	const unsigned char *val;

	for (i = 0; i < datalen; i += len) {
		tag = data[i++];
		len = data[i++];
		val = &data[i];

		switch (tag) {
		case TPMD_DT_LEVEL2_CERT:
			if (len != 210)
				break;
			memcpy(level2_cert, val, 210);
			level2_cert_read = true;
			break;
		case TPMD_DT_LEVEL3_CERT:
			if (len != 210)
				break;
			memcpy(level3_cert, val, 210);
			level3_cert_read = true;
			break;
		}
	}
}

std::string eTPM::getCert(cert_type type)
{
	if (type == TPMD_DT_LEVEL2_CERT && level2_cert_read)
		return std::string((char*)level2_cert, 210);
	else if (type == TPMD_DT_LEVEL3_CERT && level3_cert_read)
		return std::string((char*)level3_cert, 210);
	return "";
}

std::string eTPM::challenge(std::string rnd)
{
	if (rnd.length() == 8)
	{
		if (!send_cmd(TPMD_CMD_COMPUTE_SIGNATURE, rnd.c_str(), 8))
			return "";

		unsigned int tag;
		size_t len;
		unsigned char *val = (unsigned char*)recv_cmd(&tag, &len);

		if (tag != TPMD_CMD_COMPUTE_SIGNATURE)
			return "";

		std::string ret((char*)val, len);
		free(val);
		return ret;
	}
	return "";
}
