// this is nconfig 0.92, a bit modified
#define NO_MAP_SHARED
#include <stdlib.h>
#include <stdio.h>
#include <sys/stat.h>
#include <lib/base/nconfig.h>

#include <fcntl.h>
#include <string.h>
#include <memory.h>
#include <sys/types.h>
#include <unistd.h>
#include <sched.h>

#include <sys/mman.h>

#include <limits.h>

#ifndef PAGESIZE
#ifdef PAGE_SIZE
#define PAGESIZE PAGE_SIZE
#else
#define PAGESIZE 4096
#endif
#endif

#define SB				((struct nc_sb_s *) data)
#define CM(x)			((struct nc_chunk_s *) (data+(x)))
#define DE(x)			((struct nc_de_s *) (data+(x)))
#define IDE(x, y)		(DE(((unsigned *) (data+(x)->offset))[(y)]))
#define CS(x)			(((unsigned *) (data+(x)))[-1])

inline unsigned NConfig::crc(const char *d, unsigned len)
{
	unsigned ret = 0;
	unsigned l = len / sizeof(unsigned);

	while (l) {
		ret += *(const unsigned *)d;
		ret = (ret << 3) & (ret >> 29);
		l--;
		d += sizeof(unsigned);
	}
	return ret;
}

NConfig::NConfig(int protect)
{
	fd = -1;
	cname = fname = data = NULL;
	sb = NULL;
	cdir = NULL;
	chunks = NULL;
	revision = update = lsize = omode = 0;
	olck = 0;
	lock = NC_L_NONE;
	careful = protect;
}

NConfig::~NConfig()
{
	close();
	free(fname);
}

void NConfig::close()
{
	free(cname);
	cname = NULL;
	if (fd > -1) {
#ifdef NO_MAP_SHARED
		if (data) {
			int size=sb->size;
			char *buffer=new char[size];
			memcpy(buffer, data, size);
			munmap(data, size);
			data = NULL;
			::lseek(fd, 0, SEEK_SET);
			::write(fd, buffer, size);
			delete[] buffer;
		}
#endif
		::close(fd);
		fd = -1;
	}
	if (data) {
		munmap(data, sb->size);
		data = NULL;
	}
}

void NConfig::flush()
{
	close();
	open(omode);
}

int NConfig::setName(const char *name)
{
	if (!name)
		return NC_ERR_NVAL;
	if (fd > -1)
		return NC_ERR_PERM;
	free(fname);
	fname = strdup(name);
	return NC_ERR_OK;
}

int NConfig::createNew(unsigned resize, unsigned dirent, unsigned mchunks)
{
	if (fd > -1)
		return NC_ERR_NVAL;
	if (!access(fname, F_OK))
		return NC_ERR_PERM;

	int ff;
	if ((ff = ::open(fname, O_WRONLY | O_CREAT, 0600)) == -1)
		return NC_ERR_NFILE;
	struct nc_sb_s bsb = {NC_SB_MAGIC, resize*PAGESIZE, 
						dirent, mchunks, resize, mchunks,
						sizeof(struct nc_sb_s)+sizeof(struct nc_de_s)+2*sizeof(unsigned),
						sizeof(struct nc_sb_s), 0};
	struct nc_de_s bde = {sizeof(struct nc_sb_s)+sizeof(struct nc_de_s),
						NC_DIR, sizeof(struct nc_sb_s), 0, 0, 0};
	struct nc_chunk_s bcm;

	write(ff, &bsb, sizeof(bsb));
	write(ff, &bde, sizeof(bde));
	write(ff, "/", 2);

	lseek(ff, sizeof(unsigned)-2, SEEK_CUR);
	unsigned cl = sizeof(nc_chunk_s)*mchunks+sizeof(unsigned);
	write(ff, &cl, sizeof(unsigned));

	bcm.offset = bsb.chunk + sizeof(struct nc_chunk_s)*mchunks;
	bcm.size = bsb.size - bcm.offset;

	write(ff, &bcm, sizeof(bcm));

	lseek(ff, bsb.size-1, SEEK_SET);
	write(ff, "", 1);
	::close(ff);
	return NC_ERR_OK;
}
	

