/*
 * FPClock (c) 2023 jbleyel
 *
 * This program is free software; you can redistribute it and/or
 * modify it under the terms of the GNU General Public License
 * as published by the Free Software Foundation; either version 2
 * of the License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software Foundation,
 * Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
 *
 */

/*
The sceleton of the daemon is based on https://github.com/jirihnidek/daemon
by Jiri Hnidek <jiri.hnidek@tul.cz>
*/

#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <syslog.h>
#include <signal.h>
#include <getopt.h>
#include <string.h>
#include <fcntl.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <errno.h>
#ifdef __APPLE__
#include <sys/time.h>
#else
#include <time.h>
#endif
#include <sys/ioctl.h>

static bool verbose = false;
static int forcedate = -1;
static int running = 0;
static int delay = 1800;
static int counter = 0;
static char *conf_file_name = NULL;
static char *pid_file_name = NULL;
static int pid_fd = -1;
static FILE *log_stream;

const char * APP = "FPClock";
const char * app_name = "fpclock";
const char * app_ver = "1.3";


#define FP_IOCTL_SET_RTC 0x101
#define FP_IOCTL_GET_RTC 0x102

/**
 * \brief set epoch to RTC
 * \param    time   new epoch
 */
void setRTC(time_t time)
{
    char* dt = ctime(&time);

    fprintf(log_stream,"[%s] Set RTC time to %s\n",APP,dt);
    FILE *f = fopen("/proc/stb/fp/rtc", "w");
    if (f)
    {
        if (!fprintf(f, "%u", (unsigned int)time))
            fprintf(log_stream,"[%s] Write /proc/stb/fp/rtc failed: %m\n",APP);
        fclose(f);
    }
    else
    {
        int fd = open("/dev/dbox/fp0", O_RDWR);
        if (fd >= 0)
        {
            if (::ioctl(fd, FP_IOCTL_SET_RTC, (void*)&time) < 0)
                fprintf(log_stream,"[%s] FP_IOCTL_SET_RTC failed: %m\n",APP);
            close(fd);
        }
    }
}

/**
 * \brief get epoch from RTC
 */
time_t getRTC()
{
    time_t rtc_time = 0;
    FILE *f = fopen("/proc/stb/fp/rtc", "r");
    if (f)
    {
        unsigned int tmp;
        if (fscanf(f, "%u", &tmp) != 1)
            fprintf(log_stream,"[%s] Read /proc/stb/fp/rtc failed: %m\n",APP);
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
        if(verbose) {
            fprintf(log_stream,"[%s] /proc/stb/fp/rtc not exists\n",APP);
        }
        
        int fd = open("/dev/dbox/fp0", O_RDWR);
        if (fd >= 0)
        {
            if (::ioctl(fd, FP_IOCTL_GET_RTC, (void*)&rtc_time) < 0)
                fprintf(log_stream,"[%s] FP_IOCTL_GET_RTC failed: %m\n",APP);
            close(fd);
        }
        else {
            if(verbose) {
                fprintf(log_stream,"[%s] /dev/dbox/fp0 not exists\n",APP);
            }
        }
    }
    return rtc_time;
}


/**
 * \brief Read configuration from config file
 */
int read_conf_file(int reload)
{
    FILE *conf_file = NULL;
    int ret = -1;

    if (conf_file_name == NULL) return 0;

    conf_file = fopen(conf_file_name, "r");

    if (conf_file == NULL) {
        syslog(LOG_ERR, "Can not open config file: %s, error: %s",
                conf_file_name, strerror(errno));
        return -1;
    }

    ret = fscanf(conf_file, "%d", &delay);

    if (ret > 0) {
        if (reload == 1) {
            syslog(LOG_INFO, "Reloaded configuration file %s of %s",
                conf_file_name,
                app_name);
        } else {
            syslog(LOG_INFO, "Configuration of %s read from file %s",
                app_name,
                conf_file_name);
        }
    }

    fclose(conf_file);

    return ret;
}


/**
 * \brief Callback function for handling signals.
 * \param    sig    identifier of signal
 */
void handle_signal(int sig)
{
    if (sig == SIGINT) {
        fprintf(log_stream, "Debug: stopping daemon ...\n");
        /* Unlock and close lockfile */
        if (pid_fd != -1) {
            lockf(pid_fd, F_ULOCK, 0);
            close(pid_fd);
        }
        /* Try to delete lockfile */
        if (pid_file_name != NULL) {
            unlink(pid_file_name);
        }
        running = 0;
        /* Reset signal handling to default behavior */
        signal(SIGINT, SIG_DFL);
    } else if (sig == SIGHUP) {
        fprintf(log_stream, "Debug: reloading daemon config file ...\n");
        read_conf_file(1);
    } else if (sig == SIGCHLD) {
        fprintf(log_stream, "Debug: received SIGCHLD signal\n");
    }
}

/**
 * \brief This function will daemonize this app
 */
