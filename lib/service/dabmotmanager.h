/*
    DABlin - capital DAB experience
    Copyright (C) 2016-2022 Stefan Pöschel

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

#ifndef __lib_service_dabmotmanager_h
#define __lib_service_dabmotmanager_h

#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <string>
#include <map>
#include <vector>

#include <lib/service/dabpadtools.h>

namespace DABlinPAD
{


// --- MOT_FILE -----------------------------------------------------------------
struct MOT_FILE {
	std::vector<uint8_t> data;

	// from header core
	size_t body_size;
	int content_type;
	int content_sub_type;

	// from header extension
	std::string content_name;
	std::string content_name_charset;
	std::string category_title;
	std::string click_through_url;
	bool trigger_time_now;

	static const int CONTENT_TYPE_IMAGE			= 0x02;
	static const int CONTENT_TYPE_MOT_TRANSPORT	= 0x05;
	static const int CONTENT_SUB_TYPE_JFIF			= 0x001;
	static const int CONTENT_SUB_TYPE_PNG			= 0x003;
	static const int CONTENT_SUB_TYPE_HEADER_UPDATE	= 0x000;

	MOT_FILE() :
		body_size(0),
		content_type(-1),
		content_sub_type(-1),
		trigger_time_now(false)
	{}
};


typedef std::vector<uint8_t> seg_t;
typedef std::map<int,seg_t> segs_t;

// --- MOTEntity -----------------------------------------------------------------
class MOTEntity {
private:
	segs_t segs;
	int last_seg_number;
	size_t size;
public:
	MOTEntity() {Reset();}
	void Reset() {
		segs.clear();
		last_seg_number = -1;
		size = 0;
	}

	void AddSeg(int seg_number, bool last_seg, const uint8_t* data, size_t len);
	bool IsFinished();
	size_t GetSize() {return size;}
	std::vector<uint8_t> GetData();
};


// --- MOTObject -----------------------------------------------------------------
class MOTObject {
private:
	MOTEntity header;
	MOTEntity body;
	bool header_received;
	bool shown;

	MOT_FILE result_file;

	bool ParseCheckHeader(MOT_FILE& target_file);
public:
	MOTObject(): header_received(false), shown(false) {}

	void AddSeg(bool dg_type_header, int seg_number, bool last_seg, const uint8_t* data, size_t len);
	bool IsToBeShown();
	MOT_FILE GetFile() {return result_file;}

	size_t GetCurrentBodySize() {return body.GetSize();}
	size_t GetTotalBodySize() {return result_file.body_size;}
};


// --- MOTManagerObserver -----------------------------------------------------------------
class MOTManagerObserver {
public:
	virtual ~MOTManagerObserver() {}

	virtual void MOTFileCompleted(const MOT_FILE& /*file*/) {}
	virtual void MOTFileProgress(const double /*fraction*/) {}
};


// --- MOTManager -----------------------------------------------------------------
class MOTManager {
private:
	MOTManagerObserver *observer;

	MOTObject object;
	int current_transport_id;

	bool ParseCheckDataGroupHeader(const std::vector<uint8_t>& dg, size_t& offset, int& dg_type);
	bool ParseCheckSessionHeader(const std::vector<uint8_t>& dg, size_t& offset, bool& last_seg, int& seg_number, int& transport_id);
	bool ParseCheckSegmentationHeader(const std::vector<uint8_t>& dg, size_t& offset, size_t& seg_size);
public:
	MOTManager(MOTManagerObserver *observer) : observer(observer) {Reset();}

	void Reset();
	void HandleMOTDataGroup(const std::vector<uint8_t>& dg);
};

}

#endif /* __lib_service_dabmotmanager_h */
