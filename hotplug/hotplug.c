/*
Copyright (c) 2024-2026 jbleyel

This code may be used commercially. Attribution must be given to the original author.
Licensed under GPLv2.

This file also contains the previous code of
https://github.com/OpenPLi/hotplug-e2-helper
based on multiple authors.
*/


#include <fcntl.h>
#include <netdb.h>
#include <netinet/in.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/types.h>
#include <sys/un.h>
#include <unistd.h>

/// @brief Replaces all occurrences of a character in a string with another character.
/// @param str The string in which to replace characters.
/// @param orig The character to be replaced in the string.
/// @param rep The character to replace the original character with.
/// @return The number of characters replaced in the string.
int replacechar(char* str, char orig, char rep) {
	char* ix = str;
	int n = 0;
	while ((ix = strchr(ix, orig)) != NULL) {
		*ix++ = rep;
		n++;
	}
	return n;
}

/// @brief Get device size from environment or sysfs
/// @param devpath Device path for sysfs lookup
/// @param devsize Output buffer for size string (must be at least 50 bytes)
static void get_device_size(const char* devpath, char* devsize) {
	const char* part_entry_size = getenv("ID_PART_ENTRY_SIZE");
	if (part_entry_size) {
		snprintf(devsize, 50 - 1, "%s", part_entry_size);
	} else {
		long ldevsize = 0;
		FILE* f;
		char fn[255];
		snprintf(fn, sizeof(fn) - 1, "/sys%s/size", devpath);
		f = fopen(fn, "r");
		if (f) {
			if (fscanf(f, "%ld", &ldevsize) != 1)
				ldevsize = 0;
			fclose(f);
		}
		snprintf(devsize, 50 - 1, "%ld", ldevsize);
	}
}

/// @brief Write data to temporary file with normalized device name
/// @param devname Device name to normalize
/// @param data Data to write
/// @param debug Debug flag
static void write_data_to_file(const char* devname, const char* data, int debug) {
	if (debug)
		printf("%s\n", data);

	char devpathnorm[255];
	snprintf(devpathnorm, sizeof(devpathnorm), "%s", devname);
	devpathnorm[sizeof(devpathnorm) - 1] = '\0';
	replacechar(devpathnorm, '/', '_');

	char fn[280];
	snprintf(fn, sizeof(fn), "/tmp/hotplug%s", devpathnorm);

	FILE* f = fopen(fn, "w");
	if (f) {
		fprintf(f, "%s\n", data);
		fclose(f);
	}
}

/// @brief Send data or write to file based on mode
static void send_to_socket(int sd, int mode, int debug, char* data, int len, size_t datalen) {
	if (debug)
		printf("%s\n", data);
	if (mode == 1) {
		if ((size_t)len >= datalen)
			len = (int)datalen - 1;
		send(sd, data, (size_t)len + 1U, 0);
	}
}

/// @brief Main entry point - handles device hotplug events via socket or file
/// @param argc Argument count
/// @param argv Argument vector
/// @return 0 on success, 1 on invalid arguments
int main(int argc, char* argv[]) {
	const char *action = NULL, *devpath = NULL, *physdevpath = NULL;
	int sd = -1;
	struct sockaddr_un serv_addr_un;

	int mode = 0;
	int debug = 0;

	if (argc == 3) {
		action = argv[1];
		devpath = argv[2];
		mode = 1;
	} else if (argc > 3) {
		action = argv[1];
		devpath = argv[2];
		physdevpath = argv[3];
		if (strcmp(physdevpath, "-d") == 0) {
			mode = 1;
			debug = 1;
		}
		if (strcmp(physdevpath, "-e") == 0)
			mode = 2;
		if (argc > 4) {
			if (strcmp(argv[4], "-d") == 0) {
				debug = 1;
			}
			if (strcmp(argv[4], "1") == 0) // Called from bdpoll
			{
				mode = 0;
			}
		}
	}

	if (!action || !devpath) {
		return 1;
	}

	if (mode != 2) {
		memset(&serv_addr_un, 0, sizeof(serv_addr_un));
		serv_addr_un.sun_family = AF_LOCAL;
		strlcpy(serv_addr_un.sun_path, "/var/run/hotplug.socket", sizeof(serv_addr_un.sun_path));
		sd = socket(AF_LOCAL, SOCK_STREAM, 0);
	}
	if (mode == 2 || sd >= 0) {
		if (mode == 2 || connect(sd, (const struct sockaddr*)&serv_addr_un, sizeof(serv_addr_un)) >= 0) {
			char data[1024];
			size_t datalen = sizeof(data);

			if (mode > 0) {
				const char* env_devname = getenv("DEVNAME");
				const char* env_uuid = getenv("ID_FS_UUID");
				const char* env_id_type = getenv("ID_TYPE");
				const char* env_devtype = getenv("DEVTYPE");
				const char* env_fs_type = getenv("ID_FS_TYPE");
				const char* env_bus = getenv("ID_BUS");
				const char* env_model = getenv("ID_MODEL");
				const char* env_name = getenv("ID_NAME");
				if (strcmp(action, "add") == 0 && env_devname && env_uuid) {
					char devsize[50];
					get_device_size(devpath, devsize);
					int len = snprintf(data, datalen, "ACTION=%s\nDEVPATH=%s\nID_TYPE=%s\nDEVTYPE=%s\nDEVNAME=%s\nID_FS_TYPE=%s\nID_BUS=%s\nID_FS_UUID=%s\nID_MODEL=%s\nID_PART_ENTRY_SIZE=%s", action,
									   devpath, env_id_type ? env_id_type : "disk", env_devtype ? env_devtype : "", env_devname, env_fs_type ? env_fs_type : "", env_bus ? env_bus : "", env_uuid,
									   env_model ? env_model : (env_name ? env_name : ""), devsize);

					if (mode == 1) {
						send_to_socket(sd, mode, debug, data, len, datalen);
					} else {
						write_data_to_file(env_devname, data, debug);
					}
				} else if (strcmp(action, "remove") == 0) {
					if (env_devname && env_uuid) {
						int len = snprintf(data, datalen, "ACTION=%s\nDEVPATH=%s\nID_TYPE=%s\nDEVTYPE=%s\nDEVNAME=%s\nID_FS_UUID=%s", action, devpath, env_id_type ? env_id_type : "disk",
										   env_devtype ? env_devtype : "", env_devname, env_uuid);
						send_to_socket(sd, mode, debug, data, len, datalen);
					}
				} else if (strcmp(action, "ifup") == 0) {
					int len = snprintf(data, datalen, "ACTION=%s\nINTERFACE=%s", action, devpath);
					send_to_socket(sd, mode, debug, data, len, datalen);
				} else if (strcmp(action, "ifdown") == 0) {
					int len = snprintf(data, datalen, "ACTION=%s\nINTERFACE=%s", action, devpath);
					send_to_socket(sd, mode, debug, data, len, datalen);
				} else if (strcmp(action, "online") == 0) {
					int len = snprintf(data, datalen, "ACTION=%s\nSTATE=%s", action, devpath);
					send_to_socket(sd, mode, debug, data, len, datalen);
				}
			} else {
				int len = snprintf(data, datalen, "MODE=CD\nACTION=%s\nDEVPATH=%s\nPHYSDEVPATH=%s", action, devpath, physdevpath);
				send_to_socket(sd, 1, 0, data, len, datalen);
			}
		}
		if (mode != 2)
			close(sd);
	}
	return 0;
}