static void daemonize()
{
    pid_t pid = 0;
    int fd;

    /* Fork off the parent process */
    pid = fork();

    /* An error occurred */
    if (pid < 0) {
        exit(EXIT_FAILURE);
    }

    /* Success: Let the parent terminate */
    if (pid > 0) {
        exit(EXIT_SUCCESS);
    }

    /* On success: The child process becomes session leader */
    if (setsid() < 0) {
        exit(EXIT_FAILURE);
    }

    /* Ignore signal sent from child to parent process */
    signal(SIGCHLD, SIG_IGN);

    /* Fork off for the second time*/
    pid = fork();

    /* An error occurred */
    if (pid < 0) {
        exit(EXIT_FAILURE);
    }

    /* Success: Let the parent terminate */
    if (pid > 0) {
        exit(EXIT_SUCCESS);
    }

    /* Set new file permissions */
    umask(0);

    /* Change the working directory to the root directory */
    /* or another appropriated directory */
    chdir("/");

    /* Close all open file descriptors */
    for (fd = (int)sysconf(_SC_OPEN_MAX); fd > 0; fd--) {
        close(fd);
    }

    /* Reopen stdin (fd = 0), stdout (fd = 1), stderr (fd = 2) */
    stdin = fopen("/dev/null", "r");
    stdout = fopen("/dev/null", "w+");
    stderr = fopen("/dev/null", "w+");

    /* Try to write PID of daemon to lockfile */
    if (pid_file_name != NULL)
    {
        char str[256];
        pid_fd = open(pid_file_name, O_RDWR|O_CREAT, 0640);
        if (pid_fd < 0) {
            /* Can't open lockfile */
            exit(EXIT_FAILURE);
        }
        if (lockf(pid_fd, F_TLOCK, 0) < 0) {
            /* Can't lock file */
            exit(EXIT_FAILURE);
        }
        /* Get current PID */
        snprintf(str, 256, "%d\n", getpid());
        /* Write PID to lockfile */
        write(pid_fd, str, strlen(str));
    }
}

/**
 * \brief Print help for this application
 */
void print_help(void)
{
    printf("%s: Version %s\n\n",APP,app_ver);
    printf("Usage: %s [OPTIONS]\n\n", app_name);
    printf("  Options:\n");
    printf("\t-h --help                 Print this help\n");
//    printf("   -c --conf_file filename   Read configuration from the file\n");
    printf("\t-t --timeout timeout      Set the loop timeout in seconds (default 1800)\n");
    printf("\t-l --log_file  filename   Write logs to the file (only for daemon mode)\n");
    printf("\t-d --daemon               Daemonize this application\n");
    printf("\t-p --print                Print FP clock time\n");
    printf("\t-u --update               Update FP clock with the current system time\n");
    printf("\t-f --force epoch          Force FP clock to given epoch time\n");
    printf("\t-r --restore              Restore current system time from FP clock\n");
    printf("\t-v --verbose              Enable debugging output\n");
    printf("\n");
}


/**
 * \brief get epoch from RTC
 */
int read_fp()
{
    if(verbose)
        fprintf(log_stream, "[%s] Read\n",APP);
    time_t time = getRTC();
    if(time) {
        char* dt = ctime(&time);
        fprintf(log_stream, "[%s] Read result:%s\n",APP,dt);
    }
    else {
        fprintf(log_stream, "[%s] Read RTC failed\n",APP);
    }
    return 0;
}

/**
 * \brief set epoch to RTC
 * \param    c   new epoch
 */
int write_fp(int c)
{

    if(c!=-1) {
        if(verbose)
            fprintf(log_stream, "[%s] Write %d\n", APP,c);

        if(c<1680284642)
        {
            fprintf(log_stream,"[%s] Write Error epoch:%d to low.\n",APP,c);
            return 1;
        }
        setRTC(c);
    }
    else {
        fprintf(log_stream,"[%s] Update\n",APP);
        setRTC(::time(0));
    }
    return 0;
}

/**
 * \brief write epoch from RTC to system
 */
int sync_fp()
{
    fprintf(log_stream,"[%s] Sync\n",APP);
    time_t rtc_time = getRTC();
    time_t system_time = ::time(0);
    if(rtc_time)
    {
        long time_difference = rtc_time - system_time;
        if ((time_difference >= -15) && (time_difference <= 15))
        {
            timeval tdelta, tolddelta;
            tdelta.tv_sec = time_difference;
            int rc = adjtime(&tdelta, &tolddelta);
            if(rc == 0)
                fprintf(log_stream,"[%s] Slewing Linux time by %ld seconds.",APP, time_difference);
            else
                fprintf(log_stream,"[%s] Slewing Linux time by %ld seconds FAILED!",APP, time_difference);
        }
        else{
            timeval tnow;
            gettimeofday(&tnow, 0);
            tnow.tv_sec = rtc_time;
            settimeofday(&tnow, 0);
        }

    }
    else
    {
        fprintf(log_stream,"[%s] Update\n",APP);
    }

    return 0;
}


