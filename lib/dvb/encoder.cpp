#include <sys/select.h>
#include <unistd.h>
#include <errno.h>
#include <string.h>
#include <stdint.h>
#include <stdlib.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <sys/poll.h>
#include <signal.h>
#include <sys/time.h>
#include <sstream>

#include <gst/gst.h>

#include <lib/base/eerror.h>
#include <lib/base/init.h>
#include <lib/base/init_num.h>
#include <lib/base/wrappers.h>
#include <lib/base/cfile.h>
#include <lib/nav/core.h>
#include <lib/base/nconfig.h>
#include <lib/dvb/encoder.h>
#include <lib/dvb/pmt.h>
#include <lib/service/service.h>

#ifndef O_CLOEXEC
#define O_CLOEXEC 0
#endif

#ifndef DREAMSOURCE_PIPE_SIZE
#define DREAMSOURCE_PIPE_SIZE (1024 * 1024)
#endif

#ifdef DREAMNEXTGEN
#define AMVENC_AVC_IOC_MAGIC 'E'
#define AMVENC_AVC_IOC_GET_DEVINFO _IOW(AMVENC_AVC_IOC_MAGIC, 0xf0, uint32_t)
#define AMVENC_AVC_IOC_MAX_INSTANCE _IOW(AMVENC_AVC_IOC_MAGIC, 0xf1, uint32_t)
#define AMVENC_AVC_IOC_GET_ADDR _IOW(AMVENC_AVC_IOC_MAGIC, 0x00, uint32_t)
#define AMVENC_AVC_IOC_NEW_CMD _IOW(AMVENC_AVC_IOC_MAGIC, 0x02, uint32_t)
#define AMVENC_AVC_IOC_GET_STAGE _IOW(AMVENC_AVC_IOC_MAGIC, 0x03, uint32_t)
#define AMVENC_AVC_IOC_GET_OUTPUT_SIZE _IOW(AMVENC_AVC_IOC_MAGIC, 0x04, uint32_t)
#define AMVENC_AVC_IOC_CONFIG_INIT _IOW(AMVENC_AVC_IOC_MAGIC, 0x05, uint32_t)
#define AMVENC_AVC_IOC_GET_BUFFINFO _IOW(AMVENC_AVC_IOC_MAGIC, 0x08, uint32_t)

#define VIDEOGRABBER_IOC_MAGIC 'D'
#define VIDEOGRABBER_IOC_SETUP _IOW(VIDEOGRABBER_IOC_MAGIC, 0x00, struct videograbber_setup_t)
#define VIDEOGRABBER_IOC_GET_FRAME _IOR(VIDEOGRABBER_IOC_MAGIC, 0x01, struct videograbber_vframe_t)

