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

	unsigned char val[2*210 + 2*4];
	len = sizeof(val);
	tag = recv_cmd(val, &len);
	if (tag == 0xFFFFFFFF)
	{
		return;
	}
	parse_data(val, len);
}

eTPM::~eTPM()
{
	if (fd >= 0)
		close(fd);
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

unsigned int eTPM::recv_cmd(void *data, size_t *len)
{
	unsigned char buf[4];

	if (read(fd, buf, 4) != 4)
	{
		fprintf(stderr, "%s: incomplete read\n", __func__);
		return 0xFFFFFFFF;
	}

	unsigned int tag = (buf[0] << 8) | buf[1];
	unsigned int rlen = (buf[2] << 8) | buf[3];
	if (rlen > *len)
		rlen = *len;

	ssize_t rd = read(fd, data, rlen);
	if (rd < 0)
	{
		perror("eTPM::recv_cmd read");
	}
        else if ((unsigned int)rd != rlen) {
		fprintf(stderr, "%s: incomplete read\n", __func__);
		return 0xFFFFFFFF;
	}
	*len = rlen;
	return tag;
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
			break;
		case TPMD_DT_LEVEL3_CERT:
			if (len != 210)
				break;
			memcpy(level3_cert, val, 210);
			break;
		}
	}
}

std::string eTPM::getCert(cert_type type)
{
	switch (type)
	{
		case TPMD_DT_LEVEL2_CERT:
			return std::string((char*)level2_cert, 210);
		case TPMD_DT_LEVEL3_CERT:
			return std::string((char*)level3_cert, 210);
		default:
			return "";
	}
}

std::string eTPM::challenge(std::string rnd)
{
	if (rnd.length() == 8)
	{
		send_cmd(TPMD_CMD_COMPUTE_SIGNATURE, rnd.c_str(), 8);
		unsigned char val[80+8];
		memcpy(val+80, rnd.data(), 8);
		size_t len = sizeof(val);
		unsigned int tag = (unsigned char*)recv_cmd(val, &len);
		return std::string((char*)val, len);
	}
	return "";
}
