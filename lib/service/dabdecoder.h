#ifndef __lib_service_dabdecoder_h
#define __lib_service_dabdecoder_h

#include <cstddef>
#include <cstdint>
#include <functional>
#include <map>
#include <memory>
#include <string>
#include <vector>

#include <lib/service/dabpaddecoder.h>

class eDABDecoder : private DABlinPAD::PADDecoderObserver
{
public:
	typedef std::function<void(const uint8_t *, size_t, const uint8_t *, size_t, uint64_t, uint8_t)> AudioCallback;
	typedef std::function<void(const uint8_t *, size_t, int)> ImageCallback;
	typedef std::function<void(const uint8_t *, size_t, int, int,
		const std::string &, uint16_t)> MOTCallback;
	struct ServiceInfo
	{
		uint32_t serviceId;
		int bitrate;
		bool dabplus;
		std::string label;
	};

	eDABDecoder(uint32_t serviceId, uint16_t ensembleId, const AudioCallback &audioCallback,
		const ImageCallback &imageCallback, const MOTCallback &motCallback);
	~eDABDecoder();

	void feedEDI(const uint8_t *data, size_t length);
	void feedETI(const uint8_t *data, size_t length);

	uint64_t afPackets() const { return m_af_packets; }
	uint64_t etiFrames() const { return m_eti_frames; }
	uint64_t ficFrames() const { return m_fic_frames; }
	uint64_t mscFrames() const { return m_msc_frames; }
	uint64_t audioFrames() const { return m_audio_frames; }
	uint64_t crcErrors() const { return m_crc_errors; }
	uint64_t padPackets() const { return m_pad_packets; }
	uint64_t dlsLabels() const { return m_dls_labels; }
	uint64_t motSegments() const { return m_pad_decoder.GetMOTSegments(); }
	uint64_t motDataGroups() const { return m_pad_decoder.GetMOTDataGroups(); }
	uint64_t slides() const { return m_slides; }
	int slideFormat() const { return m_slide_format; }
	int bitrate() const { return m_selected_bitrate; }
	bool serviceFound() const { return m_selected_subchannel >= 0; }
	bool isDABPlus() const { return m_selected_dabplus; }
	const std::string &serviceLabel() const { return m_service_label; }
	const std::string &ensembleLabel() const { return m_ensemble_label; }
	const std::string &dynamicLabel() const { return m_dynamic_label; }
	const std::string &dlPlusItemTitle() const { return m_dl_plus_item_title; }
	const std::string &dlPlusItemArtist() const { return m_dl_plus_item_artist; }
	const std::string &dlPlusItemGenre() const { return m_dl_plus_item_genre; }
	const std::string &dlPlusProgrammeNow() const { return m_dl_plus_programme_now; }
	const std::string &dlPlusProgrammeNext() const { return m_dl_plus_programme_next; }
	const std::string &dlPlusProgrammePart() const { return m_dl_plus_programme_part; }
	const std::string &dlPlusProgrammeHost() const { return m_dl_plus_programme_host; }
	uint64_t dlPlusRevision() const { return m_dl_plus_revision; }
	uint16_t ensembleId() const { return m_ensemble_id; }
	uint64_t serviceRevision() const { return m_service_revision; }
	std::vector<ServiceInfo> serviceList() const;

private:
	struct Stream
	{
		int subchannel;
		int startAddress;
		std::vector<uint8_t> data;
	};

	struct Subchannel
	{
		int startAddress;
		int size;
		int bitrate;
		Subchannel() : startAddress(-1), size(0), bitrate(0) { }
	};

	struct Service
	{
		int subchannel;
		bool dabplus;
		std::string label;
		Service() : subchannel(-1), dabplus(false) { }
	};

