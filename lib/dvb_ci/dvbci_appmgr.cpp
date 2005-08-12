/* DVB CI Application Manager */

#include <lib/dvb_ci/dvbci_appmgr.h>

int eDVBCIApplicationManagerSession::receivedAPDU(const unsigned char *tag,const void *data, int len)
{
	printf("SESSION(%d)/APP %02x %02x %02x: ", session_nb, tag[0], tag[1], tag[2]);
	for (int i=0; i<len; i++)
		printf("%02x ", ((const unsigned char*)data)[i]);
	printf("\n");

	if ((tag[0]==0x9f) && (tag[1]==0x80))
	{
		switch (tag[2])
		{
		case 0x21:
		{
			int dl;
			printf("application info:\n");
			printf("  len: %d\n", len);
			printf("  application_type: %d\n", ((unsigned char*)data)[0]);
			printf("  application_manufacturer: %02x %02x\n", ((unsigned char*)data)[2], ((unsigned char*)data)[1]);
			printf("  manufacturer_code: %02x %02x\n", ((unsigned char*)data)[4],((unsigned char*)data)[3]);
			printf("  menu string: ");
			dl=((unsigned char*)data)[5];
			if ((dl + 6) > len)
			{
				printf("warning, invalid length (%d vs %d)\n", dl+6, len);
				dl=len-6;
			}
			for (int i = 0; i < dl; ++i)
				printf("%c", ((unsigned char*)data)[i+6]);
			printf("\n");
			break;
		}
		default:
			printf("unknown APDU tag 9F 80 %02x\n", tag[2]);
			break;
		}
	}
	return 0;
}
