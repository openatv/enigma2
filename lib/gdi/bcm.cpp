/*
 * Dreambox Broadcom FBIO_ACCEL backend.
 *
 * Legacy Dreambox models use the old Broadcom operation lists.
 * DM9x0 with DREAMBCM_ION_ACCEL uses the DreamOS-style ION/GFBDC path:
 *   - 32-bit copy:        len=92
 *   - fill:               len=104
 *   - 32-bit composition: len=158
 *   - indexed composition: len=164
 *
 * The DM9x0 path deliberately does not use the legacy 0x80 blend opcode.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <fcntl.h>
#include <unistd.h>
#include <linux/fb.h>
#include <sys/mman.h>
#include <sys/ioctl.h>
#include <time.h>
#include <limits.h>
#include <lib/base/eerror.h>

#define FBIO_ACCEL  0x23

/*
 * Define DREAMBCM_RUNTIME_DEBUG for development builds to keep environment
 * switches, trace logging and statistics counters. Production/beta builds leave
 * it undefined so the DM9x0 path uses fixed defaults without getenv/stat
 * overhead in the hot path.
 */

static unsigned int displaylist[1024];
static int ptr = 0;
static bool supportblendingflags = true;
static bool accumulateoperations = false;

#define P(x, y) do { displaylist[ptr++] = x; displaylist[ptr++] = y; } while (0)
#define C(x) P(x, 0)

static int fb_fd = -1;
static int exec_list(const char *reason = "exec");

#ifdef DREAMBCM_ION_ACCEL
#ifdef DREAMBCM_RUNTIME_DEBUG
#define DREAMBCM_BCM_STAT_INC(x) do { ++(x); } while (0)
#else
#define DREAMBCM_BCM_STAT_INC(x) do { } while (0)
#endif
static unsigned int s_bcm_fill_calls = 0;
static unsigned int s_bcm_blit_calls = 0;
static unsigned int s_bcm_blit_flags_zero = 0;
static unsigned int s_bcm_blit_flags_nonzero = 0;
static unsigned int s_bcm_blend_direct_calls = 0;
static unsigned int s_bcm_blend_direct_ok = 0;
static unsigned int s_bcm_blend_direct_fail = 0;
static unsigned int s_bcm_sync_calls = 0;
static unsigned int s_bcm_sync_empty = 0;
static unsigned int s_bcm_sync_exec = 0;
static unsigned int s_bcm_accumulate_calls = 0;
static unsigned int s_bcm_exec_calls = 0;
static unsigned int s_bcm_exec_fail = 0;
static unsigned int s_bcm_exec_len_min = UINT_MAX;
static unsigned int s_bcm_exec_len_max = 0;
static unsigned long long s_bcm_exec_len_total = 0;
static unsigned int s_bcm_exec_len_0 = 0;
static unsigned int s_bcm_exec_len_1_40 = 0;
static unsigned int s_bcm_exec_len_41_80 = 0;
static unsigned int s_bcm_exec_len_81_120 = 0;
static unsigned int s_bcm_exec_len_121_160 = 0;
static unsigned int s_bcm_exec_len_gt_160 = 0;
static unsigned int s_bcm_exec_len_92 = 0;
static unsigned int s_bcm_exec_len_104 = 0;
static unsigned int s_bcm_exec_len_126 = 0;
static unsigned int s_bcm_exec_len_158 = 0;
static unsigned int s_bcm_exec_len_164 = 0;
static long long s_bcm_last_stats_ms = 0;

static bool dreambcm_bcm_stats_enabled()
{
#ifdef DREAMBCM_RUNTIME_DEBUG
	const char *value = getenv("DREAMBCM_BCM_STATS");
	return value && !(value[0] == '0' && value[1] == 0);
#else
	return false;
#endif
}


static bool dreambcm_bcm_dreamlist_enabled();
static bool dreambcm_bcm_dreamlist_compose_enabled();
static bool dreambcm_bcm_dreamlist_fill_enabled();
static bool dreambcm_bcm_dreamlist_direct_enabled();
static bool dreambcm_bcm_dreamlist_indexed_enabled();
static bool dreambcm_bcm_dreamlist_indexed_compose_enabled();
static bool dreambcm_bcm_dreamlist_exec77_enabled();
static bool dreambcm_bcm_color_swap_enabled();
static unsigned int dreambcm_bcm_argb_format();
static unsigned int dreambcm_bcm_indexed_palette_format();
static int dreambcm_bcm_indexed_key_value();
static void dreambcm_bcm_push_indexed_surface(int addr, int stride, int width, int height, int pal_addr);
static unsigned long dreambcm_bcm_fill_color_to_dreamos(unsigned long color);