namespace {

enum
{
	AMLOGIC_AVC_MAX_ADDR_INFO_SIZE = 52,
	AMLOGIC_AVC_ENCODER_SEQUENCE = 1,
	AMLOGIC_AVC_ENCODER_IDR = 3,
	AMLOGIC_AVC_ENCODER_NON_IDR = 4,
	AMLOGIC_AVC_LOCAL_BUFF = 0,
	AMLOGIC_AVC_FMT_NV21 = 2,
	AMLOGIC_AVC_UCODE_MODE_FULL = 0,
	AMLOGIC_AVC_DEFAULT_QP = 36,
	AMLOGIC_AVC_SUPPORTED_WIDTH = 1280,
	AMLOGIC_AVC_SUPPORTED_HEIGHT = 720,
	AMLOGIC_AVC_CBR_LONG_THRESH = 4,
	AMLOGIC_AVC_START_TABLE_ID = 8,
	AMLOGIC_AVC_FLUSH_FLAG_INPUT = 0x1,
	AMLOGIC_AVC_FLUSH_FLAG_OUTPUT = 0x2,
	VIDEOGRABBER_FORMAT_RGB888 = 0,
	TS_PID_PAT = 0x0000,
	TS_PID_PMT = 0x0100,
	TS_PID_VIDEO = 0x0101,
	TS_STREAM_ID_VIDEO = 0xe0,
};

struct amlogic_avc_init_result
{
	uint32_t dct_offset;
	uint32_t dct_size;
	uint32_t bitstream_offset;
	uint32_t bitstream_size;
	uint32_t buffer_size;
};

struct videograbber_setup_t
{
	int out_width;
	int out_height;
	int out_stride;
	int out_format;
};

struct videograbber_vframe_t
{
	unsigned long canvas_phys_addr[3];
	int width[3];
	int stride[3];
	int height[3];
};

struct ts_mux_state
{
	int fd;
	uint16_t program_number;
	uint8_t pat_cc;
	uint8_t pmt_cc;
	uint8_t video_cc;
};

static uint32_t align_up_u32(uint32_t value, uint32_t alignment)
{
	return (value + alignment - 1) & ~(alignment - 1);
}

static uint8_t clamp_u8(int value)
{
	if (value < 0)
		return 0;
	if (value > 255)
		return 255;
	return (uint8_t)value;
}

static uint16_t service_ref_program_number(const std::string &serviceref)
{
	size_t begin = 0;
	size_t end = std::string::npos;

	for (int field = 0; field < 3; ++field)
	{
		begin = serviceref.find(':', begin);
		if (begin == std::string::npos)
			return 1;
		++begin;
	}

	end = serviceref.find(':', begin);
	std::string sid = serviceref.substr(begin, end == std::string::npos ? std::string::npos : end - begin);
	if (sid.empty())
		return 1;

	char *parse_end = nullptr;
	unsigned long value = strtoul(sid.c_str(), &parse_end, 16);
	if (!parse_end || *parse_end || value == 0 || value > 0xffff)
		return 1;
	return (uint16_t)value;
}

static uint32_t amlogic_avc_qp_for_bitrate(int bitrate)
{
	if (bitrate <= 1000000)
		return 42;
	if (bitrate <= 1500000)
		return 40;
	if (bitrate <= 2500000)
		return 38;
	return AMLOGIC_AVC_DEFAULT_QP;
}

static void rgb888_to_nv21(uint8_t *dst, const uint8_t *src, uint32_t width, uint32_t height, uint32_t src_stride)
{
	uint32_t dst_stride = align_up_u32(width, 32);
	uint32_t aligned_height = align_up_u32(height, 16);
	uint8_t *dst_y = dst;
	uint8_t *dst_vu = dst + dst_stride * aligned_height;

	memset(dst, 0x80, dst_stride * aligned_height * 3 / 2);

	for (uint32_t y = 0; y < height; y++)
	{
		const uint8_t *src_row = src + y * src_stride;
		uint8_t *y_row = dst_y + y * dst_stride;

		for (uint32_t x = 0; x < width; x++)
		{
			int r = src_row[x * 3 + 0];
			int g = src_row[x * 3 + 1];
			int b = src_row[x * 3 + 2];
			int yy = ((66 * r + 129 * g + 25 * b + 128) >> 8) + 16;

			y_row[x] = clamp_u8(yy);
		}
	}

	for (uint32_t y = 0; y + 1 < height; y += 2)
	{
		const uint8_t *row0 = src + y * src_stride;
		const uint8_t *row1 = src + (y + 1) * src_stride;
		uint8_t *vu_row = dst_vu + (y / 2) * dst_stride;

		for (uint32_t x = 0; x + 1 < width; x += 2)
		{
			int sum_u = 0;
			int sum_v = 0;

			for (int i = 0; i < 4; i++)
			{
				const uint8_t *p = (i < 2 ? row0 : row1) + (x + (i & 1)) * 3;
				int r = p[0];
				int g = p[1];
				int b = p[2];
				int u = ((-38 * r - 74 * g + 112 * b + 128) >> 8) + 128;
				int v = ((112 * r - 94 * g - 18 * b + 128) >> 8) + 128;

				sum_u += u;
				sum_v += v;
			}

			vu_row[x + 0] = clamp_u8(sum_v / 4);
			vu_row[x + 1] = clamp_u8(sum_u / 4);
		}
	}
}

static bool write_pipe_all(int fd, const uint8_t *data, size_t size)
{
	while (size)
	{
		ssize_t written = write(fd, data, size);
		if (written > 0)
		{
			data += written;
			size -= written;
			continue;
		}
		if (written < 0 && errno == EINTR)
			continue;
		if (written < 0 && (errno == EAGAIN || errno == EWOULDBLOCK))
		{
			struct pollfd pfd;
			memset(&pfd, 0, sizeof(pfd));
			pfd.fd = fd;
			pfd.events = POLLOUT;
			if (poll(&pfd, 1, 1000) <= 0)
				continue;
			continue;
		}
		return false;
	}
	return true;
}

static uint32_t mpeg_crc32(const uint8_t *data, size_t size)
{
	uint32_t crc = 0xffffffff;

	for (size_t i = 0; i < size; i++)
	{
		crc ^= (uint32_t)data[i] << 24;
		for (int bit = 0; bit < 8; bit++)
			crc = (crc & 0x80000000) ? (crc << 1) ^ 0x04c11db7 : crc << 1;
	}
	return crc;
}

static void append_crc(std::vector<uint8_t> &section)
{
	uint32_t crc = mpeg_crc32(&section[0], section.size());
	section.push_back((crc >> 24) & 0xff);
	section.push_back((crc >> 16) & 0xff);
	section.push_back((crc >> 8) & 0xff);
	section.push_back(crc & 0xff);
}

static bool h264_find_start_code(const uint8_t *data, size_t size, size_t &offset, size_t &prefix_size)
{
	for (size_t i = 0; i + 3 < size; ++i)
	{
		if (data[i] || data[i + 1])
			continue;
		if (data[i + 2] == 1)
		{
			offset = i;
			prefix_size = 3;
			return true;
		}
		if (i + 4 < size && data[i + 2] == 0 && data[i + 3] == 1)
		{
			offset = i;
			prefix_size = 4;
			return true;
		}
	}
	return false;
}

static uint8_t h264_first_nal_type(const uint8_t *data, size_t size)
{
	size_t offset = 0;
	size_t prefix_size = 0;
	if (!h264_find_start_code(data, size, offset, prefix_size))
		return 0;
	if (offset + prefix_size >= size)
		return 0;
	return data[offset + prefix_size] & 0x1f;
}

static void h264_prepend_aud_if_needed(std::vector<uint8_t> &access_unit)
{
	static const uint8_t aud[] = { 0x00, 0x00, 0x00, 0x01, 0x09, 0xf0 };
	if (access_unit.empty() || h264_first_nal_type(&access_unit[0], access_unit.size()) == 9)
		return;
	access_unit.insert(access_unit.begin(), aud, aud + sizeof(aud));
}

static void write_pcr(uint8_t *dst, uint64_t pcr_base)
{
	dst[0] = (pcr_base >> 25) & 0xff;
	dst[1] = (pcr_base >> 17) & 0xff;
	dst[2] = (pcr_base >> 9) & 0xff;
	dst[3] = (pcr_base >> 1) & 0xff;
	dst[4] = ((pcr_base & 0x1) << 7) | 0x7e;
	dst[5] = 0;
}

static bool ts_write_packet(ts_mux_state &mux, uint16_t pid, bool payload_start, const uint8_t *payload,
	size_t payload_size, bool has_pcr, bool random_access, uint64_t pcr_base)
{
	uint8_t packet[188];
	uint8_t *cc = pid == TS_PID_PAT ? &mux.pat_cc : (pid == TS_PID_PMT ? &mux.pmt_cc : &mux.video_cc);
	size_t header_size = 4;
	size_t min_adaptation = has_pcr ? 8 : 0;
	size_t max_payload = 188 - header_size - min_adaptation;
	bool use_adaptation = has_pcr || payload_size < (188 - header_size);
	size_t packet_payload = payload_size;

	if (packet_payload > max_payload)
		packet_payload = max_payload;

	memset(packet, 0xff, sizeof(packet));
	packet[0] = 0x47;
	packet[1] = (payload_start ? 0x40 : 0x00) | ((pid >> 8) & 0x1f);
	packet[2] = pid & 0xff;
	packet[3] = (use_adaptation ? 0x30 : 0x10) | (*cc & 0x0f);
	*cc = (*cc + 1) & 0x0f;

	if (use_adaptation)
	{
		size_t adaptation_length = 188 - header_size - 1 - packet_payload;
		packet[4] = adaptation_length;
		if (adaptation_length)
		{
			packet[5] = (has_pcr ? 0x10 : 0x00) | (random_access ? 0x40 : 0x00);
			if (has_pcr && adaptation_length >= 7)
				write_pcr(packet + 6, pcr_base);
		}
		header_size += 1 + adaptation_length;
	}

	if (packet_payload)
		memcpy(packet + header_size, payload, packet_payload);

	return write_pipe_all(mux.fd, packet, sizeof(packet));
}

static bool ts_write_section(ts_mux_state &mux, uint16_t pid, const std::vector<uint8_t> &section)
{
	uint8_t payload[184];
	size_t copy = section.size();
	if (copy > sizeof(payload) - 1)
		copy = sizeof(payload) - 1;
	payload[0] = 0x00;
	memcpy(payload + 1, &section[0], copy);
	return ts_write_packet(mux, pid, true, payload, copy + 1, false, false, 0);
}

static bool ts_write_pat_pmt(ts_mux_state &mux)
{
	std::vector<uint8_t> pat;
	std::vector<uint8_t> pmt;

	pat.push_back(0x00);
	pat.push_back(0xb0);
	pat.push_back(0x0d);
	pat.push_back(0x00);
	pat.push_back(0x01);
	pat.push_back(0xc1);
	pat.push_back(0x00);
	pat.push_back(0x00);
	pat.push_back((mux.program_number >> 8) & 0xff);
	pat.push_back(mux.program_number & 0xff);
	pat.push_back(0xe0 | ((TS_PID_PMT >> 8) & 0x1f));
	pat.push_back(TS_PID_PMT & 0xff);
	append_crc(pat);

	pmt.push_back(0x02);
	pmt.push_back(0xb0);
	pmt.push_back(0x12);
	pmt.push_back((mux.program_number >> 8) & 0xff);
	pmt.push_back(mux.program_number & 0xff);
	pmt.push_back(0xc1);
	pmt.push_back(0x00);
	pmt.push_back(0x00);
	pmt.push_back(0xe0 | ((TS_PID_VIDEO >> 8) & 0x1f));
	pmt.push_back(TS_PID_VIDEO & 0xff);
	pmt.push_back(0xf0);
	pmt.push_back(0x00);
	pmt.push_back(0x1b);
	pmt.push_back(0xe0 | ((TS_PID_VIDEO >> 8) & 0x1f));
	pmt.push_back(TS_PID_VIDEO & 0xff);
	pmt.push_back(0xf0);
	pmt.push_back(0x00);
	append_crc(pmt);

	return ts_write_section(mux, TS_PID_PAT, pat) && ts_write_section(mux, TS_PID_PMT, pmt);
}

static void append_pts(std::vector<uint8_t> &pes, uint64_t pts)
{
	pts &= 0x1ffffffffULL;
	pes.push_back(0x20 | (((pts >> 30) & 0x07) << 1) | 1);
	pes.push_back((pts >> 22) & 0xff);
	pes.push_back((((pts >> 15) & 0x7f) << 1) | 1);
	pes.push_back((pts >> 7) & 0xff);
	pes.push_back(((pts & 0x7f) << 1) | 1);
}

static bool ts_write_h264_access_unit(ts_mux_state &mux, const uint8_t *data, size_t size, uint64_t pts90k, bool random_access)
{
	std::vector<uint8_t> pes;
	size_t offset = 0;

	pes.reserve(size + 32);
	pes.push_back(0x00);
	pes.push_back(0x00);
	pes.push_back(0x01);
	pes.push_back(TS_STREAM_ID_VIDEO);

	pes.push_back(0x00);
	pes.push_back(0x00);
	pes.push_back(0x80);
	pes.push_back(0x80);
	pes.push_back(0x05);
	append_pts(pes, pts90k);
	pes.insert(pes.end(), data, data + size);

	while (offset < pes.size())
	{
		size_t remaining = pes.size() - offset;
		size_t max_payload = offset == 0 ? 176 : 184;
		size_t chunk = remaining < max_payload ? remaining : max_payload;
		bool ok = ts_write_packet(mux, TS_PID_VIDEO, offset == 0, &pes[offset], chunk,
			offset == 0, random_access && offset == 0, pts90k);
		if (!ok)
			return false;
		offset += chunk;
	}
	return true;
}

static bool create_pipe(int fds[2])
{
	if (pipe(fds) < 0)
		return false;

	fcntl(fds[0], F_SETFD, fcntl(fds[0], F_GETFD) | FD_CLOEXEC);
	fcntl(fds[1], F_SETFD, fcntl(fds[1], F_GETFD) | FD_CLOEXEC);
	return true;
}

static uint64_t clock_us()
{
	struct timeval tv;
	gettimeofday(&tv, NULL);
	return (uint64_t)tv.tv_sec * 1000000ULL + (uint64_t)tv.tv_usec;
}

static bool amlogic_avc_ioctl_words(int fd, unsigned long request, uint32_t *words, const char *name)
{
	if (ioctl(fd, request, words) < 0)
	{
		eWarning("[eEncoder][Amlogic] %s failed: errno=%d (%s)", name, errno, strerror(errno));
		return false;
	}
	return true;
}

static bool amlogic_avc_wait_ready(int fd, const char *name)
{
	struct pollfd pfd;
	memset(&pfd, 0, sizeof(pfd));
	pfd.fd = fd;
	pfd.events = POLLIN | POLLRDNORM;

	int rc;
	do
	{
		rc = poll(&pfd, 1, 7000);
	} while (rc < 0 && errno == EINTR);

	if (rc <= 0)
	{
		eWarning("[eEncoder][Amlogic] %s poll %s", name, rc == 0 ? "timeout" : strerror(errno));
		return false;
	}
	return true;
}

static bool amlogic_avc_config_init(int fd, uint32_t width, uint32_t height, amlogic_avc_init_result &init)
{
	uint32_t cfg[AMLOGIC_AVC_MAX_ADDR_INFO_SIZE];
	uint32_t value = 0;
	memset(&init, 0, sizeof(init));
	memset(cfg, 0, sizeof(cfg));

	if (!amlogic_avc_ioctl_words(fd, AMVENC_AVC_IOC_GET_BUFFINFO, &value, "GET_BUFFINFO"))
		return false;
	init.buffer_size = value;

	cfg[1] = (height + 15) / 16;
	cfg[2] = width;
	cfg[3] = height;
	cfg[4] = 0;

	if (!amlogic_avc_ioctl_words(fd, AMVENC_AVC_IOC_CONFIG_INIT, cfg, "CONFIG_INIT"))
		return false;

	init.dct_offset = cfg[1];
	init.dct_size = cfg[2];
	init.bitstream_offset = cfg[3];
	init.bitstream_size = cfg[4];

	eDebug("[eEncoder][Amlogic] CONFIG_INIT %ux%u buffer=%u dct=%u/%u bitstream=%u/%u",
			width, height, init.buffer_size, init.dct_offset, init.dct_size, init.bitstream_offset, init.bitstream_size);
	return init.buffer_size && init.dct_size && init.bitstream_size;
}

static bool amlogic_avc_sequence(int fd, uint8_t *mapped, const amlogic_avc_init_result &init, uint32_t qp, std::vector<uint8_t> &sequence)
{
	uint32_t cmd[AMLOGIC_AVC_MAX_ADDR_INFO_SIZE];
	uint32_t words[8];
	uint32_t total_size;
	memset(cmd, 0, sizeof(cmd));
	memset(words, 0, sizeof(words));

	cmd[0] = AMLOGIC_AVC_ENCODER_SEQUENCE;
	cmd[1] = AMLOGIC_AVC_UCODE_MODE_FULL;
	cmd[2] = qp;
	cmd[3] = AMLOGIC_AVC_FLUSH_FLAG_OUTPUT;
	cmd[4] = 5000;

	if (!amlogic_avc_ioctl_words(fd, AMVENC_AVC_IOC_NEW_CMD, cmd, "ENCODER_SEQUENCE"))
		return false;
	if (!amlogic_avc_wait_ready(fd, "ENCODER_SEQUENCE"))
		return false;
	if (!amlogic_avc_ioctl_words(fd, AMVENC_AVC_IOC_GET_OUTPUT_SIZE, words, "GET_OUTPUT_SIZE sequence"))
		return false;

	total_size = (words[0] >> 16) + (words[0] & 0xffff);
	if (!total_size || total_size > init.bitstream_size)
	{
		eWarning("[eEncoder][Amlogic] invalid sequence size %u", total_size);
		return false;
	}

	sequence.assign(mapped + init.bitstream_offset, mapped + init.bitstream_offset + total_size);
	eDebug("[eEncoder][Amlogic] sequence size=%u", total_size);
	return true;
}

static bool amlogic_avc_encode_frame(int fd, uint8_t *mapped, const amlogic_avc_init_result &init,
		uint32_t width, uint32_t height, bool idr, uint32_t qp, std::vector<uint8_t> &frame)
{
	uint32_t cmd[AMLOGIC_AVC_MAX_ADDR_INFO_SIZE];
	uint32_t words[8];
	uint32_t stage = 0;
	uint32_t stride = align_up_u32(width, 32);
	uint32_t aligned_height = align_up_u32(height, 16);
	uint32_t frame_size = stride * aligned_height * 3 / 2;
	memset(cmd, 0, sizeof(cmd));
	memset(words, 0, sizeof(words));

	if (frame_size > init.dct_size)
	{
		eWarning("[eEncoder][Amlogic] frame_size=%u exceeds dct buffer=%u", frame_size, init.dct_size);
		return false;
	}

	cmd[0] = idr ? AMLOGIC_AVC_ENCODER_IDR : AMLOGIC_AVC_ENCODER_NON_IDR;
	cmd[1] = AMLOGIC_AVC_UCODE_MODE_FULL;
	cmd[2] = AMLOGIC_AVC_LOCAL_BUFF;
	cmd[3] = AMLOGIC_AVC_FMT_NV21;
	cmd[4] = 0;
	cmd[5] = frame_size;
	cmd[6] = qp;
	cmd[7] = AMLOGIC_AVC_FLUSH_FLAG_INPUT | AMLOGIC_AVC_FLUSH_FLAG_OUTPUT;
	cmd[8] = 5000;
	cmd[13] = width;
	cmd[14] = height;
	cmd[44] = 16;
	cmd[45] = 9;
	cmd[46] = AMLOGIC_AVC_CBR_LONG_THRESH;
	cmd[47] = AMLOGIC_AVC_START_TABLE_ID;

	if (!amlogic_avc_ioctl_words(fd, AMVENC_AVC_IOC_NEW_CMD, cmd, idr ? "ENCODER_IDR" : "ENCODER_NON_IDR"))
		return false;
	if (!amlogic_avc_wait_ready(fd, idr ? "ENCODER_IDR" : "ENCODER_NON_IDR"))
		return false;
	ioctl(fd, AMVENC_AVC_IOC_GET_STAGE, &stage);
	if (!amlogic_avc_ioctl_words(fd, AMVENC_AVC_IOC_GET_OUTPUT_SIZE, words, "GET_OUTPUT_SIZE frame"))
		return false;

	if (!words[0] || words[0] > init.bitstream_size)
	{
		eWarning("[eEncoder][Amlogic] invalid frame output size %u stage=%u", words[0], stage);
		return false;
	}

	frame.assign(mapped + init.bitstream_offset, mapped + init.bitstream_offset + words[0]);
	return true;
}

} // namespace
#endif

