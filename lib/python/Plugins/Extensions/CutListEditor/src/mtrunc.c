/* Copyright (C) 2007, 2008, 2009 Anders Holst
 *
 * Rewritten by Jason Hood, 6 & 7 April, 2017, to truncate rather than cut.
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
 *
 * You should have received a copy of the GNU General Public License
 * along with this software; see the file COPYING.  If not, write to
 * the Free Software Foundation, Inc., 59 Temple Place, Suite 330,
 * Boston, MA 02111-1307 USA
 */

#define _LARGEFILE64_SOURCE
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdbool.h>
#ifdef _WIN32
#define bswap_32 _byteswap_ulong
#define bswap_64 _byteswap_uint64
#define O_LARGEFILE 0
#else
#include <byteswap.h>
#endif


typedef long long int pts_t;
struct ap
{
  off64_t off;
  pts_t   pts;
};


inline off_t ltell( int f )
{
  return lseek( f, 0, SEEK_CUR );
}


pts_t strtotime( char* str )
{
  char* e;
  double tt, t1;

  if (strpbrk( str, ":." ) == NULL)
  {
    pts_t t = strtoll( str, &e, 10 );
    if (*e != '\0')
      return 0;
    // Assume smaller than ten seconds means seconds, not PTS.
    return (t < 900000) ? t * 90000 : t;
  }

  tt = 0;
  for (int i = 1;; ++i)
  {
    t1 = strtod( str, &e );
    if (i == 4 || (str == e && *e != ':' && *e != '\0'))
      return 0;
    tt = 60 * tt + t1;
    if (*e == '\0')
      break;
    str = e + 1;
  }

  return tt * 90000;
}


bool readbufinternal( int f, off64_t* buf )
{
  if (read( f, buf, 16 ) != 16)
    return false;

  buf[0] = bswap_64( buf[0] );
  buf[1] = bswap_64( buf[1] );

  return true;
}


void truncsc( int fs, off64_t off )
{
  off64_t buf[2];

  if (fs == -1)
    return;

  while (readbufinternal( fs, buf ))
  {
    if (buf[0] >= off)
    {
      ftruncate( fs, ltell( fs ) - 16 );
      break;
    }
  }
}


off64_t readoff( int fa, pts_t t )
{
  struct ap buf, buf1, buf2;
  pts_t time_offset;
  pts_t tt, lt;

  if (!(readbufinternal( fa, &buf.off ) && readbufinternal( fa, &buf1.off )))
  {
    printf( "The corresponding \".ap\"-file is empty.\n" );
    exit( 8 );
  }
  lseek( fa, 0, SEEK_SET );

  time_offset = buf.pts;
  if (buf.off != 0 && buf.off < buf1.off)
    time_offset -= (buf1.pts - buf.pts) * buf.off / (buf1.off - buf.off);

  buf1 = buf2 = buf;
  lt = -1;
  do
  {
    if (!readbufinternal( fa, &buf.off ))
      break;
    tt = buf.pts - time_offset;
    if (tt <= lt || tt - lt > 90000*10)
    {
      time_offset = buf1.pts - buf2.pts;
      if (time_offset > 0 && time_offset <= 90000*10 &&
          buf2.off < buf1.off && buf1.off < buf.off)
      {
        time_offset *= buf.off - buf1.off;
        time_offset /= buf1.off - buf2.off;
      }
      else
        time_offset = 90000/25;
      time_offset = buf.pts - lt - time_offset;
      tt = buf.pts - time_offset;
    }
    lt = tt;
    buf2 = buf1;
    buf1 = buf;
  } while (tt < t);

  return buf.off;
}


void mtrunc( int fa, int fs, int fts, pts_t et )
{
  off64_t off;

  off = readoff( fa, et );
  ftruncate( fa, ltell( fa ) - 16 );
  truncsc( fs, off );
  ftruncate64( fts, off );
}


char* makefilename( const char* base, const char* post )
{
  static char buf[1024];

  snprintf( buf, sizeof(buf), "%s%s", base, post );
  return buf;
}


int main( int argc, char* argv[] )
{
  int f_ts, f_ap, f_sc;
  char* tmpname;
  char* inname = NULL;
  int i;
  bool bad = false;
  pts_t et = 0;
  struct stat statbuf;
  struct stat64 statbuf64;

  for (i = 1; i < argc; i++)
  {
    if (!strcmp( argv[i], "-e" ))
    {
      if (i == argc - 1)
      {
        bad = true;
        break;
      }
      et = strtotime( argv[++i] );
    }
    else if (argv[i][0] == '-' && (argv[i][1] == '\0' || argv[i][2] == '\0'))
    {
      bad = true;
      break;
    }
    else if (!inname)
    {
      inname = argv[i];
    }
    else
    {
      bad = true;
      break;
    }
  }
  if (argc == 1 || et == 0 || bad)
  {
    printf( "Usage: mtrunc ts_file -e end\n"
            "   -e : End the movie at this time, given as [[hour:][min]:][sec.[msec]] or PTS\n" );
    exit( 1 );
  }

#ifdef _WIN32
  _fmode = O_BINARY;
#endif

  f_ts = open( inname, O_RDWR | O_LARGEFILE );
  if (f_ts == -1)
  {
    printf( "Failed to open stream file \"%s\".\n", inname );
    exit( 2 );
  }

  tmpname = makefilename( inname, ".ap" );
  f_ap = open( tmpname, O_RDWR );
  if (f_ap == -1)
  {
    printf( "Failed to open ap file \"%s\".\n", tmpname );
    close( f_ts );
    exit( 4 );
  }

  tmpname = makefilename( inname, ".sc" );
  f_sc = open( tmpname, O_RDWR );

  if (fstat64( f_ts, &statbuf64 ))
  {
    printf( "Failed to stat stream file.\n" );
    close( f_ts );
    close( f_ap );
    if (f_sc != -1) close( f_sc );
    exit( 2 );
  }

  if (fstat( f_ap, &statbuf ))
  {
    printf( "Failed to stat ap file.\n" );
    close( f_ts );
    close( f_ap );
    if (f_sc != -1) close( f_sc );
    exit( 4 );
  }

  if (f_sc != -1 && fstat( f_sc, &statbuf ))
  {
    close( f_sc );
    f_sc = -1;
  }

  mtrunc( f_ap, f_sc, f_ts, et );

  close( f_ts );
  close( f_ap );
  if (f_sc != -1) close( f_sc );

  return 0;
}
