#ifndef _python_helpers
#define _python_helpers

#include <lib/python/python.h>
#include <lib/dvb/idvb.h>
#include <lib/service/iservice.h>

void PutToDict(ePyObject &dict, const char *key, long value);
void PutToDict(ePyObject &dict, const char *key, ePyObject item);
void PutToDict(ePyObject &dict, const char *key, const char *value);

void frontendDataToDict(ePyObject &dest, ePtr<iDVBFrontendData> data);
void frontendStatusToDict(ePyObject &dest, ePtr<iDVBFrontendStatus> status);
void transponderDataToDict(ePyObject &dest, ePtr<iDVBTransponderData> data);
void streamingDataToDict(ePyObject &dest, ePtr<iStreamData> data);

#endif