namespace {

static bool dreamsource_backend_available()
{
	return access("/dev/venc0", R_OK | W_OK) == 0 && access("/dev/aenc0", R_OK | W_OK) == 0;
}

static bool dreamsource_create_pipe(int fds[2])
{
	if (pipe(fds) < 0)
		return false;

	fcntl(fds[0], F_SETFD, fcntl(fds[0], F_GETFD) | FD_CLOEXEC);
	fcntl(fds[1], F_SETFD, fcntl(fds[1], F_GETFD) | FD_CLOEXEC);
#ifdef F_SETPIPE_SZ
	if (fcntl(fds[1], F_SETPIPE_SZ, DREAMSOURCE_PIPE_SIZE) < 0)
		eWarning("[eEncoder][Dreamsource] can't grow pipe to %d bytes: errno=%d (%s)",
			DREAMSOURCE_PIPE_SIZE, errno, strerror(errno));
#endif
	return true;
}

static int dreamsource_video_bitrate_kbit(int bitrate)
{
	if (bitrate <= 0)
		return 1500;
	return bitrate > 10000 ? bitrate / 1000 : bitrate;
}

static int dreamsource_service_input_mode(const std::string &serviceref)
{
	eServiceReference ref(serviceref);

	if (ref && ref.type == eServiceReference::idServiceHDMIIn)
		return eStreamServer::INPUT_MODE_HDMI_IN;

	return eStreamServer::INPUT_MODE_LIVE;
}

static void dreamsource_normalize_resolution(int &width, int &height)
{
	int requested_width = width;
	int requested_height = height;

	if (width <= 0)
		width = 1280;
	if (height <= 0)
		height = 720;

	if ((width == 720 && height == 576) ||
		(width == 1280 && height == 720) ||
		(width == 1920 && height == 1080))
		return;

	if (width <= 720 && height <= 576)
	{
		width = 720;
		height = 576;
	}
	else if (width > 1280 || height > 720)
	{
		width = 1920;
		height = 1080;
	}
	else
	{
		width = 1280;
		height = 720;
	}

	eDebug("[eEncoder][Dreamsource] normalize resolution %dx%d -> %dx%d",
		requested_width, requested_height, width, height);
}

static void dreamsource_framerate_fraction(int framerate, int &num, int &den)
{
	if (framerate == 50 || framerate == 50000)
		num = 50;
	else if (framerate == 60 || framerate == 60000)
		num = 60;
	else if (framerate == 30 || framerate == 29970 || framerate == 30000)
		num = 30;
	else
		num = 25;

	den = 1;

	if (framerate > 0 && framerate != num && framerate != num * 1000)
		eDebug("[eEncoder][Dreamsource] normalize framerate %d -> %d/1", framerate, num);
}

static bool dreamsource_gstreamer_ready()
{
	GError *error = NULL;

	if (!gst_init_check(NULL, NULL, &error))
	{
		if (error)
		{
			eWarning("[eEncoder][Dreamsource] GStreamer init failed: %s", error->message);
			g_error_free(error);
		}
		else
			eWarning("[eEncoder][Dreamsource] GStreamer init failed");
		return false;
	}

	return true;
}

static bool dreamsource_have_factory(const char *name)
{
	GstElementFactory *factory = gst_element_factory_find(name);
	if (!factory)
		return false;

	gst_object_unref(factory);
	return true;
}

static std::string dreamsource_pipeline_description(int fd, int bitrate, int width, int height, int framerate, int input_mode)
{
	int fps_num = 25;
	int fps_den = 1;
	std::ostringstream pipeline;

	dreamsource_normalize_resolution(width, height);
	dreamsource_framerate_fraction(framerate, fps_num, fps_den);

	pipeline
		<< "mpegtsmux name=mux alignment=7 ! fdsink fd=" << fd << " sync=false async=false "
		<< "dreamvideosource name=dreamvideosource0 bitrate=" << dreamsource_video_bitrate_kbit(bitrate) << " input-mode=" << input_mode << " ! "
		<< "video/x-h264,width=" << width << ",height=" << height << ",framerate=" << fps_num << "/" << fps_den << ",profile=main ! "
		<< "h264parse config-interval=-1";

	if (dreamsource_have_factory("h264timestamper"))
		pipeline << " ! h264timestamper";

	pipeline
		<< " ! video/x-h264,stream-format=byte-stream,alignment=au ! "
		<< "queue max-size-buffers=0 max-size-bytes=0 max-size-time=5000000000 ! mux. "
		<< "dreamaudiosource name=dreamaudiosource0 bitrate=96 input-mode=" << input_mode << " ! aacparse ! "
		<< "audio/mpeg,mpegversion=4,stream-format=adts,rate=48000 ! "
		<< "queue max-size-buffers=0 max-size-bytes=0 max-size-time=5000000000 ! mux.";

	return pipeline.str();
}

static bool dreamsource_wait_service_ready(eNavigation *navigation, int timeout_ms)
{
	int elapsed_ms = 0;

	while (elapsed_ms <= timeout_ms)
	{
		ePtr<iPlayableService> service;
		ePtr<iServiceInformation> info;

		if (navigation)
		{
			navigation->getCurrentService(service);
			if (service)
			{
				service->info(info);
				if (info)
				{
					int vpid = info->getInfo(iServiceInformation::sVideoPID);
					int apid = info->getInfo(iServiceInformation::sAudioPID);
					int pmtpid = info->getInfo(iServiceInformation::sPMTPID);

					if (vpid > 0 && apid > 0 && pmtpid > 0)
					{
						eDebug("[eEncoder][Dreamsource] service ready vpid=%d apid=%d pmtpid=%d", vpid, apid, pmtpid);
						return true;
					}
				}
			}
		}

		usleep(100 * 1000);
		elapsed_ms += 100;
	}

	eWarning("[eEncoder][Dreamsource] service not ready after %d ms", timeout_ms);
	return false;
}

static void dreamsource_log_gst_message(GstMessage *message)
{
	if (!message)
		return;

	switch(GST_MESSAGE_TYPE(message))
	{
		case GST_MESSAGE_ERROR:
		{
			GError *message_error = NULL;
			gchar *debug = NULL;

			gst_message_parse_error(message, &message_error, &debug);
			eWarning("[eEncoder][Dreamsource] pipeline error: %s%s%s",
				message_error ? message_error->message : "unknown",
				debug ? " debug=" : "",
				debug ? debug : "");
			if(message_error)
				g_error_free(message_error);
			if(debug)
				g_free(debug);
			break;
		}
		case GST_MESSAGE_EOS:
			eDebug("[eEncoder][Dreamsource] pipeline EOS");
			break;
		default:
			break;
	}
}

} // namespace