static bool dreambcm_bcm_trace_enabled()
{
#ifdef DREAMBCM_RUNTIME_DEBUG
	const char *value = getenv("DREAMBCM_BCM_TRACE");
	return value && !(value[0] == '0' && value[1] == 0);
#else
	return false;
#endif
}

static int dreambcm_bcm_stats_interval()
{
#ifdef DREAMBCM_RUNTIME_DEBUG
	const char *value = getenv("DREAMBCM_BCM_STATS_INTERVAL");
	if (!value || !value[0])
		return 500;
	int interval = atoi(value);
	return interval > 0 ? interval : 500;
#else
	return 500;
#endif
}

static long long dreambcm_bcm_now_ms()
{
	struct timespec ts;
	if (clock_gettime(CLOCK_MONOTONIC, &ts) < 0)
		return 0;
	return ((long long)ts.tv_sec * 1000LL) + ((long long)ts.tv_nsec / 1000000LL);
}

static void dreambcm_bcm_count_len(unsigned int len)
{
#ifdef DREAMBCM_RUNTIME_DEBUG
	if (!s_bcm_exec_calls || len < s_bcm_exec_len_min)
		s_bcm_exec_len_min = len;
	if (len > s_bcm_exec_len_max)
		s_bcm_exec_len_max = len;
	s_bcm_exec_len_total += len;

	if (len == 0)
		DREAMBCM_BCM_STAT_INC(s_bcm_exec_len_0);
	else if (len <= 40)
		DREAMBCM_BCM_STAT_INC(s_bcm_exec_len_1_40);
	else if (len <= 80)
		DREAMBCM_BCM_STAT_INC(s_bcm_exec_len_41_80);
	else if (len <= 120)
		DREAMBCM_BCM_STAT_INC(s_bcm_exec_len_81_120);
	else if (len <= 160)
		DREAMBCM_BCM_STAT_INC(s_bcm_exec_len_121_160);
	else
		DREAMBCM_BCM_STAT_INC(s_bcm_exec_len_gt_160);

	if (len == 92)
		DREAMBCM_BCM_STAT_INC(s_bcm_exec_len_92);
	else if (len == 104)
		DREAMBCM_BCM_STAT_INC(s_bcm_exec_len_104);
	else if (len == 126)
		DREAMBCM_BCM_STAT_INC(s_bcm_exec_len_126);
	else if (len == 158)
		DREAMBCM_BCM_STAT_INC(s_bcm_exec_len_158);
	else if (len == 164)
		DREAMBCM_BCM_STAT_INC(s_bcm_exec_len_164);
#else
	(void)len;
#endif
}

static void dreambcm_bcm_dump_stats(const char *reason, bool force = false)
{
	if (!dreambcm_bcm_stats_enabled() && !dreambcm_bcm_trace_enabled())
		return;

	long long now = dreambcm_bcm_now_ms();
	int interval = dreambcm_bcm_stats_interval();
	if (!force && now && s_bcm_last_stats_ms && ((now - s_bcm_last_stats_ms) < interval))
		return;
	s_bcm_last_stats_ms = now;

	unsigned int min_len = s_bcm_exec_calls ? s_bcm_exec_len_min : 0;
	unsigned int avg_len = s_bcm_exec_calls ? (unsigned int)(s_bcm_exec_len_total / s_bcm_exec_calls) : 0;
	eDebug("[dreamBCM:bcm] stats reason=%s fill=%u blit=%u flags=%u/%u blend-direct=%u/%u/%u accumulate=%u sync=%u empty=%u exec-sync=%u exec=%u fail=%u len[min/avg/max]=%u/%u/%u bins[0,1-40,41-80,81-120,121-160,>160]=%u/%u/%u/%u/%u/%u exact[92,104,126,158,164]=%u/%u/%u/%u/%u ptr=%d accum=%d",
		reason ? reason : "-",
		s_bcm_fill_calls, s_bcm_blit_calls,
		s_bcm_blit_flags_zero, s_bcm_blit_flags_nonzero,
		s_bcm_blend_direct_calls, s_bcm_blend_direct_ok, s_bcm_blend_direct_fail,
		s_bcm_accumulate_calls,
		s_bcm_sync_calls, s_bcm_sync_empty, s_bcm_sync_exec,
		s_bcm_exec_calls, s_bcm_exec_fail,
		min_len, avg_len, s_bcm_exec_len_max,
		s_bcm_exec_len_0, s_bcm_exec_len_1_40, s_bcm_exec_len_41_80,
		s_bcm_exec_len_81_120, s_bcm_exec_len_121_160, s_bcm_exec_len_gt_160,
		s_bcm_exec_len_92, s_bcm_exec_len_104, s_bcm_exec_len_126, s_bcm_exec_len_158, s_bcm_exec_len_164,
		ptr, accumulateoperations ? 1 : 0);
}
#else
static inline bool dreambcm_bcm_trace_enabled()
{
	return false;
}
static inline void dreambcm_bcm_dump_stats(const char *, bool = false)
{
}
#endif

