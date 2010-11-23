#include "version_info.h"
#include "version.h"

#ifndef ENIGMA2_LAST_CHANGE_DATE
#define ENIGMA2_LAST_CHANGE_DATE __DATE__
#endif
const char *enigma2_date = ENIGMA2_LAST_CHANGE_DATE;

#ifndef ENIGMA2_BRANCH
#define ENIGMA2_BRANCH "HEAD"
#endif
const char *enigma2_branch = ENIGMA2_BRANCH;

#ifndef ENIGMA2_REV
#define ENIGMA2_REV ""
#endif
const char *enigma2_rev = ENIGMA2_REV;