DEFINE_REF(eEncoder);

eEncoder *eEncoder::instance = NULL;

eEncoder *eEncoder::getInstance()
{
	return instance;
}

eEncoder::eEncoder()
{
	int decoder_index;
	ePtr<iServiceHandler> service_center;
	eNavigation *navigation_instance_normal, *navigation_instance_alternative;

	instance = this;
	eServiceCenter::getInstance(service_center);
	bcm_encoder = false;
	dreamsource_encoder = false;
#ifdef DREAMNEXTGEN
	amlogic_avc_encoder = false;
#endif

	if(service_center)
	{
		bcm_encoder = bool(CFile("/dev/bcm_enc0", "r"));

		/*
		 * The Broadcom transcoding engine does not transfer the data to the encoder
		 * itself, so we need to start a thread to do that. Therefore there is no
		 * use to connect a (valid) decoder device. Even more it won't work because
		 * we can't open the encoder when more than two (main, PiP) decoders are in
		 * use. The encoder is reported as "busy" then. That's why we use dummy values
		 * here (4 onwards).
		 *
		 * OTOH the "xtrend" transcoding engine has the video decoder connected to
		 * the selected encoder internally. So we need to use the right decoder,
		 * connected to the selected encoder. This is usually 2 -> 0, 3 -> 1.
		 *
		 * To complicate matters even more, Broadcom transcoding uses the "xtrend"
		 * interface when recording from HDMI input, so we need to always construct
		 * two navigation instances, one with the normal, usual video decoder
		 * connected for "xtrend" transcoding and for HDMI input, and one with the
		 * dummy video decoder for Broadcom transcoding.
		 */

		for(int index = 0; index < 4; index++) // increase this if machines appear with more than 4 encoding engines
		{
			char filename[256];

			snprintf(filename, sizeof(filename), "/proc/stb/encoder/%d/decoder", index);

			if (CFile::parseInt(&decoder_index, filename) < 0)
			{
				// VU+ 
				snprintf(filename, sizeof(filename), "/proc/stb/encoder/%d/demux", index);
				if (CFile::parseInt(&decoder_index, filename) < 0)
					break;
			}

			snprintf(filename, sizeof(filename), "/dev/%s%d", bcm_encoder ? "bcm_enc" : "encoder", index);
			if (access(filename, bcm_encoder ? (R_OK | W_OK) : R_OK) < 0)
			{
				eDebug("[eEncoder] stopping encoder scan at %d: %s is not usable: errno=%d (%s)",
						index, filename, errno, strerror(errno));
				break;
			}

			/* the connected video decoder for "Xtrend" transcoding / encoding or for Broadcom HDMI recording */
			if((navigation_instance_normal = new eNavigation(service_center, decoder_index)) == nullptr)
				break;

			if(bcm_encoder)
			{
				/* use a non-existing (+4) video decoder for Broadcom transcoding, we don't want a decoder there */
				if((navigation_instance_alternative = new eNavigation(service_center, index + 4)) == nullptr)
					break;
			}
			else
				navigation_instance_alternative = nullptr;

			encoder.push_back(EncoderContext(navigation_instance_normal, navigation_instance_alternative));
			encoder.back().backend = bcm_encoder ? EncoderContext::backend_bcm : EncoderContext::backend_proc;
		}

		if(encoder.empty() && dreamsource_backend_available())
		{
			eDebug("[eEncoder] registering Dreamsource encoder backend");
			if((navigation_instance_normal = new eNavigation(service_center, 0)) != nullptr)
			{
				encoder.push_back(EncoderContext(navigation_instance_normal, nullptr));
				encoder.back().backend = EncoderContext::backend_dreamsource;
				dreamsource_encoder = true;
			}
		}

#ifdef DREAMNEXTGEN
		if(encoder.empty() && access("/dev/amvenc_avc", R_OK | W_OK) == 0 && access("/dev/videograbber", R_OK | W_OK) == 0)
		{
			eDebug("[eEncoder] registering DreamNextGen Amlogic AVC encoder backend");
			if((navigation_instance_normal = new eNavigation(service_center, 0)) != nullptr)
			{
				encoder.push_back(EncoderContext(navigation_instance_normal, nullptr));
				encoder.back().backend = EncoderContext::backend_amlogic_avc;
				amlogic_avc_encoder = true;
			}
		}
#endif
	}
}

eEncoder::~eEncoder()
{
	for(int encoder_index = 0; encoder_index < (int)encoder.size(); encoder_index++)
	{
		encoder[encoder_index].state = EncoderContext::state_destroyed;
		encoder[encoder_index].navigation_instance = nullptr;
		encoder[encoder_index].navigation_instance_normal = nullptr; /* apparently we're not allowed to delete */
		encoder[encoder_index].navigation_instance_alternative = nullptr; /* apparently we're not allowed to delete */
	}

	instance = nullptr;
}