int bcm_accel_init(void)
{
	fb_fd = open("/dev/fb0", O_RDWR);
	if (fb_fd < 0)
	{
		eDebug("[bcm] /dev/fb0 %m");
		return 1;
	}
	if (exec_list("init"))
	{
		eDebug("[bcm] interface not available - %m");
		close(fb_fd);
		fb_fd = -1;
		return 1;
	}

#ifdef DREAMBCM_ION_ACCEL
	/*
	 * DM9x0 DreamOS-style path:
	 * advertise alpha support to upper layers, but do not use legacy 0x80.
	 * Real DreamOS dumps show composition via 0x5e..0x66 + 0x51.
	 */
	supportblendingflags = true;
#ifdef DREAMBCM_RUNTIME_DEBUG
	eDebug("[dreamBCM:bcm] FBIO_ACCEL backend active dreamos-path=1 alpha-advertise=%d dreamlist=%d compose=%d fill=%d indexed=%d indexed-compose=%d direct=%d color-swap=%d format=0x%x indexed-pal=0x%x indexed-key=%d exec77=%d",
		supportblendingflags ? 1 : 0,
		dreambcm_bcm_dreamlist_enabled() ? 1 : 0,
		dreambcm_bcm_dreamlist_compose_enabled() ? 1 : 0,
		dreambcm_bcm_dreamlist_fill_enabled() ? 1 : 0,
		dreambcm_bcm_dreamlist_indexed_enabled() ? 1 : 0,
		dreambcm_bcm_dreamlist_indexed_compose_enabled() ? 1 : 0,
		dreambcm_bcm_dreamlist_direct_enabled() ? 1 : 0,
		dreambcm_bcm_color_swap_enabled() ? 1 : 0,
		dreambcm_bcm_argb_format(),
		dreambcm_bcm_indexed_palette_format(),
		dreambcm_bcm_indexed_key_value(),
		dreambcm_bcm_dreamlist_exec77_enabled() ? 1 : 0);
#endif
#else
	/* now test for blending flags support */
	P(0x80, 0);
	if (exec_list("blend-probe"))
	{
		supportblendingflags = false;
	}
#endif
#ifdef FORCE_NO_BLENDING_ACCELERATION
	/* hardware doesn't allow us to detect whether the opcode is working */
	supportblendingflags = false;
#endif
	return 0;
}

void bcm_accel_close(void)
{
	dreambcm_bcm_dump_stats("close", true);
	if (fb_fd >= 0)
	{
		close(fb_fd);
		fb_fd = -1;
	}
}

int bcm_accel_sync();
int bcm_accel_accumulate();

#ifdef DREAMBCM_ION_ACCEL
static bool dreambcm_bcm_env_enabled(const char *name, bool default_value)
{
#ifdef DREAMBCM_RUNTIME_DEBUG
	const char *value = getenv(name);
	if (!value || !value[0])
		return default_value;
	if (value[0] == '0' && value[1] == 0)
		return false;
	if (!strcmp(value, "no") || !strcmp(value, "false") || !strcmp(value, "off"))
		return false;
	return true;
#else
	(void)name;
	return default_value;
#endif
}

static bool dreambcm_bcm_dreamlist_enabled()
{
	return dreambcm_bcm_env_enabled("DREAMBCM_DREAMLIST", true);
}

static bool dreambcm_bcm_dreamlist_compose_enabled()
{
	return dreambcm_bcm_env_enabled("DREAMBCM_DREAMLIST_COMPOSE", true);
}

static bool dreambcm_bcm_dreamlist_fill_enabled()
{
	/*
	 * DM9x0 uses the DreamOS len=104 fill list by default.
	 * OpenATV fill colors are converted in dreambcm_bcm_fill_color_to_dreamos().
	 */
	return dreambcm_bcm_env_enabled("DREAMBCM_DREAMLIST_FILL", true);
}

