/*
    bdpoll.c (based on addon-storage.c from hal-0.5.10)

    Poll storage devices for media changes

    Copyright (C) 2007 Andreas Oberritter
    Copyright (C) 2004 David Zeuthen, <david@fubar.dk>

    This program is free software; you can redistribute it and/or modify
    it under the terms of the GNU General Public License 2.0 as published by
    the Free Software Foundation.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License along
    with this program; if not, write to the Free Software Foundation, Inc.,
    51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
*/

#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <mntent.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mount.h>
#include <unistd.h>
#include <linux/cdrom.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <ctype.h>

enum {
	MEDIA_STATUS_UNKNOWN = 0,
	MEDIA_STATUS_GOT_MEDIA = 1,
	MEDIA_STATUS_NO_MEDIA = 2,
};

/* global static variables */
static int media_status = MEDIA_STATUS_NO_MEDIA;
static const int interval_in_seconds = 2;
static char volume_name[33];
static bool media_mounted = false;
static bool audio_cd = false;

static char *trimwhitespace(char *str)
{
	char *end;

	while(isspace(*str)) str++;

	if(*str == 0)
		return str;

	end = str + strlen(str) - 1;
	while(end > str && isspace(*end)) end--;
	*(end+1) = 0;

	return str;
}

static int media_read_data ( const char device_file[], int seek, int len, char * data)
{
	unsigned int fd;
	int ret = -1;
	if ( device_file != NULL) {
		if (( fd = open (device_file, O_RDONLY)) != -1) {
			if (lseek (fd, seek, SEEK_SET) != -1) {
				if ( read ( fd, data, len) != -1) {
					data[len] = '\0';
					ret = 0;
				}
			}
		}
		close ( fd);
	}
	return ret;
}

