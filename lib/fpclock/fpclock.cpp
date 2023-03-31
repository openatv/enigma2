 /* Copyright (C) 2023 jbleyel
  *
  * This program is free software; you can redistribute it and/or
  * modify it under the terms of the GNU General Public License as
  * published by the Free Software Foundation; either version 2, or
  * (at your option) any later version.
  * 
  * This program is distributed in the hope that it will be useful,
  * but WITHOUT ANY WARRANTY; without even the implied warranty of
  * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  * GNU General Public License for more details.
  */


#include <sys/types.h>
#include <sys/stat.h>
#include <sys/ioctl.h>
#include <fcntl.h>
#include <time.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <getopt.h>

#define FP_IOCTL_SET_RTC 0x101
#define FP_IOCTL_GET_RTC 0x102

void setRTC(time_t time)
{
    char* dt = ctime(&time);
    printf("[FPClock] Set RTC time to %s\n",dt);
    FILE *f = fopen("/proc/stb/fp/rtc", "w");
    if (f)
    {
        if (!fprintf(f, "%u", (unsigned int)time))
            printf("[FPClock] Write /proc/stb/fp/rtc failed: %m\n");
        fclose(f);
    }
    else
    {
        int fd = open("/dev/dbox/fp0", O_RDWR);
        if (fd >= 0)
        {
            if (::ioctl(fd, FP_IOCTL_SET_RTC, (void*)&time) < 0)
                printf("[FPClock] FP_IOCTL_SET_RTC failed: %m\n");
            close(fd);
        }
    }
}

time_t getRTC()
{
    time_t rtc_time = 0;
    FILE *f = fopen("/proc/stb/fp/rtc", "r");
    if (f)
    {
        unsigned int tmp;
        if (fscanf(f, "%u", &tmp) != 1)
            printf("[FPClock] Read /proc/stb/fp/rtc failed: %m\n");
        else
#ifdef HAVE_NO_RTC
            rtc_time=0; // Sorry no RTC
#else
            rtc_time=tmp;
#endif
        fclose(f);
    }
    else
    {
        int fd = open("/dev/dbox/fp0", O_RDWR);
        if (fd >= 0)
        {
            if (::ioctl(fd, FP_IOCTL_GET_RTC, (void*)&rtc_time) < 0)
                printf("[FPClock] FP_IOCTL_GET_RTC failed: %m\n");
            close(fd);
        }
    }
    return rtc_time;
}


int read_fp()
{
    printf("[FPClock] Read\n");
    time_t time = getRTC();
    char* dt = ctime(&time);
    printf("[FPClock] Read result:%s\n",dt);
    return time;
}

int write_fp(char *newval)
{
    if(newval) {
        printf("[FPClock] Write %s\n",newval);
        unsigned int c = 0;
        sscanf(newval, ":%u", &c);
        if(c<1680284642)
        {
            printf("[FPClock] Write Error epoch:%u to low.\n",c);
            return 1;
        }
        setRTC(c);
    }
    else {
        printf("[FPClock] Update\n");
        setRTC(::time(0));
    }
    return 0;
}

int sync_fp()
{
    printf("[FPClock] Sync\n");

    return 0;
}

int main(int argc, char *argv[])
{
    if (argc == 1) {
        printf("FPClock: Version 1.0\n\n");
        printf("Usage: fpclock [-ruws] [value]\n\n");
        printf("Commands:\n");
        printf("\t-r\tRead and print the current RTC from front panel clock.\n");
        printf("\t-u\tUpdate the RTC of the front panel using the system time.\n");
        printf("\t-w:XX\tWrites the given epoch time to the RTC of the front panel.\n");
        printf("\t-s\tSync the current RTC from front panel to the system time.\n");
        printf("\n");
        return 0;
    }

    int c = 0;
    while ( (c = getopt(argc, argv, "rsuw:")) != -1)
    {
        switch (c)
        {
            case 'r':
                return read_fp();
                break;
            case 'u':
                return write_fp(NULL);
                break;
            case 'w':
                return write_fp(optarg);
                break;
            case 's':
                return sync_fp();
                break;
        }
    }

    printf("Wrong command line\n");
    return 1;

}