/**
 * \brief main
 */
int main(int argc, char *argv[])
{
    static struct option long_options[] = {
        {"timeout", required_argument, 0, 't'},
        {"force", required_argument, 0, 'f'},
//        {"conf_file", required_argument, 0, 'c'},
        {"test_conf", required_argument, 0, 't'},
        {"log_file", required_argument, 0, 'l'},
        {"help", no_argument, 0, 'h'},
        {"daemon", no_argument, 0, 'd'},
        {"verbose", no_argument, 0, 'v'},
        {"restore", no_argument, 0, 'r'},
        {"print", no_argument, 0, 'p'},
        {"update", no_argument, 0, 'u'},
        {NULL, 0, 0, 0}
    };
    int value, option_index = 0, ret;
    char *log_file_name = NULL;
    bool start_daemonized = false;

    if(argc == 1)
    {
        print_help();
        return EXIT_SUCCESS;
    }

    pid_file_name = new char[256];
    snprintf(pid_file_name, 256, "/var/run/%s.pid" , app_name );

    log_stream = stdout;
    
    int action = 0;
    
    while ((value = getopt_long(argc, argv, "l:t:f:pdhrudpv", long_options, &option_index)) != -1) {
        switch (value) {
            case 't':
                sscanf(optarg, "%d", &delay);
                break;
//            case 'c':
//                conf_file_name = strdup(optarg);
//                break;
            case 'l':
                log_file_name = strdup(optarg);
                break;
            case 'd':
                start_daemonized = true;
                break;
            case 'v':
                verbose = true;
                break;
            case 'f':
                sscanf(optarg, "%d", &forcedate);
                action = 2;
                break;
            case 'r':
                action = 3;
                break;
            case 'u':
                action = 2;
                break;
            case 'h':
                print_help();
                goto EXIT;
            case 'p':
                action = 1;
                break;
            case '?':
                print_help();
                goto EXIT;
            default:
                break;
        }
    }

    if(verbose)
    {
        printf("%s: Version %s\n\n",APP,app_ver);
        printf("[%s] Verbose logging\n",APP);
        printf("[%s] Delay : %d\n",APP,delay);
        if(forcedate!=-1)
            printf("[%s] Force epoch : %d\n",APP,forcedate);
    }

    if(action) {
        if(action == 1)
        {
            read_fp();
        }
        else if(action == 2)
        {
            write_fp(forcedate);
        }
        else if(action == 3)
        {
            sync_fp();
        }
        goto EXIT;
    }

    /* When daemonizing is requested at command line. */
    if (start_daemonized) {
        /* It is also possible to use glibc function deamon()
         * at this point, but it is useful to customize your daemon. */
        daemonize();
    }
    else {
        goto EXIT;
    }

    /* Open system log and write message to it */
    openlog(argv[0], LOG_PID|LOG_CONS, LOG_DAEMON);
    syslog(LOG_INFO, "Started %s V:%s", app_name, app_ver);

    /* Daemon will handle two signals */
    signal(SIGINT, handle_signal);
    signal(SIGHUP, handle_signal);

    /* Try to open log file to this daemon */
    if (log_file_name != NULL) {
        log_stream = fopen(log_file_name, "a+");
        if (log_stream == NULL) {
            syslog(LOG_ERR, "Can not open log file: %s, error: %s",
                log_file_name, strerror(errno));
            log_stream = stdout;
        }
    }

    /* Read configuration from config file */
    read_conf_file(0);

    /* This global variable can be changed in function handling signal */
    running = 1;

    /* Never ending loop of server */
    while (running == 1) {
        /* Debug print */
		if(verbose) {
	        ret = fprintf(log_stream, "Debug: %d\n", counter++);
	        if (ret < 0) {
	            syslog(LOG_ERR, "Can not write to log stream: %s, error: %s",
	                (log_stream == stdout) ? "stdout" : log_file_name, strerror(errno));
	            break;
	        }
	        ret = fflush(log_stream);
	        if (ret != 0) {
	            syslog(LOG_ERR, "Can not fflush() log stream: %s, error: %s",
	                (log_stream == stdout) ? "stdout" : log_file_name, strerror(errno));
	            break;
	        }
		}

        write_fp(-1);

        /* Real server should use select() or poll() for waiting at
         * asynchronous event. Note: sleep() is interrupted, when
         * signal is received. */
        sleep(delay);
    }

    /* Close log file, when it is used. */
    if (log_stream != stdout) {
        fclose(log_stream);
    }


    /* Write system log and close it. */
    syslog(LOG_INFO, "Stopped %s", app_name);
    closelog();

EXIT:
    
    /* Free allocated memory */
//    if (conf_file_name != NULL) free(conf_file_name);
    if (log_file_name != NULL) free(log_file_name);
    if (pid_file_name != NULL) free(pid_file_name);

    return EXIT_SUCCESS;
}

