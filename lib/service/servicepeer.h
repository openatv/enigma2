#pragma once
#include <lib/python/python.h>

#ifndef SWIG
void init_servicepeer();
void done_servicepeer();
#endif

PyObject *getPeerStreamingBoxes();
