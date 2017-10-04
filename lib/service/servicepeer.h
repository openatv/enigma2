#pragma once
#include <lib/python/python.h>

#ifndef SWIG
# include <string>
void init_servicepeer();
void done_servicepeer();
bool getAnyPeerStreamingBox(std::string &result);
#endif

PyObject *getPeerStreamingBoxes();
