#include "etimezone.h"

#include <time.h>

etimezone::etimezone()
{
	tzset();
}