int eEncoder::allocateEncoder(const std::string &serviceref, int &buffersize,
		int bitrate, int width, int height, int framerate, int interlaced, int aspectratio,
		const std::string &vcodec, const std::string &acodec)
{
	static const char fileref[] = "1:0:1:0:0:0:0:0:0:0:";
	int encoder_index;
	char filename[128];
	std::string source_file;
	const char *vcodec_node;
	const char *acodec_node;

	eDebug("[eEncoder] allocateEncoder serviceref=%s bitrate=%d width=%d height=%d vcodec=%s acodec=%s",
			serviceref.c_str(), bitrate, width, height, vcodec.c_str(), acodec.c_str());

	// extract file path from serviceref, this is needed for Broadcom file transcoding
	if(serviceref.compare(0, sizeof(fileref) - 1, std::string(fileref), 0, std::string::npos) == 0)
		source_file = serviceref.substr(sizeof(fileref) - 1, std::string::npos);

	eDebug("[allocateEncoder] serviceref: %s", serviceref.c_str());
	eDebug("[allocateEncoder] serviceref substr: %s", serviceref.substr(0, sizeof(fileref) - 1).c_str());
	eDebug("[allocateEncoder] source_file: \"%s\"", source_file.c_str());

	for(encoder_index = 0; encoder_index < (int)encoder.size(); encoder_index++)
		if(encoder[encoder_index].state == EncoderContext::state_idle)
			break;

	if(encoder_index >= (int)encoder.size())
	{
		eWarning("[eEncoder] no encoders free");
		return(-1);
	}

	auto cleanup_proc_encoder = [&]() {
		if(encoder[encoder_index].encoder_fd >= 0)
		{
			close(encoder[encoder_index].encoder_fd);
			encoder[encoder_index].encoder_fd = -1;
		}
		if(encoder[encoder_index].file_fd >= 0)
		{
			close(encoder[encoder_index].file_fd);
			encoder[encoder_index].file_fd = -1;
		}
		encoder[encoder_index].navigation_instance = nullptr;
		encoder[encoder_index].state = EncoderContext::state_idle;
	};

	if(encoder[encoder_index].backend == EncoderContext::backend_dreamsource)
	{
		int pipe_fds[2] = { -1, -1 };
		int input_mode = dreamsource_service_input_mode(serviceref);

		if(!source_file.empty())
		{
			eWarning("[eEncoder][Dreamsource] file transcoding is not supported by the Dreamsource backend");
			return(-1);
		}

		if(!vcodec.empty() && vcodec != "h264")
		{
			eWarning("[eEncoder][Dreamsource] unsupported video codec '%s'", vcodec.c_str());
			return(-1);
		}

		if(!acodec.empty() && acodec != "aac")
		{
			eWarning("[eEncoder][Dreamsource] unsupported audio codec '%s'", acodec.c_str());
			return(-1);
		}

		if(!dreamsource_gstreamer_ready())
			return(-1);

		if(!dreamsource_create_pipe(pipe_fds))
		{
			eWarning("[eEncoder][Dreamsource] pipe failed: errno=%d (%s)", errno, strerror(errno));
			return(-1);
		}

		encoder[encoder_index].navigation_instance = encoder[encoder_index].navigation_instance_normal;
		encoder[encoder_index].encoder_fd = pipe_fds[0];
		encoder[encoder_index].output_fd = pipe_fds[1];
		encoder[encoder_index].file_fd = -1;
		encoder[encoder_index].bitrate = bitrate;
		encoder[encoder_index].width = width > 0 ? width : 1280;
		encoder[encoder_index].height = height > 0 ? height : 720;
		encoder[encoder_index].framerate = framerate > 0 ? framerate : 25000;
		encoder[encoder_index].interlaced = interlaced;
		encoder[encoder_index].aspectratio = aspectratio;
		encoder[encoder_index].program_number = 1;
		encoder[encoder_index].input_mode = input_mode;
		encoder[encoder_index].vcodec = "h264";
		encoder[encoder_index].acodec = "aac";

		if(input_mode == eStreamServer::INPUT_MODE_HDMI_IN)
			eDebug("[eEncoder][Dreamsource] HDMI-IN service detected, using input-mode=%d", input_mode);

		if(encoder[encoder_index].navigation_instance->playService(serviceref) < 0)
		{
			eWarning("[eEncoder][Dreamsource] navigation->playservice failed");
			close(pipe_fds[0]);
			close(pipe_fds[1]);
			encoder[encoder_index].encoder_fd = -1;
			encoder[encoder_index].output_fd = -1;
			encoder[encoder_index].navigation_instance = nullptr;
			encoder[encoder_index].input_mode = eStreamServer::INPUT_MODE_LIVE;
			return(-1);
		}

		buffersize = 188 * 256;
		encoder[encoder_index].state = EncoderContext::state_running;
		if(encoder[encoder_index].run())
		{
			eWarning("[eEncoder][Dreamsource] encoder thread start failed");
			encoder[encoder_index].navigation_instance->stopService();
			close(pipe_fds[0]);
			close(pipe_fds[1]);
			encoder[encoder_index].encoder_fd = -1;
			encoder[encoder_index].output_fd = -1;
			encoder[encoder_index].navigation_instance = nullptr;
			encoder[encoder_index].input_mode = eStreamServer::INPUT_MODE_LIVE;
			encoder[encoder_index].state = EncoderContext::state_idle;
			return(-1);
		}

		eDebug("[eEncoder][Dreamsource] running backend fd=%d %dx%d framerate=%d bitrate=%d input-mode=%d",
				encoder[encoder_index].encoder_fd, encoder[encoder_index].width, encoder[encoder_index].height,
				encoder[encoder_index].framerate, encoder[encoder_index].bitrate, encoder[encoder_index].input_mode);
		return(encoder[encoder_index].encoder_fd);
	}

#ifdef DREAMNEXTGEN
	if(encoder[encoder_index].backend == EncoderContext::backend_amlogic_avc)
	{
		int pipe_fds[2] = { -1, -1 };

		if(!vcodec.empty() && vcodec != "h264")
		{
			eWarning("[eEncoder][Amlogic] unsupported video codec '%s' for first AVC backend", vcodec.c_str());
			return(-1);
		}

		if(!create_pipe(pipe_fds))
		{
			eWarning("[eEncoder][Amlogic] pipe failed: errno=%d (%s)", errno, strerror(errno));
			return(-1);
		}

		encoder[encoder_index].navigation_instance = encoder[encoder_index].navigation_instance_normal;
		encoder[encoder_index].encoder_fd = pipe_fds[0];
		encoder[encoder_index].output_fd = pipe_fds[1];
		encoder[encoder_index].file_fd = -1;
		encoder[encoder_index].bitrate = bitrate;
		encoder[encoder_index].width = width > 0 ? width : 1280;
		encoder[encoder_index].height = height > 0 ? height : 720;
		if(encoder[encoder_index].width != AMLOGIC_AVC_SUPPORTED_WIDTH ||
			encoder[encoder_index].height != AMLOGIC_AVC_SUPPORTED_HEIGHT)
		{
			eWarning("[eEncoder][Amlogic] requested %dx%d is not supported by the first AVC backend yet, using %dx%d",
					encoder[encoder_index].width, encoder[encoder_index].height,
					AMLOGIC_AVC_SUPPORTED_WIDTH, AMLOGIC_AVC_SUPPORTED_HEIGHT);
			encoder[encoder_index].width = AMLOGIC_AVC_SUPPORTED_WIDTH;
			encoder[encoder_index].height = AMLOGIC_AVC_SUPPORTED_HEIGHT;
		}
		encoder[encoder_index].framerate = framerate > 0 ? framerate : 25000;
		encoder[encoder_index].interlaced = interlaced;
		encoder[encoder_index].aspectratio = aspectratio;
		encoder[encoder_index].program_number = service_ref_program_number(serviceref);
		encoder[encoder_index].vcodec = "h264";
		encoder[encoder_index].acodec = acodec.empty() ? "aac" : acodec;

		if(encoder[encoder_index].navigation_instance->playService(serviceref) < 0)
		{
			eWarning("[eEncoder][Amlogic] navigation->playservice failed");
			close(pipe_fds[0]);
			close(pipe_fds[1]);
			encoder[encoder_index].encoder_fd = -1;
			encoder[encoder_index].output_fd = -1;
			encoder[encoder_index].navigation_instance = nullptr;
			return(-1);
		}

		buffersize = 188 * 256;
		encoder[encoder_index].state = EncoderContext::state_running;
		if(encoder[encoder_index].run())
		{
			eWarning("[eEncoder][Amlogic] encoder thread start failed");
			encoder[encoder_index].navigation_instance->stopService();
			close(pipe_fds[0]);
			close(pipe_fds[1]);
			encoder[encoder_index].encoder_fd = -1;
			encoder[encoder_index].output_fd = -1;
			encoder[encoder_index].navigation_instance = nullptr;
			encoder[encoder_index].state = EncoderContext::state_idle;
			return(-1);
		}

		eDebug("[eEncoder][Amlogic] running AVC test backend fd=%d %dx%d framerate=%d bitrate=%d",
				encoder[encoder_index].encoder_fd, encoder[encoder_index].width, encoder[encoder_index].height,
				encoder[encoder_index].framerate, encoder[encoder_index].bitrate);
		return(encoder[encoder_index].encoder_fd);
	}
#endif

	// Set encoder parameters - unified for both BCM and HiSilicon encoders
	// BCM parameters now enabled for URL parameter support via Port 8001
	// This makes transtreamproxy obsolete and enables SoftCSA for transcoding

	if(bcm_encoder)
	{
		vcodec_node = "video_codec";
		acodec_node = "audio_codec";
		encoder[encoder_index].navigation_instance = encoder[encoder_index].navigation_instance_alternative;

		// Write transcoding parameters to /proc/stb/encoder for BCM
		eDebug("[eEncoder] BCM encoder %d: setting bitrate=%d framerate=%d", encoder_index, bitrate, framerate);

		snprintf(filename, sizeof(filename), "/proc/stb/encoder/%d/bitrate", encoder_index);
		CFile::writeInt(filename, bitrate);

		snprintf(filename, sizeof(filename), "/proc/stb/encoder/%d/framerate", encoder_index);
		CFile::writeInt(filename, framerate);

		snprintf(filename, sizeof(filename), "/proc/stb/encoder/%d/display_format", encoder_index);
		if(height > 576)
			CFile::write(filename, "720p");
		else if(height > 480)
			CFile::write(filename, "576p");
		else
			CFile::write(filename, "480p");

		/*
		snprintf(filename, sizeof(filename), "/proc/stb/encoder/%d/width", encoder_index);
		CFile::writeInt(filename, width);

		snprintf(filename, sizeof(filename), "/proc/stb/encoder/%d/height", encoder_index);
		CFile::writeInt(filename, height);

		snprintf(filename, sizeof(filename), "/proc/stb/encoder/%d/interlaced", encoder_index);
		CFile::writeInt(filename, interlaced);

		snprintf(filename, sizeof(filename), "/proc/stb/encoder/%d/aspectratio", encoder_index);
		CFile::writeInt(filename, aspectratio);
		*/
	}
	else
	{
		vcodec_node = "vcodec";
		acodec_node = "acodec";
		encoder[encoder_index].navigation_instance = encoder[encoder_index].navigation_instance_normal;

		snprintf(filename, sizeof(filename), "/proc/stb/encoder/%d/bitrate", encoder_index);
		CFile::writeInt(filename, bitrate);

		snprintf(filename, sizeof(filename), "/proc/stb/encoder/%d/width", encoder_index);
		CFile::writeInt(filename, width);

		snprintf(filename, sizeof(filename), "/proc/stb/encoder/%d/height", encoder_index);
		CFile::writeInt(filename, height);

		snprintf(filename, sizeof(filename), "/proc/stb/encoder/%d/framerate", encoder_index);
		CFile::writeInt(filename, framerate);

		snprintf(filename, sizeof(filename), "/proc/stb/encoder/%d/interlaced", encoder_index);
		CFile::writeInt(filename, interlaced);

		snprintf(filename, sizeof(filename), "/proc/stb/encoder/%d/aspectratio", encoder_index);
		CFile::writeInt(filename, aspectratio);

	}

	if(!vcodec.empty())
	{
		snprintf(filename, sizeof(filename), "/proc/stb/encoder/%d/%s_choices", encoder_index, vcodec_node);
		if (CFile::contains_word(filename, vcodec))
		{
			snprintf(filename, sizeof(filename), "/proc/stb/encoder/%d/%s", encoder_index, vcodec_node);
			CFile::write(filename, vcodec.c_str());
		}
	}

	if(!acodec.empty())
	{
		snprintf(filename, sizeof(filename), "/proc/stb/encoder/%d/%s_choices", encoder_index, acodec_node);
		if (CFile::contains_word(filename, acodec))
		{
			snprintf(filename, sizeof(filename), "/proc/stb/encoder/%d/%s", encoder_index, acodec_node);
			CFile::write(filename, acodec.c_str());
		}
	}

	if(!bcm_encoder) {

		snprintf(filename, sizeof(filename), "/proc/stb/encoder/%d/apply", encoder_index);
		CFile::writeInt(filename, 1);

	}

	if(source_file.empty())
		encoder[encoder_index].file_fd = -1;
	else
	{
		if((encoder[encoder_index].file_fd = open(source_file.c_str(), O_RDONLY, 0)) < 0)
		{
			eWarning("[eEncoder] open source file '%s' failed: errno=%d (%s)", source_file.c_str(), errno, strerror(errno));
			cleanup_proc_encoder();
			return(-1);
		}
	}

	snprintf(filename, sizeof(filename), "/dev/%s%d", bcm_encoder ? "bcm_enc" : "encoder", encoder_index);

	if((encoder[encoder_index].encoder_fd = open(filename, bcm_encoder ? O_RDWR : O_RDONLY)) < 0)
	{
		eWarning("[eEncoder] open encoder '%s' failed: errno=%d (%s)", filename, errno, strerror(errno));
		cleanup_proc_encoder();
		return(-1);
	}

	if(bcm_encoder)
	{
		buffersize = 188 * 256; /* broadcom magic value */
		encoder[encoder_index].state = EncoderContext::state_wait_pmt;

		switch(encoder_index)
		{
			case(0):
			{
				encoder[encoder_index].navigation_instance->connectEvent(sigc::mem_fun(*this, &eEncoder::navigation_event_0), m_nav_event_connection_0);
				break;
			}

			case(1):
			{
				encoder[encoder_index].navigation_instance->connectEvent(sigc::mem_fun(*this, &eEncoder::navigation_event_1), m_nav_event_connection_1);
				break;
			}

			default:
			{
				eWarning("[eEncoder] only encoder 0 and encoder 1 implemented");
				cleanup_proc_encoder();
				return(-1);
			}
		}
	}
	else
	{
		buffersize = -1;
		encoder[encoder_index].state = EncoderContext::state_running;
	}

	if(encoder[encoder_index].navigation_instance->playService(serviceref) < 0)
	{
		eWarning("[eEncoder] navigation->playservice failed");
		if(encoder[encoder_index].navigation_instance)
			encoder[encoder_index].navigation_instance->stopService();
		cleanup_proc_encoder();
		return(-1);
	}

	return(encoder[encoder_index].encoder_fd);
}