int NConfig::open(int how)
{
	if (!fname)
		return NC_ERR_NFILE;
	if (how != NC_O_RO && how != NC_O_RW)
		return NC_ERR_TYPE;
	if (fd > -1)
		close();

	int ff;
	if ((ff = ::open(fname, how)) == -1)
		return NC_ERR_PERM;

	struct stat sbuf;
	fstat(ff, &sbuf);

	if (!sbuf.st_size)
		return NC_ERR_CORRUPT;

#ifdef NO_MAP_SHARED
	if ((data = (char *) mmap(NULL, sbuf.st_size, how == NC_O_RO ? PROT_READ : (PROT_READ|PROT_WRITE), MAP_PRIVATE, ff, 0)) == MAP_FAILED) {
#else
	if ((data = (char *) mmap(NULL, sbuf.st_size, how == NC_O_RO ? PROT_READ : (PROT_READ|PROT_WRITE), MAP_SHARED, ff, 0)) == MAP_FAILED) {
#endif
		::close(ff);
		return NC_ERR_NMEM;
	}
	if (memcmp(((struct nc_sb_s *) data)->magic, NC_SB_MAGIC, 4)) {
		munmap(data, sbuf.st_size);
		::close(ff);
		return NC_ERR_CORRUPT;
	}
	fd = ff;
	omode = how;
	sb = SB;
	lsize = 0;
	cname = strdup("/");

	lockFile(NC_L_RO, TRUE);
	rdir = DE(sb->root);
	unLockFile();
	return NC_ERR_OK;
}

void NConfig::expand(unsigned toadd)
{
	unsigned nsize = sb->size + toadd;
	lseek(fd, nsize-1, SEEK_SET);
	write(fd, "", 1);
	_remap(sb->size, nsize);
	sb->size = nsize;
	cdir = getDirEnt(cname);
	chunks = CM(sb->chunk);
#ifdef NC_DEBUG_ALLOC
	fprintf(stderr, "Expanded from %u to %u\n", nsize-toadd, nsize);
#endif
}

unsigned NConfig::getChunk(unsigned s)
{
	int lst = -1;

	// Make sure we get aligned data
	s = alignSize(s) + sizeof(unsigned);

#ifdef NC_DEBUG_ALLOC
	fprintf(stderr, "Taking %u (total %u)\n", s, sb->chunk_ttl);
#endif

	do {
		int left = 0, right = sb->chunk_ttl - 1, c;
		while (left <= right) {
			int diff = chunks[c = (left + right) / 2].size - s;
			if (diff < 0 || diff == sizeof(unsigned)) {
#ifdef NC_DEBUG_ALLOC
				if (diff > 0)
					fprintf(stderr, "Rejected chunk %d (%u:%u)\n", c, chunks[c].offset, chunks[c].size);
#endif
				right = c - 1;
				continue;
			}
			lst = c;
			if (!diff)
				break;
			left = c + 1;
		}
		if (lst < 0) {
			unsigned ll = (s / (sb->size_inc*PAGESIZE) + 1) * PAGESIZE * sb->size_inc;
			// we don't have a suitable chunk
			expand(ll);
			// insert new chunk into list (always succeeds)
			*(unsigned *)(data+sb->size-ll) = ll;
			fast_free(sb->size-ll+sizeof(unsigned));
		}
	} while (lst < 0);

#ifdef NC_DEBUG_ALLOC
	fprintf(stderr, "haluz 7: off = %u size = %u\n", chunks[7].offset, chunks[7].size);
	fprintf(stderr, "Got %u chunk (pos %d), taking %u\n", chunks[lst].size, lst, s);
	fprintf(stderr, "chunk (%u:%u)\n", chunks[lst].offset, chunks[lst].size); 
#endif

	unsigned best = chunks[lst].offset+sizeof(unsigned);
	memset(data+best, 0, s-sizeof(unsigned));
	chunks[lst].size -= s;
	chunks[lst].offset += s;
	CS(best) = s;

	while (lst < ((signed)sb->chunk_ttl - 1) && chunks[lst].size < chunks[lst+1].size) {
		unsigned b = chunks[lst].size;
		unsigned i = lst + 1;
		chunks[lst].size = chunks[i].size;
		chunks[i].size = b;
		b = chunks[lst].offset;
		chunks[lst].offset = chunks[i].offset;
		chunks[i].offset = b;
		lst = i;
	}

#ifdef NC_DEBUG_ALLOC
	fprintf(stderr, "Returned %u:%u\n", best, CS(best));
#endif
	return best;
}

void NConfig::freeChunk(unsigned where)
{
#ifdef NC_DEBUG_ALLOC
	fprintf(stderr, "Free chunk: %u\n", CS(where));
#endif
	if (chunks[sb->chunk_ttl-2].size) {
#ifdef NC_DEBUG_ALLOC
		fprintf(stderr, "Last slot available.\n");
#endif
		unsigned n = getChunk((sb->chunk_ttl+sb->chunk_inc)*sizeof(struct nc_chunk_s));
		unsigned f = sb->chunk;
		memcpy(data+n, chunks, (sb->chunk_ttl-1)*sizeof(struct nc_chunk_s));
		chunks = CM(sb->chunk = n);
		sb->chunk_ttl += sb->chunk_inc;
		fast_free(f);
	}
	fast_free(where);
}

inline unsigned NConfig::alignSize(unsigned s)
{
	unsigned of = s % sizeof(unsigned);
	return of ? s + sizeof(unsigned) - of : s;
}

void NConfig::delKey(const char *name)
{
	_delKey(name, NULL, TRUE);
}

void NConfig::_delKey(const char *name, struct nc_de_s *p, int tosort)
{
	if (fd < 0)
		return;
	lockFile(NC_L_RW);
	struct nc_de_s *nd = getDirEnt(name, p);
	if (nd && nd != rdir && nd != cdir) {
		unsigned ndo = ((char *)nd) - data;
		if (nd->type == NC_DIR)
			for (unsigned i=0; i<DE(ndo)->pages; i++) {
				struct nc_de_s *dd = IDE(nd, i);
				if (dd->type)
					_delKey(data+dd->name, nd, FALSE);
				nd = DE(ndo);
			}
		sb->modtime++;
		freeChunk(nd->offset);
		freeChunk(DE(ndo)->name);
		nd = DE(ndo);
		struct nc_de_s *parent = DE(nd->parent);
		memset(nd, 0, sizeof(struct nc_de_s));
		// keep parent directory sorted
		if (tosort) {
			unsigned i = 0;
			while (i < parent->pages && IDE(parent, i) != nd)
				 i++;
			memmove(((unsigned *)(data+parent->offset))+i,
				((unsigned *)(data+parent->offset))+i+1,
				sizeof(unsigned)*(parent->pages-i-1));
			((unsigned *)(data+parent->offset))[parent->pages-1] = ndo;
		}
	}
	unLockFile();
}

int NConfig::_setKey(const char *name, const unsigned t, const char *value, const unsigned len)
{
	if (fd < 0)
		return NC_ERR_NFILE;
	if (omode != NC_O_RW)
		return NC_ERR_RDONLY;
	lockFile(NC_L_RW);
	struct nc_de_s *nd = getDirEnt(name);
#ifdef NC_DEBUG_INSERT
	fprintf(stderr, "Found DE %p\n", nd);
#endif
	if (!nd) {
		struct nc_de_s *sd = *name == '/' ? rdir : cdir;
		char *parse = canonize(name), *p = parse;
	
		while ((nd = getDirEnt(p, sd)))
			if (nd->type == NC_DIR) {
				sd = nd;
				p += strlen(p)+1;
			} else {
				free(parse);
				unLockFile();
				return NC_ERR_PERM;
			}

		size_t pl = 0;
		struct nc_de_s ds;
		unsigned sdo = ((char *)sd) - data;
		while (*(p+(pl = strlen(p)+1))) {
			ds.pages = ds.offset = 0;
			ds.name = getChunk(pl);
			memcpy(data+ds.name, p, pl);
			ds.type = NC_DIR;
#ifdef NC_DEBUG_INSERT
			fprintf(stderr, "Insertion parent 2: %p\n", DE(sdo));
#endif
			// FIXME: crc calculation
			sdo = ((char *)insert(sdo, &ds)) - data;
			p += pl;
		}
		ds.type = t;
		memcpy(data+(ds.name = getChunk(pl)), p, pl);
		ds.pages = ds.offset = 0;
#ifdef NC_DEBUG_INSERT
		fprintf(stderr, "Insertion parent 1: %p\n", DE(sdo));
#endif
		nd = insert(sdo, &ds);
		sb->modtime++;
		free(parse);
	} else
		if (nd->type != t) {
			unLockFile();
			return NC_ERR_TYPE;
		}
	unsigned ndo = ((char *)nd) - data;
	if (t != NC_DIR) {
		if (value) {
			if (nd->offset && CS(nd->offset)-sizeof(unsigned) < len) {
				freeChunk(nd->offset);
				nd = DE(ndo);
				nd->offset = 0;
			}
			if (nd->offset) {
				if (CS(nd->offset)-sizeof(unsigned) > alignSize(len)+sizeof(unsigned)) {
					unsigned trim = CS(nd->offset) - alignSize(len) - sizeof(unsigned);
					unsigned off = nd->offset + alignSize(len) + sizeof(unsigned);
					CS(off) = trim;
					CS(nd->offset) -= trim;
					freeChunk(off);
					nd = DE(ndo);
				}
			} else {
				unsigned off = getChunk(len);
				nd = DE(ndo);
				nd->offset = off;
			}
			memcpy(data+nd->offset, value, len);
			nd->pages = len;
		} else
			if (nd->offset) {
				freeChunk(nd->offset);
				DE(ndo)->offset = 0;
			}
	} else
		// Preallocate pages for directory
		if (len > nd->pages) {
			unsigned off = getChunk(sizeof(unsigned)*len);
			if (DE(ndo)->offset) {
				memcpy(data+off, data+DE(ndo)->offset, sizeof(unsigned)*(DE(ndo)->pages));
				freeChunk(DE(ndo)->offset);
			}
			DE(ndo)->offset = off;
			for (unsigned al = len - DE(ndo)->pages; al; al--) {
				off = getChunk(sizeof(struct nc_de_s));
				((unsigned *)(data+DE(ndo)->offset))[DE(ndo)->pages++] = off;
			}
		}
	unLockFile();
#ifdef NC_DEBUG_INSERT
	fprintf(stderr, "%p\n", cdir);
#endif
	return NC_ERR_OK;
}

char *NConfig::getName(const struct nc_de_s *w)
{
	if (w == rdir)
		return strdup("/");
	char *parent = getName(DE(w->parent));
	unsigned l1 = strlen(parent);
	unsigned l2 = strlen(data+w->name)+1;

	parent = (char *) realloc(parent, l1 + l2 + (l1 == 1 ? 0 : 1));
	if (l1 != 1) {
		memcpy(parent+l1, "/", 2);
		l1++;
	}
	memcpy(parent+l1, data+w->name, l2);
	return parent;
}

int NConfig::chDir(const char *name)
{
	if (fd < 0)
		return NC_ERR_NFILE;
	lockFile(NC_L_RO);

	int ret = NC_ERR_OK;
	struct nc_de_s *nd = getDirEnt(name);
	if (nd) {
		if (nd->type == NC_DIR) {
			cdir = nd;
			free(cname);
			cname = getName(cdir);
		} else
			ret = NC_ERR_NDIR;
	} else
		ret = NC_ERR_NEXIST;
	unLockFile();
	return ret;
}

const char *NConfig::pwDir()
{
	if (fd < 0)
		return NULL;
	lockFile(NC_L_RO);
	struct nc_de_s *l = cdir;
	char * ret = strdup(data+l->name);
	while (DE(l->parent) != l) {
		unsigned len = CS(l->name);
		char *r = (char *) malloc(strlen(ret) + len + 2);
		memcpy(r, data+l->name, len);
		if (*ret != '/' && DE(l->parent) != rdir)
			strcat(r, "/");
		strcat(r, ret);
		free(ret);
		ret = r;
		l = DE(l->parent);
	}
	unLockFile();
	return ret;
}

struct nc_de_s *NConfig::getDirEnt(const char *name, struct nc_de_s *cc)
{
	struct nc_de_s *ret = cc ? cc : ((*name == '/') ? rdir : cdir);
	char *c = canonize(name), *can;

	if (!(can = c))
		return ret;
	while (*c) {
		if (!strcmp(c, ".."))
			ret = DE(ret->parent);
		else
			if (strcmp(c, ".")) {
				struct nc_de_s *re = ret;
				int left = 0, right = ret->pages-1, p, r;

				ret = NULL;
				while (left <= right) {
					p = (left + right) / 2;
					r = strcmp(c, data+IDE(re, p)->name);
					if (r < 0) {
						left = p + 1;
						continue;
					}
					if (!r) {
						ret = IDE(re, p);
						break;
					}
					right = p - 1;
				}
			}
		c += strlen(c)+1;
		if (!ret || (*c && ret->type != NC_DIR)) {
			ret = NULL;
			break;
		}
	}
	free(can);
	return ret;
}

char *NConfig::canonize(const char *name)
{
	if (*name == '/')
		name++;
	size_t i = strlen(name);
	char *ret = (char *)calloc(1, i+3);
	memcpy(ret, name, i);
	for (size_t j=0; j<i; j++)
		if (ret[j] == '/')
			ret[j] = 0;
	return ret;
}

struct nc_de_s *NConfig::insert(unsigned where, struct nc_de_s *what)
{
#ifdef NC_DEBUG_INSERT
	fprintf(stderr, "Insertion: %s %d\n", data+what->name, what->type);
#endif
	struct nc_de_s *w = DE(where);
	if (!DE(where)->offset || IDE(w, w->pages-1)->type) {
		unsigned a = getChunk((w->pages+sb->ent_inc)*sizeof(unsigned));
		w = DE(where);
		if (w->offset) {
			memcpy(data+a, data+w->offset, w->pages*sizeof(unsigned));
			freeChunk(w->offset);
			w = DE(where);
		}
		w->offset = a;
		for (unsigned ha = 0; ha<sb->ent_inc; ha++) {
			unsigned off = getChunk(sizeof(struct nc_de_s));
			w = DE(where);
			((unsigned *)(data+w->offset))[w->pages] = off;
			w->pages++;
		}
	}
	int i = 0, l = 0, r = w->pages - 1, c;
	while (l <= r) {
		c = (l + r) / 2;
		if (!IDE(w, c)->type || strcmp(data+what->name, data+IDE(w, c)->name) > 0) {
			i = c;
			r = c - 1;
		} else
			l = c + 1;
	}	

#ifdef NC_DEBUG_INSERT
	fprintf(stderr, "Insertion to slot %u (%s)\n", i, data+what->name);
#endif
	what->parent = where;
	unsigned to = ((unsigned *)(data+w->offset))[w->pages-1];
	memmove(((unsigned *)(data+w->offset))+i+1, ((unsigned *)(data+w->offset))+i, sizeof(unsigned)*(w->pages-i-1));
	((unsigned *)(data+w->offset))[i] = to;
	void *ret = memcpy(DE(to), what, sizeof(struct nc_de_s));
	sb->modtime++;
	return (struct nc_de_s *)ret;
}

void NConfig::status()
{
	if (fd < 0)
		return;
	lockFile(NC_L_RO);
	fprintf(stderr, "Size:\t%u\n", sb->size);
	unsigned low=0, hi=chunks[0].size, cnt=0, ttl=0;
	for (unsigned i=0; i<sb->chunk_ttl; i++)
		if (chunks[i].size > 0) {
			if (!low || low > chunks[i].size)
				low = chunks[i].size;
			ttl += chunks[i].size;
			cnt++;
		}
	unLockFile();
	fprintf(stderr, "Free:\t%u in %u chunk%s\n", ttl, cnt, cnt > 1 ? "s" : "");
	if (cnt > 0)
		fprintf(stderr, "Min:\t%u\nAvg:\t%u\nMax:\t%u\n", low, ttl / cnt, hi);
}
	
struct nc_ls_s *NConfig::ls(const char *name)
{
	if (fd < 0)
		return NULL;
	lockFile(NC_L_RO);

	struct nc_ls_s *rt = NULL;
	unsigned count = 0;
	struct nc_de_s *de = NULL;
	struct nc_de_s *ds = name ? getDirEnt(name) : cdir;

	if (ds && ds->type == NC_DIR) {
		for (unsigned i=0; i<ds->pages; i++) {
			de = IDE(ds, i);
			if (de->type && de->name) {
				rt = (struct nc_ls_s *) realloc(rt, (count+2)*sizeof(nc_ls_s));
				rt[count].type = de->type;
				rt[count].name = strdup(data+de->name);
				rt[++count].type = 0;
				rt[count].name = NULL;
			}
		}
	}
	unLockFile();
	return rt;
}

void NConfig::fast_free(unsigned offset)
{
	unsigned s = CS(offset), i = 0;
	offset -= sizeof(unsigned);

	while (1) {
		if (!chunks[i].size) {
#ifdef NC_DEBUG_ALLOC
			fprintf(stderr, "Inserting %u:%u to %u\n", offset, s, i);
#endif
			chunks[i].offset = offset;
			chunks[i].size = s;
			break;
		}
		if (chunks[i].offset == offset + s) {
#ifdef NC_DEBUG_ALLOC
			fprintf(stderr, "Prepending %u:%u to %u (%u:%u)\n", offset, s, i, chunks[i].offset, chunks[i].size);
#endif
			chunks[i].offset -= s;
			chunks[i].size += s;
			break;
		}
		if (offset == chunks[i].offset + chunks[i].size) {
#ifdef NC_DEBUG_ALLOC
			fprintf(stderr, "Appending  %u:%u to %u (%u:%u)\n", offset, s, i, chunks[i].offset, chunks[i].size);
#endif
			chunks[i].size += s;
			break;
		}
		i++;
	}

	// Keep the array sorted
	while (i && chunks[i].size > chunks[i-1].size) {
		unsigned b = chunks[i].size;
		unsigned j = i - 1;
		chunks[i].size = chunks[j].size;
		chunks[j].size = b;
		b = chunks[i].offset;
		chunks[i].offset = chunks[j].offset;
		chunks[j].offset = b;
		i = j;
	}
}

int NConfig::renameKey(const char *oldname, const char *newname)
{
	if (fd < 0)
		return NC_ERR_NFILE;
	if (omode != NC_O_RW)
		return NC_ERR_RDONLY;
	lockFile(NC_L_RW);
	int ret = NC_ERR_OK;
	struct nc_de_s *parent, *nd = getDirEnt(newname);
	if (nd) {
		if ((nd = getDirEnt(oldname))) {
			size_t len = strlen(newname)+1;
			int inc = strcmp(oldname, newname);
			unsigned i, off, pos, ndo = ((char *)nd) - data;
			if (alignSize(len) != CS(nd->name)) {
				freeChunk(nd->name);
				off = getChunk(len);
				DE(ndo)->name = off;
				nd = DE(ndo);
			}
			memcpy(data+nd->name, newname, len);
			parent = DE(nd->parent);
			for (pos = 0; pos < parent->pages && IDE(parent, pos) != nd; pos++)
				;
			for (i = pos; i>=0 && i<parent->pages; i += inc)
				if (strcmp(data+IDE(parent, i)->name, newname) != inc)
					break;
			if (inc == -1)
				memmove(((unsigned *)(data+parent->offset))+i+1,
					((unsigned *)(data+parent->offset))+i,
					sizeof(unsigned)*(pos - i));
			else
				memmove(((unsigned *)(data+parent->offset))+pos,
					((unsigned *)(data+parent->offset))+pos+1,
					sizeof(unsigned)*(i-pos));
			((unsigned *)(data+parent->offset))[i] = ndo;
			sb->modtime++;
		} else
			ret = NC_ERR_NEXIST;
	} else
		ret = NC_ERR_PERM;
	unLockFile();
	return NC_ERR_OK;
}

int NConfig::createDir(const char *name, unsigned entries)
{
	return _setKey(name, NC_DIR, NULL, entries);
}

int NConfig::setKey(const char *name, const unsigned long long value)
{
	return _setKey(name, NC_UINT, (const char *)&value, sizeof(value));
}

int NConfig::setKey(const char *name, const unsigned value)
{
	unsigned long long b = value;
	return _setKey(name, NC_UINT, (const char *)&b, sizeof(b));
}

int NConfig::setKey(const char *name, const signed long long value)
{
	return _setKey(name, NC_INT, (const char *)&value, sizeof(value));
}

int NConfig::setKey(const char *name, const int value)
{
	signed long long b = value;
	return _setKey(name, NC_INT, (const char *)&b, sizeof(b));
}

int NConfig::setKey(const char *name, const char *value)
{
	return _setKey(name, NC_STRING, value, strlen(value)+1);
}

int NConfig::setKey(const char *name, const long double value)
{
	return _setKey(name, NC_DOUBLE, (const char *)&value, sizeof(value));
}

int NConfig::setKey(const char *name, const double value)
{
	long double b = value;
	return _setKey(name, NC_DOUBLE, (const char *)&b, sizeof(b));
}

int NConfig::setKey(const char *name, const char *value, const unsigned len)
{
	if (!value && len)
		return NC_ERR_NVAL;
	if (!len)
		return _setKey(name, NC_RAW, NULL, 0);
	return _setKey(name, NC_RAW, value, len);
}

int NConfig::getKey(const char *name, unsigned long long &value)
{
	if (fd < 0)
		return NC_ERR_NFILE;
	lockFile(NC_L_RO);
	int ret = NC_ERR_OK;
	struct nc_de_s *k = getDirEnt(name);
	if (k) {
		if (k->type == NC_UINT) {
			memcpy(&value, data+k->offset, sizeof(value));
		} else
			ret = NC_ERR_TYPE;
	} else
		ret = NC_ERR_NEXIST;
	unLockFile();
	return ret;
}

int NConfig::getKey(const char *name, unsigned &value)
{
	if (fd < 0)
		return NC_ERR_NFILE;
	lockFile(NC_L_RO);
	int ret = NC_ERR_OK;
	struct nc_de_s *k = getDirEnt(name);
	if (k) {
		if (k->type == NC_UINT) {
			unsigned long long b;
			memcpy(&b, data+k->offset, sizeof(b));
			value = b;
		} else
			ret = NC_ERR_TYPE;
	} else
		ret = NC_ERR_NEXIST;
	unLockFile();
	return ret;
}

int NConfig::getKey(const char *name, long double &value)
{
	if (fd < 0)
		return NC_ERR_NFILE;
	lockFile(NC_L_RO);
	int ret = NC_ERR_OK;
	struct nc_de_s *k = getDirEnt(name);
	if (k) {
		if (k->type == NC_DOUBLE) {
			memcpy(&value, data+k->offset, sizeof(value));
		} else
			ret = NC_ERR_TYPE;
	} else
		ret = NC_ERR_NEXIST;
	unLockFile();
	return ret;
}

int NConfig::getKey(const char *name, double &value)
{
	if (fd < 0)
		return NC_ERR_NFILE;
	lockFile(NC_L_RO);
	int ret = NC_ERR_OK;
	struct nc_de_s *k = getDirEnt(name);
	if (k) {
		if (k->type == NC_DOUBLE) {
			long double b;
			memcpy(&b, data+k->offset, sizeof(b));
			value = b;
		} else
			ret = NC_ERR_TYPE;
	} else
		ret = NC_ERR_NEXIST;
	unLockFile();
	return ret;
}

int NConfig::getKey(const char *name, signed long long &value)
{
	if (fd < 0)
		return NC_ERR_NFILE;
	lockFile(NC_L_RO);
	int ret = NC_ERR_OK;
	struct nc_de_s *k = getDirEnt(name);
	if (k) {
		if (k->type == NC_INT) {
			memcpy(&value, data+k->offset, sizeof(value));
		} else
			ret = NC_ERR_TYPE;
	} else
		ret = NC_ERR_NEXIST;
	unLockFile();
	return ret;
}

int NConfig::getKey(const char *name, int &value)
{
	if (fd < 0)
		return NC_ERR_NFILE;
	lockFile(NC_L_RO);
	int ret = NC_ERR_OK;
	struct nc_de_s *k = getDirEnt(name);
	if (k) {
		if (k->type == NC_INT) {
			signed long long b;
			memcpy(&b, data+k->offset, sizeof(b));
			value = b;
		} else
			ret = NC_ERR_TYPE;
	} else
		ret = NC_ERR_NEXIST;
	unLockFile();
	return ret;
}

int NConfig::getKey(const char *name, char *&value)
{
	if (fd < 0)
		return NC_ERR_NFILE;
	lockFile(NC_L_RO);
	int ret = NC_ERR_OK;
	struct nc_de_s *k = getDirEnt(name);
	if (k) {
		if (k->type == NC_STRING) {
			if (k->offset) {
				if (!(value = strdup(data+k->offset)))
					ret = NC_ERR_NMEM;
			} else
				value = NULL;
		} else
			ret = NC_ERR_TYPE;
	} else
		ret = NC_ERR_NEXIST;
	unLockFile();
	return ret;
}

int NConfig::getKey(const char *name, char *&value, unsigned &len)
{
	if (fd < 0)
		return NC_ERR_NFILE;
	lockFile(NC_L_RO);
	int ret = NC_ERR_OK;
	struct nc_de_s *k = getDirEnt(name);
	if (k) {
		if (k->type == NC_RAW) {
			if (k->offset) {
				len = k->pages;
				value = (char *)malloc(len);
				memcpy(value, data+k->offset, len);
			} else {
				len = 0;
				value = NULL;
			}
		} else
			ret = NC_ERR_TYPE;
	} else
		ret = NC_ERR_NEXIST;
	unLockFile();
	return ret;
}

void NConfig::lockFile(int type, int force)
{
#ifdef NC_DEBUG_LOCK
	fprintf(stderr, "Lock called type=%d force=%d lock=%d olck=%u\n", type, force, lock, olck);
#endif
	if (lock == NC_L_RO && type == NC_L_RW) {
		fprintf(stderr, "Lock promotion is not possible.\n");
		abort();
	}
	if (lock != NC_L_NONE) {
		olck++;
		return;
	}
	
	struct flock flc = { type == NC_L_RW ? F_WRLCK : F_RDLCK, SEEK_SET, 0, 0, 0 };
	while (fcntl(fd, F_SETLKW, &flc)) {
		sched_yield();
		flc.l_type = type == NC_L_RW ? F_WRLCK : F_RDLCK;
		flc.l_whence = SEEK_SET;
		flc.l_len = flc.l_start = 0;
	}

#ifdef NC_DEBUG_LOCK
	fprintf(stderr, "Locked %u %u %s\n", sb->modtime, update, force ? "forced." : "");
#endif
	if (careful && type == NC_L_RW)
		mprotect(data, sb->size, PROT_READ | PROT_WRITE);
	lock = type;
	olck = 0;
	if (sb->modtime != update || force) {
		// refresh memory mapping
		if (lsize != sb->size) {
			_remap(lsize, sb->size);
			lsize = sb->size;
			chunks = CM(sb->chunk);
		}
		cdir = getDirEnt(cname);
		update = sb->modtime;
	}
}

void NConfig::unLockFile()
{
#ifdef NC_DEBUG_LOCK
	fprintf(stderr, "UnLock called lock=%u olck=%u\n", lock, olck);
#endif
	if (olck) {
		olck--;
		return;
	}
	if (lock == NC_L_NONE)
		return;
	struct flock flc = {F_UNLCK, SEEK_SET, 0, 0, 0 };
	update = sb->modtime;
#ifdef NC_DEBUG_LOCK
	fprintf(stderr, "Unlock %u\n", update);
#endif
	if (careful)
		mprotect(data, sb->size, PROT_READ);
	fcntl(fd, F_SETLK, &flc);
	lock = NC_L_NONE;
	olck = 0;
}

void NConfig::_remap(const size_t osize, const size_t nsize)
{
	data = (char *) mremap(data, osize, nsize, 1);
	if (data == MAP_FAILED) {
		perror("mremap");
		abort();
	}
	sb = SB;
	rdir = DE(sb->root);
}

char * NConfig::version()
{
	return strdup("EliteDVB registry");
}