static bool dreambcm_bcm_dreamlist_direct_enabled()
{
	/*
	 * DreamOS submits one complete FBIO_ACCEL list at a time. Do the same
	 * for DM9x0 DreamOS-style lists instead of batching them into a larger
	 * accumulated OpenATV list.
	 */
	return dreambcm_bcm_env_enabled("DREAMBCM_DREAMLIST_DIRECT", true);
}

static bool dreambcm_bcm_dreamlist_indexed_enabled()
{
	/*
	 * Indexed/palette alpha composition uses the DreamOS len=158 structure
	 * with the legacy palette entry format 0x7e48888. This fixes the visible
	 * alpha hole seen when indexed sources used the legacy path.
	 */
	return dreambcm_bcm_env_enabled("DREAMBCM_DREAMLIST_INDEXED", true);
}

static bool dreambcm_bcm_dreamlist_indexed_compose_enabled()
{
	return dreambcm_bcm_env_enabled("DREAMBCM_DREAMLIST_INDEXED_COMPOSE", true);
}

static bool dreambcm_bcm_dreamlist_exec77_enabled()
{
	return dreambcm_bcm_env_enabled("DREAMBCM_DREAMLIST_EXEC77", false);
}

static bool dreambcm_bcm_color_swap_enabled()
{
	return dreambcm_bcm_env_enabled("DREAMBCM_DREAMLIST_COLOR_SWAP", true);
}

static unsigned int dreambcm_bcm_argb_format()
{
#ifdef DREAMBCM_RUNTIME_DEBUG
	const char *value = getenv("DREAMBCM_DREAMLIST_FORMAT");
	if (value && !strcmp(value, "legacy"))
		return 0x07e48888;
#endif
	return 0x07c68888;
}

static unsigned int dreambcm_bcm_indexed_palette_format()
{
#ifdef DREAMBCM_RUNTIME_DEBUG
	const char *value = getenv("DREAMBCM_DREAMLIST_INDEXED_PAL_FORMAT");

	if (value && !strcmp(value, "dreamos"))
		return 0x07c68888;
	if (value && !strcmp(value, "legacy07"))
		return 0x07e48888;
#endif

	/*
	 * Indexed palette entries must use the legacy palette format. Using the
	 * DreamOS 32-bit surface format here produces black indexed graphics.
	 */
	return 0x7e48888;
}

static int dreambcm_bcm_indexed_key_value()
{
#ifdef DREAMBCM_RUNTIME_DEBUG
	const char *value = getenv("DREAMBCM_DREAMLIST_INDEXED_KEY");
	if (value)
		return atoi(value) ? 1 : 0;
#endif
	return 1;
}

static unsigned long dreambcm_bcm_fill_color_to_dreamos(unsigned long color)
{
	if (!dreambcm_bcm_color_swap_enabled())
		return color;

	/*
	 * OpenATV's legacy fill color path feeds the old Broadcom format.
	 * DreamOS len=104 fill lists use FORMAT=0x07c68888. Swap R/B to avoid
	 * the blue->brown effect seen in v10.
	 */
	return (color & 0xff00ff00UL) |
		((color & 0x00ff0000UL) >> 16) |
		((color & 0x000000ffUL) << 16);
}

static void dreambcm_bcm_push_surface(int addr, int stride, int width, int height, unsigned int format)
{
	P(0x0, addr);
	P(0x1, stride);
	P(0x2, width);
	P(0x3, height);
	P(0x4, format);
}

static void dreambcm_bcm_push_indexed_surface(int addr, int stride, int width, int height, int pal_addr)
{
	/*
	 * Indexed source descriptor: legacy palette setup combined with the
	 * DreamOS composition sequence.
	 */
	P(0x0, addr);
	P(0x1, stride);
	P(0x2, width);
	P(0x3, height);
	P(0x4, 0x12e40008);
	P(0x78, 256);
	P(0x79, pal_addr);
	P(0x7a, dreambcm_bcm_indexed_palette_format());
}

static void dreambcm_bcm_push_zero_surface()
{
	dreambcm_bcm_push_surface(0, 0, 0, 0, 0);
}

static void dreambcm_bcm_push_rect(int x, int y, int width, int height)
{
	P(0x2e, x);
	P(0x2f, y);
	P(0x30, width);
	P(0x31, height);
}

static void dreambcm_bcm_push_key(int key_r)
{
	P(0x6f, key_r);
	P(0x70, 0);
	P(0x71, 2);
	P(0x72, 2);
	C(0x73);
}

static void dreambcm_bcm_push_resets()
{
	C(0x43);
	C(0x53);
	C(0x67);
	C(0x5b);
	C(0x75);
}