int eEncoder::allocateHDMIEncoder(const std::string &serviceref, int &buffersize,
		int bitrate, int width, int height, int framerate, int interlaced, int aspectratio,
		const std::string &vcodec, const std::string &acodec)
{
	int hdmi_encoding_bitrate = bitrate > 0 ? bitrate : eConfigManager::getConfigIntValue("config.hdmirecord.bitrate", 8 * 1024 * 1024);
	int hdmi_encoding_width = width > 0 ? width : eConfigManager::getConfigIntValue("config.hdmirecord.width", 1280);
	int hdmi_encoding_height = height > 0 ? height : eConfigManager::getConfigIntValue("config.hdmirecord.height", 720);
	int hdmi_encoding_framerate = framerate > 0 ? framerate : eConfigManager::getConfigIntValue("config.hdmirecord.framerate", 50000);
	int hdmi_encoding_interlaced = interlaced >= 0 ? interlaced : eConfigManager::getConfigIntValue("config.hdmirecord.interlaced", 0);
	int hdmi_encoding_aspect_ratio = aspectratio >= 0 ? aspectratio : eConfigManager::getConfigIntValue("config.hdmirecord.aspectratio", 0);
	std::string hdmi_encoding_vcodec = vcodec.empty() ? eConfigManager::getConfigValue("config.hdmirecord.vcodec") : vcodec;
	if(hdmi_encoding_vcodec.empty())
		hdmi_encoding_vcodec = "h264";
	std::string hdmi_encoding_acodec = acodec.empty() ? eConfigManager::getConfigValue("config.hdmirecord.acodec") : acodec;
	if(hdmi_encoding_acodec.empty())
		hdmi_encoding_acodec = "aac";

	if(dreamsource_encoder)
	{
		hdmi_encoding_vcodec = "h264";
		hdmi_encoding_acodec = "aac";
		return allocateEncoder(serviceref, buffersize, hdmi_encoding_bitrate, hdmi_encoding_width, hdmi_encoding_height,
				hdmi_encoding_framerate, hdmi_encoding_interlaced, hdmi_encoding_aspect_ratio,
				hdmi_encoding_vcodec, hdmi_encoding_acodec);
	}

	char filename[128];
	const char *vcodec_node;
	const char *acodec_node;

	if(bcm_encoder)
	{
		vcodec_node = "video_codec";
		acodec_node = "audio_codec";
		buffersize = 188 * 256; /* broadcom magic value */
	}
	else
	{
		vcodec_node = "vcodec";
		acodec_node = "acodec";
		buffersize = -1;
	}

	/* both systems can only use the first encoder for HDMI recording */

	if((encoder.size() < 1) || (encoder[0].state != EncoderContext::state_idle))
	{
		eWarning("[eEncoder] no encoders free");
		return(-1);
	}

	encoder[0].navigation_instance = encoder[0].navigation_instance_normal;

	auto cleanup_hdmi_encoder = [&]() {
		if(encoder[0].encoder_fd >= 0)
		{
			close(encoder[0].encoder_fd);
			encoder[0].encoder_fd = -1;
		}
		if(encoder[0].file_fd >= 0)
		{
			close(encoder[0].file_fd);
			encoder[0].file_fd = -1;
		}
		if(encoder[0].navigation_instance)
			encoder[0].navigation_instance->stopService();
		encoder[0].navigation_instance = nullptr;
		encoder[0].state = EncoderContext::state_idle;
	};

	CFile::writeInt("/proc/stb/encoder/0/bitrate", hdmi_encoding_bitrate);
	CFile::writeInt("/proc/stb/encoder/0/width", hdmi_encoding_width);
	CFile::writeInt("/proc/stb/encoder/0/height", hdmi_encoding_height);

	if(bcm_encoder)
		CFile::write("/proc/stb/encoder/0/display_format", "720p");

	CFile::writeInt("/proc/stb/encoder/0/framerate", hdmi_encoding_framerate);
	CFile::writeInt("/proc/stb/encoder/0/interlaced", hdmi_encoding_interlaced);
	CFile::writeInt("/proc/stb/encoder/0/aspectratio", hdmi_encoding_aspect_ratio);

	snprintf(filename, sizeof(filename), "/proc/stb/encoder/%d/%s", 0, vcodec_node);
	CFile::write(filename, hdmi_encoding_vcodec.c_str());

	snprintf(filename, sizeof(filename), "/proc/stb/encoder/%d/%s", 0, acodec_node);
	CFile::write(filename, hdmi_encoding_acodec.c_str());

	snprintf(filename, sizeof(filename), "/proc/stb/encoder/%d/apply", 0);
	CFile::writeInt(filename, 1);

	if(encoder[0].navigation_instance->playService(serviceref) < 0)
	{
		eWarning("[eEncoder] navigation->playservice failed");
		cleanup_hdmi_encoder();
		return(-1);
	}

	snprintf(filename, sizeof(filename), "/dev/%s%d", "encoder", 0);

	if((encoder[0].encoder_fd = open(filename, O_RDONLY)) < 0)
	{
		eWarning("[eEncoder] open encoder '%s' failed: errno=%d (%s)", filename, errno, strerror(errno));
		cleanup_hdmi_encoder();
		return(-1);
	}

	encoder[0].state = EncoderContext::state_running;

	return(encoder[0].encoder_fd);
}

