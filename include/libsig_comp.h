#ifndef __LIBSIG_COMP_H
#define __LIBSIG_COMP_H

#include <sigc++/sigc++.h>

#define CONNECT(_signal, _slot) _signal.connect(sigc::mem_fun(*this, &_slot))
#define CONNECT_EXTRA(_signal, _slot, extra_args...) _signal.connect(bind(sigc::mem_fun(*this, &_slot), extra_args))

#endif // __LIBSIG_COMP_H