static void dreambcm_bcm_push_dream_blend_setup()
{
	/*
	 * DreamOS DM9x0 len=158 composition setup. This path does not use 0x80.
	 */
	P(0x5e, 0x00000003);
	P(0x5f, 0x00000005);
	P(0x60, 0x00000000);
	P(0x61, 0x00000007);
	P(0x62, 0x00000006);
	P(0x63, 0x00000000);
	P(0x64, 0x00000000);
	P(0x65, 0x00000000);

	P(0x5e, 0x00000005);
	P(0x5f, 0x00000002);
	P(0x60, 0x00000000);
	P(0x61, 0x00000009);
	P(0x62, 0x00000006);
	P(0x63, 0x00000000);
	P(0x64, 0x00000000);
	P(0x66, 0x00000000);
}

static void dreambcm_bcm_ensure_space(unsigned int needed_words)
{
	if (accumulateoperations && ((sizeof(displaylist) / sizeof(displaylist[0]) - ptr) < needed_words))
	{
		eDebug("[dreamBCM:bcm] not enough space for DreamOS list, sync first ptr=%d need=%u", ptr, needed_words);
		bcm_accel_sync();
		bcm_accel_accumulate();
	}
}

static bool dreambcm_bcm_begin_dreamos_direct(const char *reason)
{
	if (!dreambcm_bcm_dreamlist_direct_enabled())
		return false;

	if (accumulateoperations)
	{
		if (ptr)
		{
			DREAMBCM_BCM_STAT_INC(s_bcm_sync_exec);
			if (exec_list(reason))
				eDebug("[dreamBCM:bcm] pre-direct flush failed for %s", reason);
		}
		accumulateoperations = false;
		return true;
	}
	return false;
}

static void dreambcm_bcm_restore_accumulate(bool restore)
{
	if (restore)
		bcm_accel_accumulate();
}
#endif

int exec_list(const char *reason)
{
	int ret;
	struct
	{
		void *ptr;
		int len;
	} l;

	if (fb_fd < 0) return -1;

	l.ptr = displaylist;
	l.len = ptr;
#ifdef DREAMBCM_ION_ACCEL
	DREAMBCM_BCM_STAT_INC(s_bcm_exec_calls);
	dreambcm_bcm_count_len((unsigned int)l.len);
#endif
	ret = ioctl(fb_fd, FBIO_ACCEL, &l);
#ifdef DREAMBCM_ION_ACCEL
	if (ret)
		DREAMBCM_BCM_STAT_INC(s_bcm_exec_fail);
	if (dreambcm_bcm_trace_enabled())
		eDebug("[dreamBCM:bcm] exec reason=%s len=%d ret=%d", reason ? reason : "-", l.len, ret);
	dreambcm_bcm_dump_stats(reason);
#endif
	ptr = 0;
	return ret;
}

bool bcm_accel_has_alphablending()
{
	return supportblendingflags;
}

int bcm_accel_accumulate()
{
#ifdef SUPPORT_ACCUMULATED_ACCELERATION_OPERATIONS
#ifdef DREAMBCM_ION_ACCEL
	DREAMBCM_BCM_STAT_INC(s_bcm_accumulate_calls);
	dreambcm_bcm_dump_stats("accumulate");
#endif
	accumulateoperations = true;
	return 0;
#else
	return -1;
#endif
}

int bcm_accel_sync()
{
	int retval = 0;
#ifdef DREAMBCM_ION_ACCEL
	DREAMBCM_BCM_STAT_INC(s_bcm_sync_calls);
#endif
	if (accumulateoperations)
	{
		if (ptr)
		{
#ifdef DREAMBCM_ION_ACCEL
			DREAMBCM_BCM_STAT_INC(s_bcm_sync_exec);
			if (dreambcm_bcm_trace_enabled())
				eDebug("[dreamBCM:bcm] sync exec ptr=%d", ptr);
#endif
			retval = exec_list("sync");
		}
#ifdef DREAMBCM_ION_ACCEL
		else
		{
			DREAMBCM_BCM_STAT_INC(s_bcm_sync_empty);
			if (dreambcm_bcm_trace_enabled())
				eDebug("[dreamBCM:bcm] sync empty");
		}
#endif
		accumulateoperations = false;
	}
#ifdef DREAMBCM_ION_ACCEL
	else
	{
		DREAMBCM_BCM_STAT_INC(s_bcm_sync_empty);
		if (dreambcm_bcm_trace_enabled())
			eDebug("[dreamBCM:bcm] sync without accumulate ptr=%d", ptr);
	}
	dreambcm_bcm_dump_stats("sync-call");
#endif
	return retval;
}