static void bdpoll_notify(const char devname[])
{
	char buf[1024];
	struct stat file_check;
	int i = 0;
	FILE *f;
	int fd = -1;
	int media_type = 0, start_track = 0, end_track = 0; 
	snprintf(buf, sizeof(buf), "/dev/%s", devname);
	// create symlink cdrom to the device needed for audio cd's  gst-1.0
	if (lstat("/dev/cdrom", &file_check) != 0) {
		symlink(buf, "/dev/cdrom");
	}
	// recreate symlink to the actif device
	else {
		unlink("/dev/cdrom");
		symlink(buf, "/dev/cdrom");
	}
	if (media_status == MEDIA_STATUS_GOT_MEDIA) {
		fd = open(buf, O_RDONLY | O_NONBLOCK);
		if (fd >= 0) {
			media_type = ioctl(fd, CDROM_DISC_STATUS , CDSL_CURRENT);
			struct cdrom_tochdr header;
			ioctl(fd,CDROMREADTOCHDR,(void *) &header);
			start_track = header.cdth_trk0;
			end_track = header.cdth_trk1;
			close(fd);
		}
		if( (end_track > 0 && media_type == CDS_AUDIO) || (end_track > 1 && media_type == CDS_MIXED) )
		{
			if (lstat("/media/audiocd/cdplaylist.cdpls", &file_check) == 0)
				unlink("/media/audiocd/cdplaylist.cdpls");
			else
				mkdir("/media/audiocd", 0777);
			for(i = start_track; i <= end_track; i++)
			{
				f = fopen("/media/audiocd/cdplaylist.cdpls", "a");
				if (f && i < 10)
					fprintf(f,"/media/audiocd/track-0%d.cda\n", i);
				if (f && i >= 10)
					fprintf(f,"/media/audiocd/track-%d.cda\n", i);
				fclose(f);
			}
			setenv("X_E2_MEDIA_STATUS", "1", 1);
			snprintf(buf, sizeof(buf), "/usr/bin/hotplug_e2_helper audiocdadd /dev/%s /block/%s/device 1", devname, devname);
			system(buf);
			media_mounted = false;
			audio_cd = true;
		}
		// CD/DVD will be mounted to his volume_label if avbl else to devicename
		else if (media_type >= CDS_DATA_1) {
			int seek =32808;
			int len = 32;
			char * out_buff = NULL;
			out_buff = malloc( (sizeof (out_buff)) * (len+1));
			snprintf(buf, sizeof(buf), "/dev/%s", devname);
			volume_name[0] = '\0';          // Set to empty string
			if ( media_read_data ( buf, seek, len, out_buff) != -1) {
				if (!strncmp(out_buff, "NO NAME", 7) || !strncmp (out_buff, " ",1)) {
					snprintf(volume_name, sizeof(volume_name), "UNTITLED-DISC");
				}
				else {
					// remove white spaces.
					char *trimmed_buff = NULL;
					trimmed_buff = trimwhitespace(out_buff);
					snprintf(volume_name, sizeof(volume_name), "%s", trimmed_buff);
				}
			}
			if (volume_name[0] == '\0') {   // Mustn't have empty string
				snprintf(volume_name, sizeof(volume_name), "%s", devname);
			}
			free(out_buff);
			out_buff = NULL;
			snprintf(buf, sizeof(buf),"/media/%s", volume_name);
			mkdir(buf, 0777);
			snprintf(buf, sizeof(buf), "/bin/mount -t udf /dev/%s /media/%s", devname, volume_name);
			printf("Mounting device /dev/%s to /media/%s\n", devname, volume_name);
			if (system(buf) == 0) {
				setenv("X_E2_MEDIA_STATUS", (media_status == MEDIA_STATUS_GOT_MEDIA) ? "1" : "0", 1);
				snprintf(buf, sizeof(buf), "/usr/bin/hotplug_e2_helper add /block/%s /block/%s/device 1", devname, devname);
				system(buf);
				media_mounted = true;
			}
			else {
					// udf fails, try iso9660
					snprintf(buf, sizeof(buf), "/bin/mount -t iso9660 /dev/%s /media/%s", devname, volume_name);
					if(system(buf) == 0) {
						setenv("X_E2_MEDIA_STATUS", (media_status == MEDIA_STATUS_GOT_MEDIA) ? "1" : "0", 1);
						snprintf(buf, sizeof(buf), "/usr/bin/hotplug_e2_helper add /block/%s /block/%s/device 1", devname, devname);
						system(buf);
						media_mounted = true;
					}
					else
						printf("Unable to mount disc\n");
			}
		}
		else {
			// unsuported media
			printf("Unable to mount disc\n");
		}
	}
	else {
		// unmounting cd/dvd upon removal. Clear mointpoint.
		if (media_mounted || audio_cd)
		{
			if (audio_cd)
			{
				snprintf(buf, sizeof(buf), "/usr/bin/hotplug_e2_helper audiocdremove /dev/%s /block/%s/device 1", devname, devname);
				system(buf);
				setenv("X_E2_MEDIA_STATUS", "0", 1);
				audio_cd = false;
				if (lstat("/media/audiocd/cdplaylist.cdpls", &file_check) == 0)
				{
					unlink("/media/audiocd/cdplaylist.cdpls");
					rmdir("/media/audiocd");
				}
			}
			else
			{
				snprintf(buf, sizeof(buf), "/bin/umount /dev/%s -l", devname);
				system(buf);
				snprintf(buf, sizeof(buf), "/media/%s", volume_name);
				unlink(buf);
				rmdir(buf);
				// Clear volume_name.
				memset(&volume_name[0], 0, sizeof(volume_name));
				setenv("X_E2_MEDIA_STATUS", "0", 1);
				// Removing device after cd/dvd is removed.
				snprintf(buf, sizeof(buf), "/usr/bin/hotplug_e2_helper remove /block/%s /block/%s/device 1", devname, devname);
				system(buf);
				media_mounted = false;
			}
		}
		else
		{
			setenv("X_E2_MEDIA_STATUS", "0", 1);
			setenv("DEVPATH", NULL, 1);
			setenv("PHYSDEVPATH", NULL, 1);
			setenv("ACTION", NULL, 1);
		}
	}
}

static bool is_mounted(const char device_file[])
{
	FILE *f;
	bool rc;
	struct mntent mnt;
	struct mntent *mnte;
	char buf[512];

	rc = false;

	if ((f = setmntent("/etc/mtab", "r")) == NULL)
		return rc;

	while ((mnte = getmntent_r(f, &mnt, buf, sizeof(buf))) != NULL) {
		if (strcmp(device_file, mnt.mnt_fsname) == 0) {
			rc = true;
			break;
		}
	}

	endmntent(f);
	return rc;
}

