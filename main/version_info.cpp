#include "version_info.h"
#include "version.h"

#ifndef ENIGMA2_COMMIT_DATE
#define ENIGMA2_COMMIT_DATE __DATE__
#endif
const char *enigma2_date = ENIGMA2_COMMIT_DATE;

#ifndef ENIGMA2_BRANCH
#define ENIGMA2_BRANCH "(no branch)"
#endif
const char *enigma2_branch = ENIGMA2_BRANCH;

const char *enigma2_version = (ENIGMA2_COMMIT_DATE "-" ENIGMA2_BRANCH);