int bcm_accel_blit(
		int src_addr, int src_width, int src_height, int src_stride, int src_format,
		int dst_addr, int dst_width, int dst_height, int dst_stride,
		int src_x, int src_y, int width, int height,
		int dst_x, int dst_y, int dwidth, int dheight,
		int pal_addr, int flags)
{
	int ret = 0;
#ifdef DREAMBCM_ION_ACCEL
	bool restore_accumulate = false;

	DREAMBCM_BCM_STAT_INC(s_bcm_blit_calls);
	if (flags)
		DREAMBCM_BCM_STAT_INC(s_bcm_blit_flags_nonzero);
	else
		DREAMBCM_BCM_STAT_INC(s_bcm_blit_flags_zero);

	if (dreambcm_bcm_trace_enabled())
		eDebug("[dreamBCM:bcm] blit src=0x%x dst=0x%x fmt=%d src=%dx%d+%d,%d dst=%dx%d+%d,%d flags=0x%x ptr=%d accum=%d dreamlist=%d",
			src_addr, dst_addr, src_format, width, height, src_x, src_y, dwidth, dheight, dst_x, dst_y,
			flags, ptr, accumulateoperations ? 1 : 0,
			dreambcm_bcm_dreamlist_enabled() ? 1 : 0);

	/*
	 * DM9x0 DreamOS path for 32-bit surfaces.
	 * No legacy 0x80. No CPU fallback from here on success/failure decision:
	 * the caller receives the real ioctl result.
	 */
	if (dreambcm_bcm_dreamlist_enabled() && src_format == 0)
	{
		unsigned int fmt = dreambcm_bcm_argb_format();

		if (flags && dreambcm_bcm_dreamlist_compose_enabled())
		{
			restore_accumulate = dreambcm_bcm_begin_dreamos_direct("pre-dreamos-compose-flush");

			dreambcm_bcm_ensure_space(158);

			dreambcm_bcm_push_resets();
			dreambcm_bcm_push_key(1);
			dreambcm_bcm_push_dream_blend_setup();

			P(0x33, 0x00030003);
			P(0x41, 0x00000000);

			dreambcm_bcm_push_surface(src_addr, src_stride, src_width, src_height, fmt);
			C(0x05);

			dreambcm_bcm_push_zero_surface();
			C(0x06);

			dreambcm_bcm_push_rect(src_x, src_y, width, height);
			C(0x32);

			/*
			 * Destination as input surface. This matches DreamOS len=158:
			 * current destination is sampled, source is composed over it,
			 * and the result is written back to the destination output.
			 */
			dreambcm_bcm_push_surface(dst_addr, dst_stride, dst_width, dst_height, fmt);
			C(0x45);

			dreambcm_bcm_push_zero_surface();
			C(0x46);

			dreambcm_bcm_push_rect(dst_x, dst_y, dwidth, dheight);
			C(0x51);

			dreambcm_bcm_push_surface(dst_addr, dst_stride, dst_width, dst_height, fmt);
			C(0x69);

			dreambcm_bcm_push_zero_surface();
			C(0x6a);

			dreambcm_bcm_push_rect(dst_x, dst_y, dwidth, dheight);
			C(0x6e);

			if (dreambcm_bcm_dreamlist_exec77_enabled())
				C(0x77);

			if (dreambcm_bcm_dreamlist_direct_enabled() || !accumulateoperations)
			{
				ret = exec_list("dreamos-compose-158");
				DREAMBCM_BCM_STAT_INC(s_bcm_blend_direct_calls);
				if (ret)
					DREAMBCM_BCM_STAT_INC(s_bcm_blend_direct_fail);
				else
					DREAMBCM_BCM_STAT_INC(s_bcm_blend_direct_ok);
				dreambcm_bcm_dump_stats(ret ? "dreamos-compose-158-fail" : "dreamos-compose-158-ok");
				dreambcm_bcm_restore_accumulate(restore_accumulate);
				return ret;
			}

			return 0;
		}

		restore_accumulate = dreambcm_bcm_begin_dreamos_direct("pre-dreamos-copy-flush");

		dreambcm_bcm_ensure_space(92);

		dreambcm_bcm_push_resets();
		dreambcm_bcm_push_key(0);

		P(0x33, 0x00030003);
		P(0x41, 0x00000000);

		dreambcm_bcm_push_surface(src_addr, src_stride, src_width, src_height, fmt);
		C(0x05);

		dreambcm_bcm_push_zero_surface();
		C(0x06);

		dreambcm_bcm_push_rect(src_x, src_y, width, height);
		C(0x32);

		dreambcm_bcm_push_surface(dst_addr, dst_stride, dst_width, dst_height, fmt);
		C(0x69);

		dreambcm_bcm_push_zero_surface();
		C(0x6a);

		dreambcm_bcm_push_rect(dst_x, dst_y, dwidth, dheight);
		C(0x6e);

		if (dreambcm_bcm_dreamlist_exec77_enabled())
			C(0x77);

		if (dreambcm_bcm_dreamlist_direct_enabled() || !accumulateoperations)
		{
			ret = exec_list("dreamos-copy-92");
			dreambcm_bcm_restore_accumulate(restore_accumulate);
			return ret;
		}

		return 0;
	}
#endif
#ifdef DREAMBCM_ION_ACCEL
	if (dreambcm_bcm_dreamlist_enabled() && dreambcm_bcm_dreamlist_indexed_enabled() && src_format == 1 && flags && dreambcm_bcm_dreamlist_indexed_compose_enabled())
	{
		unsigned int fmt = dreambcm_bcm_argb_format();

		restore_accumulate = dreambcm_bcm_begin_dreamos_direct("pre-dreamos-indexed-compose-flush");

		/*
		 * DreamOS dumps did not contain indexed/palette lists, but the v12
		 * OpenATV trace shows the remaining alpha artifacts are fmt=1 +
		 * flags 0x2/0x4/0x6. This list keeps the DreamOS composition sequence
		 * and only swaps the source surface descriptor to indexed+palette.
		 */
		dreambcm_bcm_ensure_space(164);

		dreambcm_bcm_push_resets();
		dreambcm_bcm_push_key(dreambcm_bcm_indexed_key_value());
		dreambcm_bcm_push_dream_blend_setup();

		P(0x33, 0x00030003);
		P(0x41, 0x00000000);

		dreambcm_bcm_push_indexed_surface(src_addr, src_stride, src_width, src_height, pal_addr);
		C(0x05);

		dreambcm_bcm_push_zero_surface();
		C(0x06);

		dreambcm_bcm_push_rect(src_x, src_y, width, height);
		C(0x32);

		dreambcm_bcm_push_surface(dst_addr, dst_stride, dst_width, dst_height, fmt);
		C(0x45);

		dreambcm_bcm_push_zero_surface();
		C(0x46);

		dreambcm_bcm_push_rect(dst_x, dst_y, dwidth, dheight);
		C(0x51);

		dreambcm_bcm_push_surface(dst_addr, dst_stride, dst_width, dst_height, fmt);
		C(0x69);

		dreambcm_bcm_push_zero_surface();
		C(0x6a);

		dreambcm_bcm_push_rect(dst_x, dst_y, dwidth, dheight);
		C(0x6e);

		if (dreambcm_bcm_dreamlist_exec77_enabled())
			C(0x77);

		if (dreambcm_bcm_dreamlist_direct_enabled() || !accumulateoperations)
		{
			ret = exec_list("dreamos-indexed-compose-164");
			DREAMBCM_BCM_STAT_INC(s_bcm_blend_direct_calls);
			if (ret)
				DREAMBCM_BCM_STAT_INC(s_bcm_blend_direct_fail);
			else
				DREAMBCM_BCM_STAT_INC(s_bcm_blend_direct_ok);
			dreambcm_bcm_dump_stats(ret ? "dreamos-indexed-compose-164-fail" : "dreamos-indexed-compose-164-ok");
			dreambcm_bcm_restore_accumulate(restore_accumulate);
			return ret;
		}

		return 0;
	}
#endif

	/*
	 * Palette/unsupported source fallback. Indexed sources without alpha still
	 * use the legacy path. With DREAMBCM_ION_ACCEL this path deliberately does
	 * not emit opcode 0x80.
	 */
	if (accumulateoperations)
	{
		if (((sizeof(displaylist) / sizeof(displaylist[0]) - ptr) / 2) < 40)
		{
			eDebug("bcm_accel_blit: not enough space to accumulate");
			bcm_accel_sync();
			bcm_accel_accumulate();
		}
	}

	C(0x43); // reset source
	C(0x53); // reset dest
	C(0x5b); // reset pattern
	C(0x67); // reset blend
	C(0x75); // reset output

	P(0x0, src_addr);
	P(0x1, src_stride);
	P(0x2, src_width);
	P(0x3, src_height);
	switch (src_format)
	{
	case 0:
		P(0x4, 0x7e48888);
		break;
	case 1:
		P(0x4, 0x12e40008);
		P(0x78, 256);
		P(0x79, pal_addr);
		P(0x7a, 0x7e48888);
		break;
	default:
		return -1;
	}

	C(0x5);

	P(0x2e, src_x);
	P(0x2f, src_y);
	P(0x30, width);
	P(0x31, height);
	C(0x32);

	P(0x0, dst_addr);
	P(0x1, dst_stride);
	P(0x2, dst_width);
	P(0x3, dst_height);
	P(0x4, 0x7e48888);
	C(0x69);

	P(0x2e, dst_x);
	P(0x2f, dst_y);
	P(0x30, dwidth);
	P(0x31, dheight);
	C(0x6e);

#ifndef DREAMBCM_ION_ACCEL
	if (supportblendingflags && flags) P(0x80, flags);
#else
	(void)flags;
#endif

	C(0x77);

	if (!accumulateoperations)
		ret = exec_list("legacy-palette-blit");

#ifdef DREAMBCM_ION_ACCEL
	dreambcm_bcm_restore_accumulate(restore_accumulate);
#endif
	return ret;
}

