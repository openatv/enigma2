#ifndef NC_NCONFIG_H
#define NC_NCONFIG_H	1

#include <stdio.h>
#include <stdlib.h>

/*
 * Superblock definitions
 */
#define NC_SB_MAGIC		("\0\11\22")			// Superblock identifier

/*
 * Key type definitions
 */
#define NC_DIR			0x01	// The key is a directory
#define NC_STRING		0x02	// The key contains a string
#define NC_INT			0x03	// The key contains a signed integer
#define NC_UINT			0x04	// The key contains an unsigned integer
#define NC_RAW			0x05	// The key contains raw data
#define NC_DOUBLE		0x06	// The key contains a double
#define NC_LINK			0x07	// The key points somewhere else

/*
 * File access definitions
 */
#define NC_O_RO			0x01	// Open file in read-only mode
#define NC_O_RW			0x02	// Open file in read-write mode

/*
 * Lock types
 */
#define NC_L_NONE		0x00	// No lock
#define NC_L_RO			0x01	// Read-only lock
#define	NC_L_RW			0x02	// Read-write lock

/*
 * Error codes
 */
#define NC_ERR_OK		  	0		// Everything is OK
#define NC_ERR_TYPE		 -1		// Type mismatch
#define NC_ERR_NDIR		 -2		// Key is not a directory
#define NC_ERR_PERM		 -3		// Operation is not allowed
#define NC_ERR_NMEM		 -4		// Not enough memory to complete operation
#define NC_ERR_NEXIST	 -5		// Key does not exist
#define NC_ERR_NFILE	 -6		// No file is assigned/open
#define NC_ERR_CORRUPT -7		// File is corrupted
#define NC_ERR_NVAL		 -8		// Invalid value
#define NC_ERR_RDONLY	 -9		// File is open in read-only mode
#define NC_ERR_NOSUPPORT -10	// Support is not compiled-in

/*
 * Truth value definitions
 */
#ifndef TRUE
#define TRUE			1
#endif
#ifndef FALSE
#define FALSE			0
#endif

/*
 * Header of the config file.
 */
struct nc_sb_s {
	char magic[4];		// superblock magic
	unsigned size;		// Current file size
	unsigned ent_inc;	// directory increment
	unsigned chunk_inc;	// Memory chunks increment
	unsigned size_inc;	// file size increment
	unsigned chunk_ttl;	// size of chunkmap
	unsigned chunk;		// pointer to chunkmap
	unsigned root;		// pointer to root direntry
	unsigned modtime;	// file version
};

/*
 * Free chunk descriptor
 */
struct nc_chunk_s {
	unsigned offset;
	unsigned size;
};

/*
 *  In-file directory entry
 */
struct nc_de_s {
	unsigned name;
	unsigned type;
	unsigned parent;
	unsigned offset;
	unsigned pages;
	unsigned crc;
};

/*
 * Ls reporting
 */
struct nc_ls_s {
	const char *name;
	unsigned type;
};

class NConfig
{
public:
		/*
		 * Class constructor
		 * pass TRUE as parameter to enable
		 * write protection when leaving library
		 */
		NConfig(int protect = FALSE);
		virtual ~NConfig();
		
		/*
		 * Set file name (prior to open)
		 * Errors:
		 * NC_ERR_PERM	file is already open
		 * NC_ERR_NVAL	no file name is given
		 */
		int setName(const char *name);

		/*
		 * Open the configuration file, re-open it
		 * Errors:
		 * NC_ERR_NFILE		no file name is assigned
		 * NC_ERR_TYPE		file open mode is invalid
		 * NC_ERR_PERM		file cannot be opened/created
		 * NC_ERR_NMEM		unable to mmap the file
		 * NC_ERR_CORRUPT	superblock magic mismatch
		 */
		int open(const int how = NC_O_RW);

		/*
		 * Close the configuration file
		 * No errors defined
		 */
		void close();
		
		void flush(); // flush file if not mmap'ed
		
