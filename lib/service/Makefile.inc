noinst_LIBRARIES += service/libenigma_service.a

service_libenigma_service_a_CXXFLAGS = \
	$(LIBXINE_CFLAGS)

service_libenigma_service_a_SOURCES = \
	service/event.cpp \
	service/listboxservice.cpp \
	service/service.cpp \
	service/servicedvb.cpp \
	service/servicedvbrecord.cpp \
	service/servicefs.cpp \
	service/servicemp3.cpp \
	service/servicemp3record.cpp \
	service/servicem2ts.cpp \
	service/servicedvbstream.cpp \
	service/servicehdmi.cpp

serviceincludedir = $(pkgincludedir)/lib/service
serviceinclude_HEADERS = \
	service/event.h \
	service/iservice.h \
	service/listboxservice.h \
	service/service.h \
	service/servicedvb.h \
	service/servicedvbrecord.h \
	service/servicefs.h \
	service/servicemp3.h \
	service/servicemp3record.h \
	service/servicem2ts.h \
	service/servicedvbstream.h \
	service/servicehdmi.h

if HAVE_LIBXINE
service_libenigma_service_a_SOURCES += \
	service/servicexine.cpp
serviceinclude_HEADERS += \
	service/servicexine.h
endif

if HAVE_LIBDDVD
service_libenigma_service_a_SOURCES += \
	service/servicedvd.cpp
serviceinclude_HEADERS += \
	service/servicedvd.h
endif