void bcm_accel_fill(
		int dst_addr, int dst_width, int dst_height, int dst_stride,
		int x, int y, int width, int height,
		unsigned long color)
{
#ifdef DREAMBCM_ION_ACCEL
	DREAMBCM_BCM_STAT_INC(s_bcm_fill_calls);
	if (dreambcm_bcm_trace_enabled())
		eDebug("[dreamBCM:bcm] fill dst=0x%x rect=%dx%d+%d,%d color=0x%lx dreamcolor=0x%lx ptr=%d accum=%d dreamlist=%d",
			dst_addr, width, height, x, y, color, dreambcm_bcm_fill_color_to_dreamos(color),
			ptr, accumulateoperations ? 1 : 0,
			dreambcm_bcm_dreamlist_enabled() ? 1 : 0);

	if (dreambcm_bcm_dreamlist_enabled() && dreambcm_bcm_dreamlist_fill_enabled())
	{
		bool restore_accumulate = dreambcm_bcm_begin_dreamos_direct("pre-dreamos-fill-flush");
		unsigned int fmt = dreambcm_bcm_argb_format();
		unsigned long dream_color = dreambcm_bcm_fill_color_to_dreamos(color);

		dreambcm_bcm_ensure_space(104);

		dreambcm_bcm_push_resets();

		dreambcm_bcm_push_zero_surface();
		C(0x45);

		dreambcm_bcm_push_zero_surface();
		C(0x46);

		dreambcm_bcm_push_zero_surface();
		C(0x05);

		dreambcm_bcm_push_zero_surface();
		C(0x06);

		P(0x2d, dream_color);

		dreambcm_bcm_push_rect(x, y, width, height);
		C(0x6e);

		dreambcm_bcm_push_surface(dst_addr, dst_stride, dst_width, dst_height, fmt);
		C(0x69);

		dreambcm_bcm_push_zero_surface();
		C(0x6a);

		dreambcm_bcm_push_key(0);

		if (dreambcm_bcm_dreamlist_exec77_enabled())
			C(0x77);

		if (dreambcm_bcm_dreamlist_direct_enabled() || !accumulateoperations)
			exec_list("dreamos-fill-104");

		dreambcm_bcm_restore_accumulate(restore_accumulate);
		return;
	}
#endif

	if (accumulateoperations)
	{
		if (((sizeof(displaylist) / sizeof(displaylist[0]) - ptr) / 2) < 40)
		{
			eDebug("bcm_accel_fill: not enough space to accumulate");
			bcm_accel_sync();
			bcm_accel_accumulate();
		}
	}

	C(0x43); // reset source
	C(0x53); // reset dest
	C(0x5b); // reset pattern
	C(0x67); // reset blend
	C(0x75); // reset output

	P(0x0, 0);
	P(0x1, 0);
	P(0x2, 0);
	P(0x3, 0);
	P(0x4, 0);
	C(0x45);

	P(0x0, 0);
	P(0x1, 0);
	P(0x2, 0);
	P(0x3, 0);
	P(0x4, 0);
	C(0x5);

	P(0x2d, color);

	P(0x2e, x);
	P(0x2f, y);
	P(0x30, width);
	P(0x31, height);
	C(0x6e);

	P(0x0, dst_addr);
	P(0x1, dst_stride);
	P(0x2, dst_width);
	P(0x3, dst_height);
	P(0x4, 0x7e48888);
	C(0x69);

	P(0x6f, 0);
	P(0x70, 0);
	P(0x71, 2);
	P(0x72, 2);
	C(0x73);

	C(0x77);

	if (!accumulateoperations) exec_list("legacy-fill");
}