		/*
		 * Create a new file
		 * resize is filesize increment is system pages
		 * dirent is directory increment
		 * mchunks is memory block increment
		 * Errors:
		 * NC_ERR_PERM		file already exists
		 * NC_ERR_NFILE		cannot create new file
		 * NC_ERR_NVAL		file is already open
		 */
		int createNew(unsigned resize = 4, unsigned dirent = 32, unsigned mchunks = 32);

		/*
		 * Get an unsigned integer
		 * Errors:
		 * NC_ERR_NFILE		no file is open
		 * NC_ERR_NEXIST	the key does not exist
		 * NC_ERR_TYPE		the key exists, but is of different type
		 */
		int getKey(const char *name, unsigned &value);
		int getKey(const char *name, unsigned long long &value);

		/*
		 * Get a signed integer
		 * Errors:
		 * NC_ERR_NFILE		no file is open
		 * NC_ERR_NEXIST	the key does not exist
		 * NC_ERR_TYPE		the key exists, but is of different type
		 */
		int getKey(const char *name, int &value);
		int getKey(const char *name, signed long long &value);

		/*
		 * Get a string
		 * Errors:
		 * NC_ERR_NFILE		no file is open
		 * NC_ERR_NEXIST	the key does not exist
		 * NC_ERR_TYPE		the key exists, but is of different type
		 */
		int getKey(const char *name, char *&value);

		/*
		 * Get a long double
		 * Errors:
		 * NC_ERR_NFILE		no file is open
		 * NC_ERR_NEXIST	the key does not exist
		 * NC_ERR_TYPE		the key exists, but is of different type
		 */
		int getKey(const char *name, double &value);
		int getKey(const char *name, long double &value);
		
		/*
		 * Get raw data
		 * Errors:
		 * NC_ERR_NFILE		no file is open
		 * NC_ERR_NEXIST	the key does not exist
		 * NC_ERR_TYPE		the key exists, but is of different type
		 */
		int getKey(const char *name, char *&value, unsigned &len);

		/*
		 * Insert an unsigned integer
		 * NC_ERR_NFILE		no file is open
		 * NC_ERR_RDONLY	file is open in read-only mode
		 * NC_ERR_PERM		intermediate key is not a directory
		 * NC_ERR_TYPE		key already exists, but is not an usigned integer
		 * NC_ERR_NEXIST	key does not exist (should NEVER happen)
		 */
		int setKey(const char *name, const unsigned value);
		int setKey(const char *name, const unsigned long long value);
		
		/*
		 * Insert an integer
		 * NC_ERR_NFILE		no file is open
		 * NC_ERR_RDONLY	file is open in read-only mode
		 * NC_ERR_PERM		intermediate key is not a directory
		 * NC_ERR_TYPE		key already exists, but is not a signed integer
		 * NC_ERR_NEXIST	key does not exist (should NEVER happen)
		 */
		int setKey(const char *name, const int value);
		int setKey(const char *name, const signed long long value);
		
		/*
		 * Insert a string
		 * NC_ERR_NFILE		no file is open
		 * NC_ERR_RDONLY	file is open in read-only mode
		 * NC_ERR_PERM		intermediate key is not a directory
		 * NC_ERR_TYPE		key already exists, but is not a string
		 * NC_ERR_NEXIST	key does not exist (should NEVER happen)
		 */
		int setKey(const char *name, const char *value);

		/*
		 * Insert raw data
		 * NC_ERR_NFILE		no file is open
		 * NC_ERR_RDONLY	file is open in read-only mode
		 * NC_ERR_PERM		intermediate key is not a directory
		 * NC_ERR_TYPE		key already exists, but is not raw data
		 * NC_ERR_NEXIST	key does not exist (should NEVER happen)
		 */
		int setKey(const char *name, const char *value, const unsigned len);
		
		/*
		 * Insert a double
		 * NC_ERR_NFILE		no file is open
		 * NC_ERR_RDONLY	file is open in read-only mode
		 * NC_ERR_PERM		intermediate key is not a directory
		 * NC_ERR_TYPE		key already exists, but is not raw data
		 * NC_ERR_NEXIST	key does not exist (should NEVER happen)
		 */
		int setKey(const char *name, const double value);
		int setKey(const char *name, const long double value);
		