void eEncoder::freeEncoder(int encoderfd)
{
	int encoder_index;
	ePtr<iPlayableService> service;
	ePtr<iTapService> tservice;

	if(encoderfd < 0)
	{
		eWarning("[eEncoder] trying to release incorrect encoder %d", encoderfd);
		return;
	}

	for(encoder_index = 0; encoder_index < (int)encoder.size(); encoder_index++)
		if(encoder[encoder_index].encoder_fd == encoderfd)
			break;

	if(encoder_index >= (int)encoder.size())
	{
		eWarning("[eEncoder] encoder with fd=%d not found", encoderfd);
		return;
	}

	switch(encoder[encoder_index].state)
	{
		case(EncoderContext::state_idle):
		case(EncoderContext::state_finishing):
		case(EncoderContext::state_destroyed):
		{
			eWarning("[eEncoder] trying to release inactive encoder %d fd=%d, state=%d", encoder_index, encoderfd, encoder[encoder_index].state);
			return;
		}
		default:
			break;
	}

	if(encoder[encoder_index].backend == EncoderContext::backend_dreamsource)
	{
		eDebug("[eEncoder][Dreamsource] free encoder index=%d fd=%d", encoder_index, encoderfd);
		encoder[encoder_index].state = EncoderContext::state_finishing;
		if(encoder[encoder_index].encoder_fd >= 0)
		{
			eDebug("[eEncoder][Dreamsource] closing pipe reader before joining encoder thread");
			close(encoder[encoder_index].encoder_fd);
			encoder[encoder_index].encoder_fd = -1;
		}

		encoder[encoder_index].kill();
		eDebug("[eEncoder][Dreamsource] encoder thread joined");

		if(encoder[encoder_index].navigation_instance)
			encoder[encoder_index].navigation_instance->stopService();

		if(encoder[encoder_index].output_fd >= 0)
			close(encoder[encoder_index].output_fd);
		if(encoder[encoder_index].file_fd >= 0)
			close(encoder[encoder_index].file_fd);

		encoder[encoder_index].output_fd = -1;
		encoder[encoder_index].file_fd = -1;
		encoder[encoder_index].navigation_instance = nullptr;
		encoder[encoder_index].input_mode = eStreamServer::INPUT_MODE_LIVE;
		encoder[encoder_index].vcodec.clear();
		encoder[encoder_index].acodec.clear();
		encoder[encoder_index].state = EncoderContext::state_idle;
		return;
	}

#ifdef DREAMNEXTGEN
	if(encoder[encoder_index].backend == EncoderContext::backend_amlogic_avc)
	{
		eDebug("[eEncoder][Amlogic] free encoder index=%d fd=%d", encoder_index, encoderfd);
		encoder[encoder_index].state = EncoderContext::state_finishing;
		if(encoder[encoder_index].encoder_fd >= 0)
		{
			eDebug("[eEncoder][Amlogic] closing pipe reader before joining encoder thread");
			close(encoder[encoder_index].encoder_fd);
			encoder[encoder_index].encoder_fd = -1;
		}

		encoder[encoder_index].kill();
		eDebug("[eEncoder][Amlogic] encoder thread joined");

		if(encoder[encoder_index].navigation_instance)
			encoder[encoder_index].navigation_instance->stopService();

		if(encoder[encoder_index].output_fd >= 0)
			close(encoder[encoder_index].output_fd);
		if(encoder[encoder_index].file_fd >= 0)
			close(encoder[encoder_index].file_fd);

		encoder[encoder_index].output_fd = -1;
		encoder[encoder_index].file_fd = -1;
		encoder[encoder_index].navigation_instance = nullptr;
		encoder[encoder_index].vcodec.clear();
		encoder[encoder_index].acodec.clear();
		encoder[encoder_index].state = EncoderContext::state_idle;
		return;
	}
#endif

	if(encoder[encoder_index].stream_thread != nullptr)
	{
		encoder[encoder_index].stream_thread->stop();
		delete encoder[encoder_index].stream_thread;
		encoder[encoder_index].stream_thread = nullptr;
	}

	encoder[encoder_index].state = EncoderContext::state_finishing;
	encoder[encoder_index].kill();

	// Send STOP_TRANSCODING ioctl before closing (required for BCM encoders!)
	if(bcm_encoder && encoder[encoder_index].encoder_fd >= 0)
	{
		eDebug("[eEncoder] freeEncoder: sending STOP_TRANSCODING ioctl");
		if(ioctl(encoder[encoder_index].encoder_fd, IOCTL_BROADCOM_STOP_TRANSCODING, 0))
			eWarning("[eEncoder] freeEncoder: STOP_TRANSCODING ioctl failed");
	}

	encoder[encoder_index].navigation_instance->getCurrentService(service);

	service->tap(tservice);

	if(tservice)
		tservice->stopTapToFD();

	encoder[encoder_index].navigation_instance->stopService();

	close(encoder[encoder_index].encoder_fd);
	close(encoder[encoder_index].file_fd);
	encoder[encoder_index].encoder_fd = -1;
	encoder[encoder_index].file_fd = -1;
	encoder[encoder_index].navigation_instance = nullptr;
	encoder[encoder_index].state = EncoderContext::state_idle;
}

int eEncoder::getUsedEncoderCount()
{
	int count = 0;

	for(int encoder_index = 0; encoder_index < (int)encoder.size(); encoder_index++)
	{
		switch(encoder[encoder_index].state)
		{
			case(EncoderContext::state_running):
			case(EncoderContext::state_wait_pmt):
			{
				count++;
				break;
			}
			default:
				break;
		}
	}

	return(count);
}

void eEncoder::navigation_event(int encoder_index, int event)
{
	eDebug("[eEncoder] navigation event: %d %d", encoder_index, event);

	if((encoder_index < 0) || (encoder_index >= (int)encoder.size()))
		return;

	if(event == eDVBServicePMTHandler::eventTuned)
	{
		eDebug("[eEncoder] navigation event tuned: %d %d", encoder_index, event);

		if(encoder[encoder_index].state == EncoderContext::state_wait_pmt)
		{
			ePtr<iPlayableService> service;
			ePtr<iTapService> tservice;
			ePtr<iServiceInformation> info;
			std::vector<int> pids;

			encoder[encoder_index].navigation_instance->getCurrentService(service);
			service->info(info);

			int vpid = info->getInfo(iServiceInformation::sVideoPID);
			int apid = info->getInfo(iServiceInformation::sAudioPID);
			int pmtpid = info->getInfo(iServiceInformation::sPMTPID);

			if((vpid > 0) && (apid > 0) && (pmtpid > 0))
			{
				eDebug("[eEncoder] info complete, vpid: %d (0x%x), apid: %d (0x%x), pmptpid: %d (0x%x)", vpid, vpid, apid, apid, pmtpid, pmtpid);

				pids.push_back(pmtpid);
				pids.push_back(vpid);
				pids.push_back(apid);

				if(ioctl(encoder[encoder_index].encoder_fd, IOCTL_BROADCOM_SET_PMTPID_MIPS, pmtpid) ||
						ioctl(encoder[encoder_index].encoder_fd, IOCTL_BROADCOM_SET_VPID_MIPS, vpid) ||
						ioctl(encoder[encoder_index].encoder_fd, IOCTL_BROADCOM_SET_APID_MIPS, apid))
				{
					eDebug("[eEncoder] set ioctl(mips) failed");

					if(ioctl(encoder[encoder_index].encoder_fd, IOCTL_BROADCOM_SET_PMTPID_ARM, pmtpid) ||
							ioctl(encoder[encoder_index].encoder_fd, IOCTL_BROADCOM_SET_VPID_ARM, vpid) ||
							ioctl(encoder[encoder_index].encoder_fd, IOCTL_BROADCOM_SET_APID_ARM, apid))
					{
						eWarning("[eEncoder] set ioctl(arm) failed too, giving up");
						freeEncoder(encoder[encoder_index].encoder_fd);
						return;
					}
				}

				encoder[encoder_index].run();

				if(encoder[encoder_index].file_fd < 0)
				{
					service->tap(tservice);

					if(tservice == nullptr)
					{
						eWarning("[eEncoder] tap service failed");
						freeEncoder(encoder[encoder_index].encoder_fd);
						return;
					}

					tservice->startTapToFD(encoder[encoder_index].encoder_fd, pids);
				}
				else
				{
					service->stop();

					if(encoder[encoder_index].stream_thread != nullptr)
					{
						eWarning("[eEncoder] datapump already running");
						return;
					}

					encoder[encoder_index].stream_thread = new eDVBRecordStreamThread(188, 188 * 256, true);
					encoder[encoder_index].stream_thread->setTargetFD(encoder[encoder_index].encoder_fd);
					encoder[encoder_index].stream_thread->start(encoder[encoder_index].file_fd);
				}

				encoder[encoder_index].state = EncoderContext::state_running;
			}
		}
	}
}

void eEncoder::navigation_event_0(int event)
{
	navigation_event(0, event);
}

void eEncoder::navigation_event_1(int event)
{
	navigation_event(1, event);
}

