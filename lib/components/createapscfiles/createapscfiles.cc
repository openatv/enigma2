 /* Copyright (C) 2009 Anders Holst
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

#define _LARGEFILE64_SOURCE
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <dirent.h>
#include <unistd.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <byteswap.h>
#include <errno.h>
#include <iostream>

#define LEN 24064

using namespace std;

char* makefilename(const char* dir, const char* base, const char* ext, const char* post)
{
  static char buf[256];
  int len1, len2, len3;
  len1 = (dir ? strlen(dir) : 0);
  len2 = (base ? strlen(base) : 0);
  len3 = (ext ? strlen(ext) : 0);
  if (dir) {
    strcpy(buf, dir);
    if (buf[len1-1] != '/') {
      buf[len1++] = '/';
      buf[len1] = 0;
    }
  }
  if (base)
    strcpy(buf+len1, base);
  if (ext && len2>=len3 && !strcmp(base+len2-len3,ext))
    len2 -= len3;
  if (ext)
    strcpy(buf+len1+len2, ext);
  if (post)
    strcpy(buf+len1+len2+len3, post);
  return buf;
}

int writebufinternal(int f, off64_t sz, off64_t tm)
{
  off64_t buf[2];
  buf[0] = (off64_t)bswap_64((unsigned long long int)sz);
  buf[1] = (off64_t)bswap_64((unsigned long long int)tm);
  if (write(f, buf, 16) != 16)
    return 1;
  else
    return 0;
}

int framepid(unsigned char* buf, int pos)
{
  return ((buf[pos+1] & 0x1f) << 8) + buf[pos+2];
}

off64_t framepts(unsigned char* buf, int pos)
{
  int tmp = (buf[pos+3] & 0x20 ? pos+buf[pos+4]+5 : pos+4);
  off64_t pts;
  if (buf[pos+1] & 0x40 &&
      buf[pos+3] & 0x10 &&
      buf[tmp]==0 && buf[tmp+1]==0 && buf[tmp+2]==1 &&
      buf[tmp+7] & 0x80) {
    pts  = ((unsigned long long)(buf[tmp+9]&0xE))  << 29;
    pts |= ((unsigned long long)(buf[tmp+10]&0xFF)) << 22;
    pts |= ((unsigned long long)(buf[tmp+11]&0xFE)) << 14;
    pts |= ((unsigned long long)(buf[tmp+12]&0xFF)) << 7;
    pts |= ((unsigned long long)(buf[tmp+13]&0xFE)) >> 1;
  } else
    pts = -1;
  return pts;
}

int framesearch(int fts, int first, off64_t& retpos, off64_t& retpts, off64_t& retpos2, off64_t& retdat, int filesize)
{
  static unsigned char buf[LEN];
  static int ind;
  static off64_t pos = -1;
  static off64_t num;
  static int pid = -1;
  static int st = 0;
  static double bytecount = 0;
  static double progress = 0.00;
  static int sdflag = 0;
  unsigned char* p;
  if (pos == -1 || first) {
    num = read(fts, buf, LEN);
    ind = 0;
    pos = 0;
    st = 0;
    sdflag = 0;
    pid = -1;
  }
  while (1) {
    p = buf+ind+st;
    ind = -1;
    for (; p < buf+num-6; p++) {

      bytecount = bytecount + 1;

      if (p[0]==0 && p[1]==0 && p[2]==1) {
        ind = ((p - buf)/188)*188;
        if ((p[3] & 0xf0) == 0xe0 && (buf[ind+1] & 0x40) &&
            (p-buf)-ind == (buf[ind+3] & 0x20 ? buf[ind+4] + 5 : 4)) {
          pid = framepid(buf, ind);
        } else if (pid != -1 && pid != framepid(buf, ind)) {
          ind = -1;
          continue;
        }

        if (p[3]==0 || p[3]==0xb3 || p[3]==0xb8) { // MPEG2
          if (p[3]==0xb3) {
            retpts = framepts(buf, ind);
            retpos = pos + ind;
          } else {
            retpts = -1;
            retpos = -1;
          }
          retdat = (unsigned int) p[3] | (p[4]<<8) | (p[5]<<16) | (p[6]<<24);
          retpos2 = pos + (p - buf);
          st = (p - buf) - ind + 1;
          sdflag = 1;
          return 1; 
        } else if (!sdflag && p[3]==0x09 && (buf[ind+1] & 0x40)) { // H264
          if ((p[4] >> 5)==0) {
            retpts = framepts(buf, ind);
            retpos = pos + ind;
          } else {
            retpts = -1;
            retpos = -1;
          }
          retdat = p[3] | (p[4]<<8);
          retpos2 = pos + (p - buf);
          st = (p - buf) - ind + 1;
          return 1; 
        } else {
          ind = -1;
          continue;
        }
      }
    }

    progress = bytecount/filesize*100;
    cout << "\rcreating ap&sc files: ";
    cout.width(2);
    cout << (int)progress << "%";

    st = 0;
    sdflag = 0; // reset to get some fault tolerance
    if (num == LEN) {
      pos += num;
      num = read(fts, buf, LEN);
      ind = 0;
    } else if (num) {
      ind = num;
      retpts = 0;
      retdat = 0;
      retpos = pos + num;
      num = 0;
      return -1;
    } else {
      retpts = 0;
      retdat = 0;
      retpos = 0;
      return -1;
    }
  }
}

int do_one(int fts, int fap, int fsc, int filesize)
{
  off64_t pos;
  off64_t pos2;
  off64_t pts;
  off64_t dat;
  int first = 1;
  while (framesearch(fts, first, pos, pts, pos2, dat, filesize) >= 0) {
    first = 0;
    if (pos >= 0 && pts >= 0)
      if (fap >= 0 && writebufinternal(fap, pos, pts))
        return 1;
    if (fsc >= 0 && writebufinternal(fsc, pos2, dat))
      return 1;
  }
  return 0;
}

int do_movie(char* inname)
{
  int f_ts=-1, f_sc=-1, f_ap=-1, f_tmp=-1;
  char* tmpname;
  long filesize;
  FILE *fp;
  tmpname = makefilename(0, inname, ".ts", 0);
  f_ts = open(tmpname, O_RDONLY | O_LARGEFILE);

  if (f_ts == -1) {
    printf("Failed to open input stream file \"%s\"\n", tmpname);
    return 1;
  }
  tmpname = makefilename(0, inname, ".ts", ".reconstruct_apsc");
  f_tmp = open(tmpname, O_WRONLY | O_CREAT | O_TRUNC, 0x1a4);
  if (f_tmp == -1) {
    printf("Failed to open sentry file \"%s\"\n", tmpname);
    goto failure;
  }
  close(f_tmp);
  tmpname = makefilename(0, inname, ".ts", ".ap");
  f_ap = open(tmpname, O_WRONLY | O_CREAT | O_TRUNC, 0x1a4);
  if (f_ap == -1) {
    printf("Failed to open output .ap file \"%s\"\n", tmpname);
    goto failure;
  }
  tmpname = makefilename(0, inname, ".ts", ".sc");
  f_sc = open(tmpname, O_WRONLY | O_CREAT | O_TRUNC, 0x1a4);
  if (f_sc == -1) {
    printf("Failed to open output .sc file \"%s\"\n", tmpname);
    goto failure;
  }

  //printf("  Processing .ap and .sc of \"%s\" ... ", inname);

  fp=fopen(inname,"rb");
  fseek(fp,0L,SEEK_END);
  filesize=ftell(fp);
  fclose(fp);

  fflush(stdout);
  if (do_one(f_ts, f_ap, f_sc, filesize)) {
    printf("\nFailed to reconstruct files for \"%s\"\n", inname);
    goto failure;
  }

  cout << "\rcreating ap&sc files: ";
  cout.width(3);
  cout << "100" << "%\n";

  close(f_ts);
  close(f_ap);
  close(f_sc);
  unlink(makefilename(0, inname, ".ts", ".reconstruct_apsc"));
  return 0;
 failure:
  if (f_ts != -1)
    close(f_ts);
  if (f_ap != -1) {
    close(f_ap);
    unlink(makefilename(0, inname, ".ts", ".ap"));
  }
  if (f_sc != -1) {
    close(f_sc);
    unlink(makefilename(0, inname, ".ts", ".sc"));
  }
  unlink(makefilename(0, inname, ".ts", ".reconstruct_apsc"));
  return 1;
}

int main(int argc, char* argv[])
{
  if (argc == 2 && *argv[1] != '-') {
    if (do_movie(argv[1]))
      exit(1);
  } else {
    printf("Usage: reconstruct_apsc movie_file\n");
    exit(1);
  }
}