		/*
		 * Rename a key
		 * Errors:
		 * NC_ERR_NFILE		no file is open
		 * NC_ERR_RDONLY	file is open read-only
		 * NC_ERR_NEXIST	the key does not exist
		 * NC_ERR_PERM		key with specified name already exists
		 */
		int renameKey(const char *oldname, const char *newname);

		/*
		 * Delete a key
		 * No errors defined
		 */
		void delKey(const char *name);

		/*
		 * Create a directory
		 * entries parameter specifies number of direntries to preallocate
		 * Errors:
		 * NC_ERR_NFILE		no file is open
		 * NC_ERR_RDONLY	file is open in read-only mode
		 * NC_ERR_PERM		intermediate key is not a directory
		 * NC_ERR_TYPE		key already exists, but is not a directory
		 * NC_ERR_NEXIST	key does not exist (should NEVER happen)
		 */
		int createDir(const char *name, unsigned entries = 0);

		/*
		 * Change working directory
		 * Errors:
		 * NC_ERR_NFILE		no file is open
		 * NC_ERR_NDIR		target key is not a directory
		 * NC_ERR_NEXIST	target key direcotry does not exist
		 */
		int chDir(const char *name);

		/*
		 * Print working directory
		 * Errors:
		 * Returns NULL on error
		 */
		const char *pwDir();

		/*
		 * List all keys in current/specified directory
		 * Result is a NULL-terminated array of nc_ls_s
		 * structures.
		 * Errors:
		 * Returns NULL on error
		 * Note:
		 * You need to free the returned pointer,
		 * as well as all the names in it.
		 */
		struct nc_ls_s *ls(const char *dir = NULL);
	
		/*
		 * Lock file
		 * This will block until lock becomes available
		 * type is either:
		 * 		NC_L_RO	for read-only lock
		 * 		NC_L_RW for read-write lock
		 * No errors defined
		 *
		 * NOTE: lock may get promoted
		 */
		void lockFile(int type, int force = FALSE);

		/*
		 * Unlock file
		 * No errors defined
		 */
		void unLockFile();
	
		/*
		 * Print out (to stderr) information about current file
		 * No errors defined
		 */
		void status();

		/*
		 * Return version string
		 */
		static char *version();

		/*
		 * Dump current file to XML
		 * Errors:
		 * NC_ERR_NFILE		no file is open
		 * NC_ERR_PERM		could not write XML output
		 */
		int toXML(const char *filename);

		/*
		 * Load XML to current file
		 * a file has to be open
		 * force can be
		 * 	TRUE - existing keys will be deleted
		 * 	FALSE - import will ignore a key if existing key type conflicts
		 * Errors:
		 * NC_ERR_NFILE		no file is open
		 * NC_ERR_PERM		file is open read-only
		 */
		int fromXML(const char *filename, int force = TRUE);
		
protected:
		int fd, omode, lock, careful;
		char *fname, *data, *cname;
		unsigned lsize, update;
		unsigned revision, olck;
		struct nc_sb_s *sb;
		struct nc_de_s *rdir, *cdir;
		struct nc_chunk_s *chunks;
		
		int _setKey(const char *, const unsigned, const char *, const unsigned);
		void _delKey(const char *, struct nc_de_s *, int);
		void expand(unsigned);
		
		void fast_free(unsigned);

		unsigned getChunk(unsigned);
		void freeChunk(unsigned);
		static inline unsigned alignSize(unsigned);

		struct nc_de_s *getDirEnt(const char *, struct nc_de_s * = NULL);
		struct nc_de_s *insert(unsigned, struct nc_de_s *);
		char *canonize(const char *);
		char *getName(const struct nc_de_s *);

		void _remap(const size_t, const size_t);

		inline unsigned crc(const char *, unsigned);
		void store(nc_de_s *, FILE *);
		void restore(void *, int);
};

#endif /* NC_NCONFIG_H */