#ifdef DREAMNEXTGEN
void eEncoder::EncoderContext::threadAmlogicAvc(void)
{
	int avc_fd = -1;
	int grab_fd = -1;
	void *avc_map = MAP_FAILED;
	void *grab_map = MAP_FAILED;
	size_t grab_map_length = 0;
	unsigned long grab_canvas = 0;
	amlogic_avc_init_result init;
	std::vector<uint8_t> sequence;
	std::vector<uint8_t> frame;
	std::vector<uint8_t> access_unit;
	uint32_t out_width = width > 0 ? (uint32_t)width : 1280;
	uint32_t out_height = height > 0 ? (uint32_t)height : 720;
	int fps = framerate > 1000 ? (framerate + 500) / 1000 : framerate;
	uint64_t pts90k = 0;
	uint64_t start_us = 0;
	uint64_t next_frame_us = 0;
	uint64_t frame_interval_us;
	uint32_t qp;
	unsigned frame_index = 0;
	unsigned gop_frames;
	bool logged_waiting_for_grabber = false;
	bool logged_first_grabber_frame = false;
	ts_mux_state mux;
	char devinfo[64];
	struct videograbber_setup_t setup;
	struct videograbber_vframe_t vf;

	hasStarted();

	sigset_t sigpipe_set;
	sigemptyset(&sigpipe_set);
	sigaddset(&sigpipe_set, SIGPIPE);
	pthread_sigmask(SIG_BLOCK, &sigpipe_set, NULL);

	if (fps <= 0)
		fps = 25;
	if (fps > 60)
		fps = 60;
	frame_interval_us = 1000000ULL / fps;
	gop_frames = fps * 2;
	if (!gop_frames)
		gop_frames = 50;
	qp = amlogic_avc_qp_for_bitrate(bitrate);

	memset(&mux, 0, sizeof(mux));
	mux.fd = output_fd;
	mux.program_number = program_number > 0 && program_number <= 0xffff ? (uint16_t)program_number : 1;

	eDebug("[eEncoder][Amlogic] thread start %ux%u fps=%d bitrate=%d qp=%u program=%u",
			out_width, out_height, fps, bitrate, qp, mux.program_number);

	usleep(500000);

	avc_fd = open("/dev/amvenc_avc", O_RDWR | O_CLOEXEC);
	if (avc_fd < 0)
	{
		eWarning("[eEncoder][Amlogic] open /dev/amvenc_avc failed: errno=%d (%s)", errno, strerror(errno));
		goto out;
	}

	memset(devinfo, 0, sizeof(devinfo));
	if (ioctl(avc_fd, AMVENC_AVC_IOC_GET_DEVINFO, devinfo) >= 0)
		eDebug("[eEncoder][Amlogic] device info: %s", devinfo);

	if (!amlogic_avc_config_init(avc_fd, out_width, out_height, init))
		goto out;

	avc_map = mmap(NULL, init.buffer_size, PROT_READ | PROT_WRITE, MAP_SHARED, avc_fd, 0);
	if (avc_map == MAP_FAILED)
	{
		eWarning("[eEncoder][Amlogic] mmap /dev/amvenc_avc failed: errno=%d (%s)", errno, strerror(errno));
		goto out;
	}

	if (!amlogic_avc_sequence(avc_fd, (uint8_t *)avc_map, init, qp, sequence))
		goto out;

	grab_fd = open("/dev/videograbber", O_RDWR | O_CLOEXEC);
	if (grab_fd < 0)
	{
		eWarning("[eEncoder][Amlogic] open /dev/videograbber failed: errno=%d (%s)", errno, strerror(errno));
		goto out;
	}

	memset(&setup, 0, sizeof(setup));
	setup.out_width = (int)out_width;
	setup.out_height = (int)out_height;
	setup.out_stride = (int)out_width * 3;
	setup.out_format = VIDEOGRABBER_FORMAT_RGB888;

	if (ioctl(grab_fd, VIDEOGRABBER_IOC_SETUP, &setup) < 0)
	{
		eWarning("[eEncoder][Amlogic] VIDEOGRABBER_IOC_SETUP failed: errno=%d (%s)", errno, strerror(errno));
		goto out;
	}

	if (!ts_write_pat_pmt(mux))
		goto out;

	start_us = clock_us();
	next_frame_us = start_us;

	while (state == state_running)
	{
		bool idr = (frame_index % gop_frames) == 0;
		size_t next_map_length;
		uint64_t frame_us = clock_us();
		pts90k = ((frame_us - start_us) * 90ULL) / 1000ULL;

		memset(&vf, 0, sizeof(vf));
		if (!logged_waiting_for_grabber)
		{
			logged_waiting_for_grabber = true;
			eDebug("[eEncoder][Amlogic] waiting for first videograbber frame");
		}
		if (ioctl(grab_fd, VIDEOGRABBER_IOC_GET_FRAME, &vf) < 0)
		{
			eWarning("[eEncoder][Amlogic] VIDEOGRABBER_IOC_GET_FRAME failed: errno=%d (%s)", errno, strerror(errno));
			break;
		}
		if (!logged_first_grabber_frame)
		{
			logged_first_grabber_frame = true;
			eDebug("[eEncoder][Amlogic] first videograbber frame canvas=0x%lx width=%d height=%d stride=%d",
					vf.canvas_phys_addr[0], vf.width[0], vf.height[0], vf.stride[0]);
		}

		if (vf.width[0] != (int)out_width || vf.height[0] != (int)out_height || vf.stride[0] < (int)out_width * 3)
		{
			eWarning("[eEncoder][Amlogic] videograbber geometry mismatch width=%d height=%d stride=%d",
					vf.width[0], vf.height[0], vf.stride[0]);
			break;
		}

		next_map_length = (size_t)vf.stride[0] * (size_t)vf.height[0];
		if (grab_map == MAP_FAILED || grab_canvas != vf.canvas_phys_addr[0] || grab_map_length != next_map_length)
		{
			if (grab_map != MAP_FAILED)
			{
				munmap(grab_map, grab_map_length);
				grab_map = MAP_FAILED;
			}
			grab_canvas = vf.canvas_phys_addr[0];
			grab_map_length = next_map_length;
			grab_map = mmap(NULL, grab_map_length, PROT_READ, MAP_SHARED, grab_fd, (off_t)grab_canvas);
			if (grab_map == MAP_FAILED)
			{
				eWarning("[eEncoder][Amlogic] mmap /dev/videograbber failed: errno=%d (%s)", errno, strerror(errno));
				break;
			}
		}

		rgb888_to_nv21((uint8_t *)avc_map + init.dct_offset, (const uint8_t *)grab_map, out_width, out_height, (uint32_t)vf.stride[0]);

		if (!amlogic_avc_encode_frame(avc_fd, (uint8_t *)avc_map, init, out_width, out_height, idr, qp, frame))
			break;

		if (idr && frame_index && !ts_write_pat_pmt(mux))
			break;

		if (idr)
		{
			access_unit = sequence;
			access_unit.insert(access_unit.end(), frame.begin(), frame.end());
		}
		else
		{
			access_unit = frame;
		}
		h264_prepend_aud_if_needed(access_unit);

		if (!ts_write_h264_access_unit(mux, &access_unit[0], access_unit.size(), pts90k, idr))
			break;

		if (frame_index == 0 || (fps > 0 && (frame_index % fps) == 0))
		{
			eDebug("[eEncoder][Amlogic] frame=%u type=%s frame_size=%u au_size=%u pts90k=%llu",
					frame_index, idr ? "IDR" : "P",
					(unsigned int)frame.size(), (unsigned int)access_unit.size(),
					(unsigned long long)pts90k);
		}

		frame_index++;
		next_frame_us += frame_interval_us;
		frame_us = clock_us();
		if (frame_us < next_frame_us)
			usleep(next_frame_us - frame_us);
		else if (frame_us > next_frame_us + frame_interval_us)
			next_frame_us = frame_us;
	}

out:
	if (grab_map != MAP_FAILED)
		munmap(grab_map, grab_map_length);
	if (avc_map != MAP_FAILED)
		munmap(avc_map, init.buffer_size);
	if (grab_fd >= 0)
		close(grab_fd);
	if (avc_fd >= 0)
		close(avc_fd);
	if (output_fd >= 0)
	{
		close(output_fd);
		output_fd = -1;
	}
	eDebug("[eEncoder][Amlogic] thread finish frames=%u", frame_index);
}
#endif

void eEncoder::EncoderContext::threadDreamSource(void)
{
	GstElement *pipeline = NULL;
	GstBus *bus = NULL;
	GError *error = NULL;
	std::string pipeline_description;

	hasStarted();

	if(output_fd < 0)
	{
		eWarning("[eEncoder][Dreamsource] thread started without output fd");
		return;
	}

	if(input_mode == eStreamServer::INPUT_MODE_LIVE)
		dreamsource_wait_service_ready(navigation_instance, 5000);
	else
		eDebug("[eEncoder][Dreamsource] skip DVB service readiness wait for input-mode=%d", input_mode);

	pipeline_description = dreamsource_pipeline_description(output_fd, bitrate, width, height, framerate, input_mode);
	eDebug("[eEncoder][Dreamsource] pipeline: %s", pipeline_description.c_str());

	pipeline = gst_parse_launch(pipeline_description.c_str(), &error);
	if(!pipeline)
	{
		if(error)
		{
			eWarning("[eEncoder][Dreamsource] pipeline creation failed: %s", error->message);
			g_error_free(error);
		}
		else
			eWarning("[eEncoder][Dreamsource] pipeline creation failed");
		goto out;
	}

	bus = gst_element_get_bus(pipeline);
	if(gst_element_set_state(pipeline, GST_STATE_PLAYING) == GST_STATE_CHANGE_FAILURE)
	{
		eWarning("[eEncoder][Dreamsource] failed to set pipeline to PLAYING");
		if(bus)
		{
			GstMessage *message = gst_bus_timed_pop_filtered(bus, GST_SECOND,
				(GstMessageType)(GST_MESSAGE_ERROR | GST_MESSAGE_EOS));
			dreamsource_log_gst_message(message);
			if(message)
				gst_message_unref(message);
		}
		goto out;
	}

	while(state == state_running)
	{
		GstMessage *message = gst_bus_timed_pop_filtered(bus, 250 * GST_MSECOND,
			(GstMessageType)(GST_MESSAGE_ERROR | GST_MESSAGE_EOS));

		if(!message)
			continue;

		switch(GST_MESSAGE_TYPE(message))
		{
			case GST_MESSAGE_ERROR:
			{
				dreamsource_log_gst_message(message);
				gst_message_unref(message);
				goto out;
			}
			case GST_MESSAGE_EOS:
			{
				dreamsource_log_gst_message(message);
				gst_message_unref(message);
				goto out;
			}
			default:
			{
				gst_message_unref(message);
				break;
			}
		}
	}

out:
	if(pipeline)
		gst_element_set_state(pipeline, GST_STATE_NULL);
	if(bus)
		gst_object_unref(bus);
	if(pipeline)
		gst_object_unref(pipeline);
	if(output_fd >= 0)
	{
		close(output_fd);
		output_fd = -1;
	}
	eDebug("[eEncoder][Dreamsource] thread finish");
}

void eEncoder::EncoderContext::thread(void)
{
	if (backend == backend_dreamsource)
	{
		threadDreamSource();
		return;
	}

#ifdef DREAMNEXTGEN
	if (backend == backend_amlogic_avc)
	{
		threadAmlogicAvc();
		return;
	}
#endif

	hasStarted();

	eDebug("[EncoderContext %x] start ioctl transcoding", (int)pthread_self());

	if(ioctl(encoder_fd, IOCTL_BROADCOM_START_TRANSCODING, 0))
		eWarning("[eEncoder] thread encoder failed");

	eDebug("[EncoderContext %x] finish ioctl transcoding", (int)pthread_self());
}

eAutoInitPtr<eEncoder> init_eEncoder(eAutoInitNumbers::service + 1, "Encoders");
