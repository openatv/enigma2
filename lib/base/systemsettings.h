// System settings functions, to be exported into Enigma using SWIG

// Implemented in lib/base/filepush.cpp
int getFlushSize(void);
void setFlushSize(int size);

// Implemented in lib/dvb/demux.cpp
int getDemuxSize(void);
void setDemuxSize(int size);