	struct PacketComponent
	{
		uint32_t serviceId;
		int serviceComponent;
		int subchannel;
		int dataServiceType;
		int packetAddress;
		int applicationType;
		bool dataGroups;
		bool logged;
		PacketComponent()
			: serviceId(0), serviceComponent(-1), subchannel(-1), dataServiceType(-1),
			  packetAddress(-1), applicationType(-1), dataGroups(false), logged(false) { }
	};

	struct PFCollection
	{
		uint32_t fragmentCount;
		uint16_t nominalLength;
		bool fec;
		uint8_t rsk;
		uint8_t rsz;
		bool addressed;
		uint16_t source;
		uint16_t destination;
		std::vector<std::vector<uint8_t> > fragments;
		size_t received;
		uint64_t arrival = 0;
		PFCollection();
	};

	void processAF(const uint8_t *data, size_t length);
	size_t processPF(const uint8_t *data, size_t length);
	void processTags(const uint8_t *data, size_t length);
	void parseFIC(const uint8_t *data, size_t length);
	void parseFIG0(const uint8_t *data, size_t length);
	void parseFIG1(const uint8_t *data, size_t length);
	void reportPacketComponent(uint16_t componentId);
	void resolveService();
	void feedMSC(const std::vector<Stream> &streams);
	void feedDABPlus(const uint8_t *data, size_t length);
	void processSuperframe();
	void inspectPAD(const uint8_t *data, size_t length);
	void emitLOAS(const uint8_t *data, size_t length, uint8_t config, uint64_t durationNs);
	void PADChangeDynamicLabel(const DABlinPAD::DL_STATE &label) override;
	void PADChangeSlide(const DABlinPAD::MOT_FILE &slide) override;
	bool reconstructPF(uint16_t sequence, PFCollection &collector, std::vector<uint8_t> &af);
	void trimPFCollectors();

	static uint16_t read16(const uint8_t *data);
	static uint32_t read24(const uint8_t *data);
	static uint32_t read32(const uint8_t *data);
	static uint16_t crc16(uint16_t crc, const uint8_t *data, size_t length, uint16_t polynomial);
	static bool checkInvertedCRC(const uint8_t *data, size_t length);
	static bool checkFireCode(const uint8_t *data, size_t length);
	static std::string decodeLabel(const uint8_t *data, size_t length, int charset);

	uint32_t m_service_id;
	uint16_t m_ensemble_id;
	AudioCallback m_audio_callback;
	ImageCallback m_image_callback;
	MOTCallback m_mot_callback;
	DABlinPAD::PADDecoder m_pad_decoder;
	std::map<uint16_t, PFCollection> m_pf_collectors;
	uint64_t m_pf_arrival = 0;
	std::map<int, Subchannel> m_subchannels;
	std::map<uint32_t, Service> m_services;
	std::map<uint16_t, PacketComponent> m_packet_components;
	std::map<uint16_t, std::unique_ptr<class eDABPacketDecoder> > m_packet_decoders;
	std::string m_service_label;
	std::string m_ensemble_label;
	int m_selected_subchannel;
	int m_selected_start_address;
	int m_selected_bitrate;
	bool m_selected_dabplus;
	std::vector<uint8_t> m_superframe;
	size_t m_superframe_part_size;
	int m_superframe_parts;
	std::string m_dynamic_label;
	std::string m_dl_plus_item_title;
	std::string m_dl_plus_item_artist;
	std::string m_dl_plus_item_genre;
	std::string m_dl_plus_programme_now;
	std::string m_dl_plus_programme_next;
	std::string m_dl_plus_programme_part;
	std::string m_dl_plus_programme_host;
	uint64_t m_af_packets;
	uint64_t m_eti_frames;
	uint64_t m_fic_frames;
	uint64_t m_msc_frames;
	uint64_t m_audio_frames;
	uint64_t m_crc_errors;
	uint64_t m_pad_packets;
	uint64_t m_dls_labels;
	uint64_t m_dl_plus_revision;
	uint64_t m_slides;
	uint64_t m_service_revision;
	int m_slide_format;
};

#endif