static bool poll_for_media(const char devname[], bool is_cdrom, bool support_media_changed)
{
	int fd;
	bool got_media = false;
	bool ret = false;
	char device_file[38];
	snprintf(device_file, sizeof(device_file), "/dev/%s", devname); 

	if (is_cdrom) {
		int drive;

		fd = open(device_file, O_RDONLY | O_NONBLOCK | O_EXCL);
		if (fd < 0 && errno == EBUSY) {
			/* this means the disc is mounted or some other app,
			 * like a cd burner, has already opened O_EXCL */

			/* HOWEVER, when starting hald, a disc may be
			 * mounted; so check /etc/mtab to see if it
			 * actually is mounted. If it is we retry to open
			 * without O_EXCL
			 */
			if (!is_mounted(device_file))
				return false;
			fd = open(device_file, O_RDONLY | O_NONBLOCK);
		}
		if (fd < 0) {
			printf("%s: %s", device_file, strerror(errno));
			return false;
		}

		/* Check if a disc is in the drive
		 *
		 * @todo Use MMC-2 API if applicable
		 */
		drive = ioctl(fd, CDROM_DRIVE_STATUS, CDSL_CURRENT);
		switch (drive) {
			case CDS_NO_INFO:
			case CDS_NO_DISC:
			case CDS_TRAY_OPEN:
			case CDS_DRIVE_NOT_READY:
				break;
			case CDS_DISC_OK:
				/* some CD-ROMs report CDS_DISK_OK even with an open
				 * tray; if media check has the same value two times in
				 * a row then this seems to be the case and we must not
				 * report that there is a media in it. */
				if (support_media_changed) { // -cm option
					if (ioctl(fd, CDROM_MEDIA_CHANGED, CDSL_CURRENT) &&
						ioctl(fd, CDROM_MEDIA_CHANGED, CDSL_CURRENT)) {
						ioctl(fd, CDROM_LOCKDOOR, 0);
					}
					else {
						got_media = true;
						/*
						 * this is a bit of a hack; because we mount the cdrom, the eject button
						 * would not work, so we would never detect 'medium removed', and
						 * never umount the cdrom.
						 * So we unlock the door
						 */
						ioctl(fd, CDROM_LOCKDOOR, 0);
					}
				}
				else { // -c option
					got_media = true;
					/*
					 * this is a bit of a hack; because we mount the cdrom, the eject button
					 * would not work, so we would never detect 'medium removed', and
					 * never umount the cdrom.
					 * So we unlock the door
					 */
					ioctl(fd, CDROM_LOCKDOOR, 0);
				}
				break;
			case -1:
				printf("%s: CDROM_DRIVE_STATUS: %s", device_file, strerror(errno));
				break;
		}
		close(fd);
	} else {
		fd = open(device_file, O_RDONLY);
		if ((fd < 0) && (errno == ENOMEDIUM)) {
			got_media = false;
		} else if (fd >= 0) {
			got_media = true;
			close(fd);
		} else {
			printf("%s: %s", device_file, strerror(errno));
			return false;
		}
	}

	switch (media_status) {
	case MEDIA_STATUS_GOT_MEDIA:
		if (!got_media) {
			printf("Media removal detected on %s\n", device_file);
			ret = true;
			/* have to this to trigger appropriate hotplug events */
			fd = open(device_file, O_RDONLY | O_NONBLOCK);
			if (fd >= 0) {
				ioctl(fd, BLKRRPART);
				close(fd);
			}
		}
		break;

	case MEDIA_STATUS_NO_MEDIA:
		if (got_media) {
			printf("Media insertion detected on %s\n", device_file);
			ret = true;
		}
		break;
	}

	/* update our current status */
	if (got_media)
		media_status = MEDIA_STATUS_GOT_MEDIA;
	else {
		media_status = MEDIA_STATUS_NO_MEDIA;
	}

	return ret;
}

static void usage(const char argv0[])
{
	fprintf(stderr, "usage: %s <devname> [-c][-m][-D]\n", argv0);
}

int main(int argc, char *argv[], char *envp[])
{
	const char *devname = NULL;
	bool is_cdrom = false;
	bool support_media_changed = false;
	int opt;
	bool run_as_daemon = true;

	while ((opt = getopt(argc, argv, "cmD")) != -1) {
		switch (opt) {
		case 'c':
			is_cdrom = true;
			break;
		case 'm':
			support_media_changed = true;
			break;
		case 'D':
			run_as_daemon = false;
			break;
		default:
			usage(argv[0]);
			return EXIT_FAILURE;
		}
	}

	if (optind >= argc) {
		usage(argv[0]);
		return EXIT_FAILURE;
	}

	devname = argv[optind];

	if (run_as_daemon) daemon(0, 0);

	for (;;) {
		if (poll_for_media(devname, is_cdrom, support_media_changed))
			bdpoll_notify(devname);
		sleep(interval_in_seconds);
	}

	return EXIT_SUCCESS;
}
