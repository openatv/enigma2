#include <lib/gdi/dreamge2d.h>

#ifdef DREAMNEXTGEN

#include <lib/base/eerror.h>
#include <lib/gdi/erect.h>
#include <lib/gdi/gpixmap.h>

#include <errno.h>
#include <fcntl.h>
#include <map>
#include <new>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <unistd.h>

#ifndef O_CLOEXEC
#define O_CLOEXEC 02000000
#endif

#define DREAM_GE2D_IOC_MAGIC 'G'
#define DREAM_GE2D_GET_CAP 0x470b
#define DREAM_GE2D_FILLRECTANGLE 0x46fd
#define DREAM_GE2D_BLIT 0x46ff
#define DREAM_GE2D_BLEND 0x4700

#define DREAM_GE2D_CONFIG_EX _IOW(DREAM_GE2D_IOC_MAGIC, 0x01, struct dream_config_para_ex_s)
#define DREAM_GE2D_CONFIG_EX_MEM _IOW(DREAM_GE2D_IOC_MAGIC, 0x07, struct dream_config_ge2d_para_ex_s)
#define DREAM_GE2D_SYNC_DEVICE _IOW(DREAM_GE2D_IOC_MAGIC, 0x08, int)
#define DREAM_GE2D_SYNC_CPU _IOW(DREAM_GE2D_IOC_MAGIC, 0x09, int)

#define DREAM_GE2D_LITTLE_ENDIAN (1U << 24)
#define DREAM_GE2D_COLOR_MAP_SHIFT 20
#define DREAM_GE2D_COLOR_MAP_ARGB8888 (1U << DREAM_GE2D_COLOR_MAP_SHIFT)
#define DREAM_GE2D_FMT_S32_RGBA (DREAM_GE2D_LITTLE_ENDIAN | 0x00300U)
#define DREAM_GE2D_FORMAT_S32_ARGB (DREAM_GE2D_FMT_S32_RGBA | DREAM_GE2D_COLOR_MAP_ARGB8888)
#define DREAM_GE2D_FORMAT_S32_DREAMOS_FILL (DREAM_GE2D_LITTLE_ENDIAN | (2U << DREAM_GE2D_COLOR_MAP_SHIFT) | 0x00300U)
#define DREAM_GE2D_FILL_SUBMIT_OP_DREAMOS 0x00100010U

#define DREAM_OPERATION_ADD 0
#define DREAM_COLOR_FACTOR_SRC_ALPHA 6
#define DREAM_COLOR_FACTOR_ONE_MINUS_SRC_ALPHA 7
#define DREAM_ALPHA_FACTOR_ONE 1
#define DREAM_ALPHA_FACTOR_ONE_MINUS_SRC_ALPHA 3
#define DREAM_GE2D_BLEND_SRC_OVER (((DREAM_OPERATION_ADD & 0xff) << 24) | \
	((DREAM_COLOR_FACTOR_SRC_ALPHA & 0xf) << 20) | \
	((DREAM_COLOR_FACTOR_ONE_MINUS_SRC_ALPHA & 0xf) << 16) | \
	((DREAM_OPERATION_ADD & 0xff) << 8) | \
	((DREAM_ALPHA_FACTOR_ONE & 0xf) << 4) | \
	(DREAM_ALPHA_FACTOR_ONE_MINUS_SRC_ALPHA & 0xf))

#define DREAM_CANVAS_OSD0 0
#define DREAM_CANVAS_ALLOC 2
#define DREAM_CANVAS_TYPE_INVALID 3

#define DREAM_AML_GE2D_MEM_INVALID 2

#define DREAM_ION_IOC_MAGIC 'I'
#define DREAM_ION_IOC_MESON_PHYS_ADDR 8

#define DREAM_ION_IOC_ALLOC _IOWR(DREAM_ION_IOC_MAGIC, 0, struct dream_ion_allocation_data)
#define DREAM_ION_IOC_FREE _IOWR(DREAM_ION_IOC_MAGIC, 1, struct dream_ion_handle_data)
#define DREAM_ION_IOC_SHARE _IOWR(DREAM_ION_IOC_MAGIC, 4, struct dream_ion_fd_data)
#define DREAM_ION_IOC_CUSTOM _IOWR(DREAM_ION_IOC_MAGIC, 6, struct dream_ion_custom_data)
#define DREAM_ION_IOC_SYNC _IOWR(DREAM_ION_IOC_MAGIC, 7, struct dream_ion_fd_data)
#define DREAM_ION_IOC_INVALID_CACHE _IOWR(DREAM_ION_IOC_MAGIC, 9, struct dream_ion_fd_data)

#define DREAM_ION_DEFAULT_HEAP_MASK 0x16U
#define DREAM_ION_DEFAULT_FLAGS 0x0U
#define DREAM_ION_DEFAULT_ALIGN 0x1000U

#define DREAM_BLIT_ALPHA_TEST 1
#define DREAM_BLIT_ALPHA_BLEND 2
#define DREAM_BLIT_SCALE 4

struct dream_ge2d_rectangle_s
{
	int x;
	int y;
	int w;
	int h;
};

struct dream_ge2d_para_s
{
	unsigned int color;
	struct dream_ge2d_rectangle_s src1_rect;
	struct dream_ge2d_rectangle_s src2_rect;
	struct dream_ge2d_rectangle_s dst_rect;
	int op;
};

struct dream_src_dst_para_ex_s
{
	int canvas_index;
	int top;
	int left;
	int width;
	int height;
	int format;
	int mem_type;
	int color;
	unsigned char x_rev;
	unsigned char y_rev;
	unsigned char fill_color_en;
	unsigned char fill_mode;
};

struct dream_src_key_ctrl_s
{
	int key_enable;
	int key_color;
	int key_mask;
	int key_mode;
};

struct dream_config_planes_s
{
	unsigned long addr;
	unsigned int w;
	unsigned int h;
};

struct dream_config_para_ex_s
{
	struct dream_src_dst_para_ex_s src_para;
	struct dream_src_dst_para_ex_s src2_para;
	struct dream_src_dst_para_ex_s dst_para;

	struct dream_src_key_ctrl_s src_key;
	struct dream_src_key_ctrl_s src2_key;

	unsigned char src1_cmult_asel;
	unsigned char src2_cmult_asel;
	unsigned char src2_cmult_ad;
	int alu_const_color;
	unsigned char src1_gb_alpha_en;
	unsigned int src1_gb_alpha;
	unsigned char src2_gb_alpha_en;
	unsigned int src2_gb_alpha;
	unsigned int op_mode;
	unsigned char bitmask_en;
	unsigned char bytemask_only;
	unsigned int bitmask;
	unsigned char dst_xy_swap;

	unsigned int hf_init_phase;
	int hf_rpt_num;
	unsigned int hsc_start_phase_step;
	int hsc_phase_slope;
	unsigned int vf_init_phase;
	int vf_rpt_num;
	unsigned int vsc_start_phase_step;
	int vsc_phase_slope;
	unsigned char src1_vsc_phase0_always_en;
	unsigned char src1_hsc_phase0_always_en;
	unsigned char src1_hsc_rpt_ctrl;
	unsigned char src1_vsc_rpt_ctrl;

	struct dream_config_planes_s src_planes[4];
	struct dream_config_planes_s src2_planes[4];
	struct dream_config_planes_s dst_planes[4];
};

struct dream_config_planes_ion_s
{
	unsigned long addr;
	unsigned int w;
	unsigned int h;
	int shared_fd;
};

struct dream_config_para_ex_ion_s
{
	struct dream_src_dst_para_ex_s src_para;
	struct dream_src_dst_para_ex_s src2_para;
	struct dream_src_dst_para_ex_s dst_para;

	struct dream_src_key_ctrl_s src_key;
	struct dream_src_key_ctrl_s src2_key;

	unsigned char src1_cmult_asel;
	unsigned char src2_cmult_asel;
	unsigned char src2_cmult_ad;
	int alu_const_color;
	unsigned char src1_gb_alpha_en;
	unsigned int src1_gb_alpha;
	unsigned char src2_gb_alpha_en;
	unsigned int src2_gb_alpha;
	unsigned int op_mode;
	unsigned char bitmask_en;
	unsigned char bytemask_only;
	unsigned int bitmask;
	unsigned char dst_xy_swap;

	unsigned int hf_init_phase;
	int hf_rpt_num;
	unsigned int hsc_start_phase_step;
	int hsc_phase_slope;
	unsigned int vf_init_phase;
	int vf_rpt_num;
	unsigned int vsc_start_phase_step;
	int vsc_phase_slope;
	unsigned char src1_vsc_phase0_always_en;
	unsigned char src1_hsc_phase0_always_en;
	unsigned char src1_hsc_rpt_ctrl;
	unsigned char src1_vsc_rpt_ctrl;

	struct dream_config_planes_ion_s src_planes[4];
	struct dream_config_planes_ion_s src2_planes[4];
	struct dream_config_planes_ion_s dst_planes[4];
};

struct dream_config_para_ex_memtype_s
{
	int ge2d_magic;
	struct dream_config_para_ex_ion_s _ge2d_config_ex;
	unsigned int src1_mem_alloc_type;
	unsigned int src2_mem_alloc_type;
	unsigned int dst_mem_alloc_type;
};

struct dream_config_ge2d_para_ex_s
{
	union
	{
		struct dream_config_para_ex_ion_s para_config_ion;
		struct dream_config_para_ex_memtype_s para_config_memtype;
	};
};

typedef int dream_ion_user_handle_t;

struct dream_ion_allocation_data
{
	size_t len;
	size_t align;
	unsigned int heap_id_mask;
	unsigned int flags;
	dream_ion_user_handle_t handle;
};

struct dream_ion_fd_data
{
	dream_ion_user_handle_t handle;
	int fd;
};

struct dream_ion_handle_data
{
	dream_ion_user_handle_t handle;
};

struct dream_ion_custom_data
{
	unsigned int cmd;
	unsigned long arg;
};

struct dream_meson_phys_data
{
	int share_fd;
	unsigned int reserved0;
	unsigned long phys_addr;
	size_t size;
};

namespace
{
	struct DreamGE2DBuffer
	{
		gUnmanagedSurface *surface;
		dream_ion_user_handle_t handle;
		int fd;
		int width;
		int height;
		int stride;
		int size;
		unsigned long phys;
		size_t phys_size;
		void *data;
	};

	struct DreamGE2DTarget
	{
		int width;
		int height;
		int stride;
		unsigned long phys;
		int fd;
		bool managed;
		bool framebuffer;
		void *data;
	};

	struct DreamGE2DFramebuffer
	{
		void *base_data;
		unsigned long base_phys;
		int width;
		int height;
		int stride;
		int pages;
		size_t bytes;
		bool valid;
	};

	int s_ge2d_fd = -1;
	int s_ion_fd = -1;
	bool s_ge2d_disabled = false;
	bool s_ion_disabled = false;
	bool s_ge2d_logged_copy_failure = false;
	bool s_ge2d_logged_alloc_failure = false;
	bool s_ge2d_logged_accel_active = false;
	bool s_ge2d_logged_accel_disabled = false;
	bool s_runtime_initialized = false;
	bool s_flush_enabled = true;
	bool s_logged_flush_disabled = false;
	bool s_surface_accel_enabled = false;
	bool s_fill_accel_enabled = false;
	bool s_blit_accel_enabled = false;
	bool s_blend_accel_enabled = false;
	bool s_blend_scale_enabled = false;
	bool s_raw_phys_accel_enabled = false;
	bool s_raw_phys_warning_logged = false;
	bool s_fb_accel_enabled = false;
	bool s_fb_write_enabled = false;
	bool s_fb_fill_enabled = false;
	bool s_fb_blit_enabled = false;
	bool s_fb_blend_enabled = false;
	bool s_fb_msync_enabled = false;
	bool s_fb_pagecopy_enabled = true;
	bool s_fb_submit_dreamos_enabled = true;
	bool s_fb_submit_dreamos_fill_enabled = true;
	bool s_fb_submit_dreamos_blit_enabled = true;
	bool s_fb_submit_dreamos_blend_enabled = true;
	unsigned int s_fb_fill_dreamos_format = DREAM_GE2D_FORMAT_S32_DREAMOS_FILL;
	bool s_fb_pagecopy_logged = false;
	bool s_fb_pagecopy_warning_logged = false;
	bool s_fb_warning_logged = false;
	bool s_fb_logged_register = false;
	bool s_stats_enabled = false;
	bool s_trace_enabled = false;
	int s_stats_interval = 1000;
	int s_trace_limit = 80;
	int s_trace_count = 0;
	unsigned long long s_stats_events = 0;
	unsigned int s_ion_heap_mask = DREAM_ION_DEFAULT_HEAP_MASK;
	unsigned int s_ion_flags = DREAM_ION_DEFAULT_FLAGS;
	unsigned int s_ion_align = DREAM_ION_DEFAULT_ALIGN;
	int s_keep_ion_handle = 0;
	int s_min_surface_size = 0;
	int s_min_operation_size = 0;
	struct DreamGE2DStats
	{
		unsigned long long alloc_ok;
		unsigned long long alloc_fail;
		unsigned long long free_ok;
		unsigned long long fill_ok;
		unsigned long long fill_fallback;
		unsigned long long fill_fail;
		unsigned long long fill_ion_ok;
		unsigned long long fill_raw_ok;
		unsigned long long fill_fb_ok;
		unsigned long long blit_ok;
		unsigned long long blit_fallback;
		unsigned long long blit_fail;
		unsigned long long blit_ion_ok;
		unsigned long long blit_raw_ok;
		unsigned long long blit_fb_ok;
		unsigned long long blend_ok;
		unsigned long long blend_fallback;
		unsigned long long blend_fail;
		unsigned long long blend_ion_ok;
		unsigned long long blend_raw_ok;
		unsigned long long blend_fb_ok;
		unsigned long long pagecopy_ok;
		unsigned long long pagecopy_fallback;
		unsigned long long pagecopy_fail;
	};

	DreamGE2DStats s_stats;
	DreamGE2DFramebuffer s_fb;
	std::map<const gUnmanagedSurface *, DreamGE2DBuffer> s_buffers;

	void statsLog(const char *reason, bool force)
	{
		if (!s_stats_enabled && !force)
			return;
		eTrace("[dreamGE2D] stats%s%s: alloc=%llu/%llu free=%llu live=%u fill=%llu/%llu/%llu ion/raw/fb=%llu/%llu/%llu blit=%llu/%llu/%llu ion/raw/fb=%llu/%llu/%llu blend=%llu/%llu/%llu ion/raw/fb=%llu/%llu/%llu pagecopy=%llu/%llu/%llu",
			reason ? " " : "", reason ? reason : "",
			s_stats.alloc_ok, s_stats.alloc_fail, s_stats.free_ok, (unsigned int)s_buffers.size(),
			s_stats.fill_ok, s_stats.fill_fallback, s_stats.fill_fail, s_stats.fill_ion_ok, s_stats.fill_raw_ok, s_stats.fill_fb_ok,
			s_stats.blit_ok, s_stats.blit_fallback, s_stats.blit_fail, s_stats.blit_ion_ok, s_stats.blit_raw_ok, s_stats.blit_fb_ok,
			s_stats.blend_ok, s_stats.blend_fallback, s_stats.blend_fail, s_stats.blend_ion_ok, s_stats.blend_raw_ok, s_stats.blend_fb_ok,
			s_stats.pagecopy_ok, s_stats.pagecopy_fallback, s_stats.pagecopy_fail);
	}

	void statsEvent(const char *reason)
	{
		if (!s_stats_enabled)
			return;
		++s_stats_events;
		if (s_stats_interval > 0 && (s_stats_events % (unsigned long long)s_stats_interval) == 0)
			statsLog(reason, false);
	}

	void statsBlitFallback(bool blend, const char *reason)
	{
		if (blend)
			++s_stats.blend_fallback;
		else
			++s_stats.blit_fallback;
		statsEvent(reason);
	}

	void statsBlitFail(bool blend, const char *reason)
	{
		if (blend)
			++s_stats.blend_fail;
		else
			++s_stats.blit_fail;
		statsEvent(reason);
	}

	bool envFlagEnabled(const char *name, bool default_value)
	{
		const char *value = getenv(name);
		if (!value || !*value)
			return default_value;
		if (!strcmp(value, "0") || !strcasecmp(value, "no") || !strcasecmp(value, "false") || !strcasecmp(value, "off"))
			return false;
		return true;
	}

	int envIntValue(const char *name, int default_value)
	{
		const char *value = getenv(name);
		if (!value || !*value)
			return default_value;
		int parsed = atoi(value);
		return parsed >= 0 ? parsed : default_value;
	}

	unsigned int envUIntValue(const char *name, unsigned int default_value)
	{
		const char *value = getenv(name);
		if (!value || !*value)
			return default_value;
		char *end = 0;
		unsigned long parsed = strtoul(value, &end, 0);
		if (end == value)
			return default_value;
		return (unsigned int)parsed;
	}

	void initRuntimeOptions()
	{
		if (s_runtime_initialized)
			return;
		s_runtime_initialized = true;

		s_flush_enabled = envFlagEnabled("DREAM_GE2D_FLUSH", true);
		/* Public beta 2: enable the validated DreamOS GE2D submit path by default. */
		s_surface_accel_enabled = envFlagEnabled("DREAM_GE2D_SURFACE_ACCEL", true);
		s_fill_accel_enabled = envFlagEnabled("DREAM_GE2D_ACCEL_FILL", s_surface_accel_enabled);
		s_blit_accel_enabled = envFlagEnabled("DREAM_GE2D_ACCEL_BLIT", s_surface_accel_enabled);
		s_blend_accel_enabled = envFlagEnabled("DREAM_GE2D_ACCEL_BLEND", s_surface_accel_enabled);
		s_blend_scale_enabled = envFlagEnabled("DREAM_GE2D_BLEND_SCALE", envFlagEnabled("DREAM_GE2D_FB_BLEND_SCALE", true));
		/* Raw physical surfaces stay disabled. Framebuffer pages are handled through the registered FB resolver only. */
		s_raw_phys_accel_enabled = envFlagEnabled("DREAM_GE2D_RAWPHYS_ACCEL", false);
		const bool fb_requested = envFlagEnabled("DREAM_GE2D_FB_ACCEL", true);
		s_fb_write_enabled = true;
		s_fb_accel_enabled = fb_requested;
		s_fb_fill_enabled = s_fb_accel_enabled && envFlagEnabled("DREAM_GE2D_FB_FILL", true);
		s_fb_blit_enabled = s_fb_accel_enabled && envFlagEnabled("DREAM_GE2D_FB_BLIT", true);
		s_fb_blend_enabled = s_fb_accel_enabled && envFlagEnabled("DREAM_GE2D_FB_BLEND", true);
		s_fb_msync_enabled = envFlagEnabled("DREAM_GE2D_FB_MSYNC", false);
		s_fb_pagecopy_enabled = envFlagEnabled("DREAM_GE2D_FB_PAGECOPY", true);
		s_fb_submit_dreamos_enabled = envFlagEnabled("DREAM_GE2D_FB_SUBMIT_DREAMOS", true);
		s_fb_submit_dreamos_fill_enabled = envFlagEnabled("DREAM_GE2D_FB_FILL_SUBMIT_DREAMOS", s_fb_submit_dreamos_enabled);
		s_fb_submit_dreamos_blit_enabled = envFlagEnabled("DREAM_GE2D_FB_BLIT_SUBMIT_DREAMOS", s_fb_submit_dreamos_enabled);
		s_fb_submit_dreamos_blend_enabled = envFlagEnabled("DREAM_GE2D_FB_BLEND_SUBMIT_DREAMOS", s_fb_submit_dreamos_enabled);
		s_fb_fill_dreamos_format = DREAM_GE2D_FORMAT_S32_DREAMOS_FILL;
		s_stats_enabled = envFlagEnabled("DREAM_GE2D_STATS", false) || envFlagEnabled("DREAM_GPIXMAP_STATS", false);
		s_trace_enabled = envFlagEnabled("DREAM_GE2D_TRACE", false) || envFlagEnabled("DREAM_GE2D_SURFACE_TRACE", false);
		s_trace_limit = envIntValue("DREAM_GE2D_TRACE_LIMIT", s_trace_limit);
		s_ion_heap_mask = envUIntValue("DREAM_GE2D_ION_HEAP", DREAM_ION_DEFAULT_HEAP_MASK);
		s_ion_flags = envUIntValue("DREAM_GE2D_ION_FLAGS", DREAM_ION_DEFAULT_FLAGS);
		s_ion_align = envUIntValue("DREAM_GE2D_ION_ALIGN", DREAM_ION_DEFAULT_ALIGN);
		s_keep_ion_handle = envFlagEnabled("DREAM_GE2D_KEEP_ION_HANDLE", false) ? 1 : 0;
		s_min_surface_size = envIntValue("DREAM_GE2D_MIN_SURFACE", s_min_surface_size);
		s_min_operation_size = envIntValue("DREAM_GE2D_MIN_OP", s_min_operation_size);
		s_stats_interval = envIntValue("DREAM_GE2D_STATS_INTERVAL", envIntValue("DREAM_GPIXMAP_STATS_INTERVAL_MS", s_stats_interval));
		if (s_fb_submit_dreamos_enabled)
			eDebug("[dreamGE2D] DreamOS submit v26 active: fill=%d blit=%d blend=%d fill_format=0x%x op=0x%x",
				s_fb_submit_dreamos_fill_enabled ? 1 : 0, s_fb_submit_dreamos_blit_enabled ? 1 : 0,
				s_fb_submit_dreamos_blend_enabled ? 1 : 0, s_fb_fill_dreamos_format, DREAM_GE2D_FILL_SUBMIT_OP_DREAMOS);
		if (s_stats_enabled)
			statsLog("init", true);
		if (s_trace_enabled)
			eTrace("[dreamGE2D] surface trace enabled limit=%d", s_trace_limit);
	}

	int rectBytes(const gUnmanagedSurface *surface, const eRect &area)
	{
		if (!surface || area.empty())
			return 0;
		return area.width() * area.height() * surface->bypp;
	}

	void setupOSDPara(struct dream_src_dst_para_ex_s *para, int width, int virtual_height)
	{
		memset(para, 0, sizeof(*para));
		para->canvas_index = 0;
		para->top = 0;
		para->left = 0;
		para->width = width > 0 ? width : 1;
		para->height = virtual_height > 0 ? virtual_height : 1;
		para->format = 0;
		para->mem_type = DREAM_CANVAS_OSD0;
		para->color = 0;
	}

	void configClear(struct dream_config_para_ex_s *cfg)
	{
		memset(cfg, 0, sizeof(*cfg));
		cfg->src_para.mem_type = DREAM_CANVAS_TYPE_INVALID;
		cfg->src2_para.mem_type = DREAM_CANVAS_TYPE_INVALID;
		cfg->dst_para.mem_type = DREAM_CANVAS_TYPE_INVALID;
		cfg->alu_const_color = 0xff;
	}

	void setupTargetParaFormat(struct dream_src_dst_para_ex_s *para, const DreamGE2DTarget &target, unsigned int format)
	{
		memset(para, 0, sizeof(*para));
		para->canvas_index = 0;
		para->top = 0;
		para->left = 0;
		para->width = target.width;
		para->height = target.height;
		para->format = (int)format;
		para->mem_type = DREAM_CANVAS_ALLOC;
		para->color = 0;
	}

	unsigned int dreamOSFormatForTarget(const DreamGE2DTarget &target, bool role_is_primary_src)
	{
		/*
		 * v25 fixed DreamOS-style OSD Fill/Blit/Blend, but real PNG/logo content still
		 * showed a red/blue swap (for example ARD blue rendered brown).
		 *
		 * On DreamTwo this points to the source pixmap color-map selection rather than the
		 * Fill submit color packing. Keep framebuffer/destination on 0x01200300 and also use
		 * the same DreamOS color-map for primary source pixmaps so GE2D interprets uploaded
		 * image bytes as expected. White text/alpha-only overlays are unaffected, while colored
		 * PNG/logo surfaces should regain the correct blue/red balance.
		 */
		(void)role_is_primary_src;
		if (target.framebuffer)
			return DREAM_GE2D_FORMAT_S32_DREAMOS_FILL;
		return DREAM_GE2D_FORMAT_S32_DREAMOS_FILL;
	}

	void setupTargetPara(struct dream_src_dst_para_ex_s *para, const DreamGE2DTarget &target)
	{
		setupTargetParaFormat(para, target, DREAM_GE2D_FORMAT_S32_ARGB);
	}

	void setupTargetParaDreamOS(struct dream_src_dst_para_ex_s *para, const DreamGE2DTarget &target, bool role_is_primary_src)
	{
		setupTargetParaFormat(para, target, dreamOSFormatForTarget(target, role_is_primary_src));
	}

	unsigned int dreamOSSubmitColor(unsigned int color)
	{
		/*
		 * v23 fixed alpha placement, but on real DreamTwo the fill tint still came out
		 * brown/orange instead of blue. This means alpha is now correct, while red and blue
		 * are still swapped for the FillContext path.
		 *
		 * Convert Enigma2 gRGB 0xAARRGGBB into BBGGRRAA for the DreamOS fill submit path.
		 * Example: 0xdf0d1940 -> 0x40190ddf.
		 */
		const unsigned int a = (color >> 24) & 0xffU;
		const unsigned int r = (color >> 16) & 0xffU;
		const unsigned int g = (color >> 8) & 0xffU;
		const unsigned int b = color & 0xffU;
		return (b << 24) | (g << 16) | (r << 8) | a;
	}

	void setupTargetPlane(struct dream_config_planes_s *plane, const DreamGE2DTarget &target)
	{
		memset(plane, 0, sizeof(*plane));
		plane->addr = target.phys;
		plane->w = target.stride / 4;
		plane->h = target.height;
	}

	int getGE2DFd()
	{
		if (s_ge2d_disabled)
			return -1;
		if (s_ge2d_fd >= 0)
			return s_ge2d_fd;

		s_ge2d_fd = open("/dev/ge2d", O_RDWR | O_CLOEXEC);
		if (s_ge2d_fd < 0)
		{
			eDebug("[dreamGE2D] failed to open /dev/ge2d: %m");
			s_ge2d_disabled = true;
			return -1;
		}

		int cap = 0;
		if (ioctl(s_ge2d_fd, DREAM_GE2D_GET_CAP, &cap) == 0)
			eDebug("[dreamGE2D] /dev/ge2d opened, cap=0x%x", cap);
		else
			eDebug("[dreamGE2D] GE2D_GET_CAP failed: %m");

		return s_ge2d_fd;
	}

	int getIONFd()
	{
		if (s_ion_disabled)
			return -1;
		if (s_ion_fd >= 0)
			return s_ion_fd;

		s_ion_fd = open("/dev/ion", O_RDWR | O_CLOEXEC);
		if (s_ion_fd < 0)
		{
			eDebug("[dreamGE2D] failed to open /dev/ion: %m");
			s_ion_disabled = true;
			return -1;
		}

		eDebug("[dreamGE2D] /dev/ion opened, heap=0x%x flags=0x%x align=0x%x", s_ion_heap_mask, s_ion_flags, s_ion_align);
		return s_ion_fd;
	}

	bool ionSyncFD(int fd, unsigned long cmd)
	{
		int ion_fd = getIONFd();
		if (ion_fd < 0 || fd < 0)
			return false;

		struct dream_ion_fd_data data;
		memset(&data, 0, sizeof(data));
		data.fd = fd;
		return ioctl(ion_fd, cmd, &data) == 0;
	}

	bool ge2dSyncFD(int fd, unsigned long cmd)
	{
		int ge2d_fd = getGE2DFd();
		if (ge2d_fd < 0 || fd < 0)
			return false;
		int sync_fd = fd;
		return ioctl(ge2d_fd, cmd, &sync_fd) == 0;
	}

	std::map<const gUnmanagedSurface *, DreamGE2DBuffer>::iterator findBuffer(const gUnmanagedSurface *surface)
	{
		return s_buffers.find(surface);
	}

	const DreamGE2DBuffer *findBufferByData(const void *data, unsigned long *offset)
	{
		if (offset)
			*offset = 0;
		if (!data)
			return 0;
		const unsigned char *ptr = static_cast<const unsigned char *>(data);
		for (std::map<const gUnmanagedSurface *, DreamGE2DBuffer>::const_iterator it = s_buffers.begin(); it != s_buffers.end(); ++it)
		{
			const DreamGE2DBuffer &buffer = it->second;
			if (!buffer.data || buffer.size <= 0)
				continue;
			const unsigned char *base = static_cast<const unsigned char *>(buffer.data);
			if (ptr >= base && ptr < base + buffer.size)
			{
				if (offset)
					*offset = (unsigned long)(ptr - base);
				return &buffer;
			}
		}
		return 0;
	}

	const DreamGE2DBuffer *findBufferByPhys(unsigned long phys, unsigned long *offset)
	{
		if (offset)
			*offset = 0;
		if (!phys)
			return 0;
		for (std::map<const gUnmanagedSurface *, DreamGE2DBuffer>::const_iterator it = s_buffers.begin(); it != s_buffers.end(); ++it)
		{
			const DreamGE2DBuffer &buffer = it->second;
			if (!buffer.phys || buffer.size <= 0)
				continue;
			if (phys >= buffer.phys && phys < buffer.phys + (unsigned long)buffer.size)
			{
				if (offset)
					*offset = phys - buffer.phys;
				return &buffer;
			}
		}
		return 0;
	}

	bool getFramebufferDataOffset(const void *data, unsigned long *offset, int *page)
	{
		if (offset)
			*offset = 0;
		if (page)
			*page = -1;
		if (!s_fb.valid || !s_fb.base_data || !data)
			return false;
		const unsigned char *base = static_cast<const unsigned char *>(s_fb.base_data);
		const unsigned char *ptr = static_cast<const unsigned char *>(data);
		if (ptr < base || ptr >= base + s_fb.bytes)
			return false;
		const unsigned long off = (unsigned long)(ptr - base);
		if (offset)
			*offset = off;
		if (page)
		{
			const unsigned long page_size = (unsigned long)s_fb.stride * (unsigned long)s_fb.height;
			*page = page_size ? (int)(off / page_size) : -1;
		}
		return true;
	}

	bool getFramebufferPhysOffset(unsigned long phys, unsigned long *offset, int *page)
	{
		if (offset)
			*offset = 0;
		if (page)
			*page = -1;
		if (!s_fb.valid || !s_fb.base_phys || !phys)
			return false;
		if (phys < s_fb.base_phys || phys >= s_fb.base_phys + s_fb.bytes)
			return false;
		const unsigned long off = phys - s_fb.base_phys;
		if (offset)
			*offset = off;
		if (page)
		{
			const unsigned long page_size = (unsigned long)s_fb.stride * (unsigned long)s_fb.height;
			*page = page_size ? (int)(off / page_size) : -1;
		}
		return true;
	}

	bool isFramebufferSurface(const gUnmanagedSurface *surface);

	void traceSurface(const char *op, const char *role, const char *reason, const gUnmanagedSurface *surface, const eRect *rect)
	{
		if (!s_trace_enabled || s_trace_count >= s_trace_limit)
			return;
		++s_trace_count;

		if (!surface)
		{
			eTrace("[dreamGE2D] trace %d %s/%s reason=%s surface=NULL", s_trace_count, op ? op : "?", role ? role : "?", reason ? reason : "?");
			return;
		}

		unsigned long ion_data_offset = 0;
		unsigned long ion_phys_offset = 0;
		unsigned long fb_data_offset = 0;
		unsigned long fb_phys_offset = 0;
		int fb_data_page = -1;
		int fb_phys_page = -1;
		const unsigned long phys = (unsigned long)(uint32_t)surface->data_phys;
		std::map<const gUnmanagedSurface *, DreamGE2DBuffer>::iterator ptr_it = findBuffer(surface);
		const DreamGE2DBuffer *ion_data = findBufferByData(surface->data, &ion_data_offset);
		const DreamGE2DBuffer *ion_phys = findBufferByPhys(phys, &ion_phys_offset);
		const bool fb_data = getFramebufferDataOffset(surface->data, &fb_data_offset, &fb_data_page);
		const bool fb_phys = getFramebufferPhysOffset(phys, &fb_phys_offset, &fb_phys_page);
		const bool fb_strict = isFramebufferSurface(surface);
		const int rx = rect ? rect->x() : 0;
		const int ry = rect ? rect->y() : 0;
		const int rw = rect ? rect->width() : 0;
		const int rh = rect ? rect->height() : 0;

		eTrace("[dreamGE2D] trace %d %s/%s reason=%s surface=%p data=%p phys=0x%lx x=%d y=%d bpp=%d bypp=%d stride=%d rect=%d,%d %dx%d ptr=%d ion_data=%d/%lu ion_phys=%d/%lu fb_data=%d p=%d off=%lu fb_phys=%d p=%d off=%lu fb_strict=%d",
			s_trace_count, op ? op : "?", role ? role : "?", reason ? reason : "?", surface, surface->data, phys, surface->x, surface->y, surface->bpp, surface->bypp, surface->stride, rx, ry, rw, rh,
			ptr_it != s_buffers.end() ? 1 : 0, ion_data ? 1 : 0, ion_data_offset, ion_phys ? 1 : 0, ion_phys_offset,
			fb_data ? 1 : 0, fb_data_page, fb_data_offset, fb_phys ? 1 : 0, fb_phys_page, fb_phys_offset, fb_strict ? 1 : 0);

		if (ion_data || ion_phys)
		{
			const DreamGE2DBuffer *buffer = ion_data ? ion_data : ion_phys;
			eTrace("[dreamGE2D] trace %d ion-match owner=%p data=%p phys=0x%lx size=%d stride=%d fd=%d data_off=%lu phys_off=%lu",
				s_trace_count, buffer->surface, buffer->data, buffer->phys, buffer->size, buffer->stride, buffer->fd, ion_data_offset, ion_phys_offset);
		}
	}

	bool isFramebufferSurface(const gUnmanagedSurface *surface)
	{
		if (!surface || !s_fb.valid || !s_fb.base_data || !s_fb.base_phys || !surface->data || !surface->data_phys)
			return false;
		if (surface->bpp != 32 || surface->stride != s_fb.stride || surface->x != s_fb.width || surface->y != s_fb.height)
			return false;
		const unsigned char *base = static_cast<const unsigned char *>(s_fb.base_data);
		const unsigned char *ptr = static_cast<const unsigned char *>(surface->data);
		const unsigned long phys = (unsigned long)(uint32_t)surface->data_phys;
		if (ptr < base || ptr >= base + s_fb.bytes)
			return false;
		if (phys < s_fb.base_phys || phys >= s_fb.base_phys + s_fb.bytes)
			return false;
		const size_t data_offset = (size_t)(ptr - base);
		const unsigned long phys_offset = phys - s_fb.base_phys;
		if (data_offset != phys_offset)
			return false;
		if ((data_offset % (size_t)(s_fb.stride * s_fb.height)) != 0)
			return false;
		return true;
	}

	bool getFramebufferTargetStrict(const gUnmanagedSurface *surface, DreamGE2DTarget &target)
	{
		memset(&target, 0, sizeof(target));
		target.fd = -1;
		target.managed = false;
		target.framebuffer = false;
		target.data = 0;
		if (!isFramebufferSurface(surface))
			return false;
		target.width = surface->x;
		target.height = surface->y;
		target.stride = surface->stride;
		target.phys = (unsigned long)(uint32_t)surface->data_phys;
		target.fd = -1;
		target.managed = false;
		target.framebuffer = true;
		target.data = surface->data;
		return target.phys != 0;
	}

	void msyncFramebufferTarget(const DreamGE2DTarget &target, int flags)
	{
		if (!target.framebuffer || !target.data || !s_fb_msync_enabled)
			return;
		const size_t bytes = (size_t)target.stride * (size_t)target.height;
		if (bytes > 0)
			msync(target.data, bytes, flags);
	}

	bool getSurfaceTarget(const gUnmanagedSurface *surface, DreamGE2DTarget &target)
	{
		memset(&target, 0, sizeof(target));
		target.fd = -1;
		target.managed = false;
		target.framebuffer = false;
		target.data = 0;

		if (!surface || surface->bpp != 32 || surface->x <= 0 || surface->y <= 0 || surface->stride <= 0)
			return false;

		std::map<const gUnmanagedSurface *, DreamGE2DBuffer>::iterator it = findBuffer(surface);
		if (it != s_buffers.end())
		{
			const DreamGE2DBuffer &buffer = it->second;
			if (!buffer.phys || buffer.stride <= 0 || buffer.width <= 0 || buffer.height <= 0)
				return false;
			target.width = buffer.width;
			target.height = buffer.height;
			target.stride = buffer.stride;
			target.phys = buffer.phys;
			target.fd = buffer.fd;
			target.managed = true;
			target.framebuffer = false;
			target.data = buffer.data;
			return true;
		}

		if (!surface->data_phys)
			return false;

		if (isFramebufferSurface(surface))
		{
			if (!s_fb_accel_enabled)
			{
				if (!s_fb_warning_logged)
				{
					eTrace("[dreamGE2D] framebuffer surface acceleration disabled");
					s_fb_warning_logged = true;
				}
				return false;
			}
			target.width = surface->x;
			target.height = surface->y;
			target.stride = surface->stride;
			target.phys = (unsigned long)(uint32_t)surface->data_phys;
			target.fd = -1;
			target.managed = false;
			target.framebuffer = true;
			target.data = surface->data;
			return target.phys != 0;
		}

		if (!s_raw_phys_accel_enabled)
		{
			if (!s_raw_phys_warning_logged)
			{
				eTrace("[dreamGE2D] raw physical surface acceleration disabled");
				s_raw_phys_warning_logged = true;
			}
			return false;
		}

		target.width = surface->x;
		target.height = surface->y;
		target.stride = surface->stride;
		target.phys = (unsigned long)(uint32_t)surface->data_phys;
		target.fd = -1;
		target.managed = false;
		target.framebuffer = false;
		target.data = surface->data;
		return target.phys != 0;
	}

	void syncTargetDevice(const DreamGE2DTarget &target)
	{
		if (target.fd >= 0)
		{
			ionSyncFD(target.fd, DREAM_ION_IOC_SYNC);
			ge2dSyncFD(target.fd, DREAM_GE2D_SYNC_DEVICE);
		}
		else if (target.framebuffer)
		{
			msyncFramebufferTarget(target, MS_SYNC);
		}
	}

	void syncTargetCPU(const DreamGE2DTarget &target)
	{
		if (target.fd >= 0)
		{
			ge2dSyncFD(target.fd, DREAM_GE2D_SYNC_CPU);
			ionSyncFD(target.fd, DREAM_ION_IOC_INVALID_CACHE);
		}
		else if (target.framebuffer)
		{
			msyncFramebufferTarget(target, MS_INVALIDATE);
		}
	}

	void freeBuffer(std::map<const gUnmanagedSurface *, DreamGE2DBuffer>::iterator it, bool preserve_cpu_data)
	{
		if (it == s_buffers.end())
			return;

		DreamGE2DBuffer buffer = it->second;
		s_buffers.erase(it);

		if (buffer.surface)
		{
			if (preserve_cpu_data && buffer.surface->data && buffer.size > 0)
			{
				unsigned char *new_data = new (std::nothrow) unsigned char[buffer.size];
				if (new_data)
				{
					memcpy(new_data, buffer.surface->data, buffer.size);
					buffer.surface->data = new_data;
					buffer.surface->data_phys = 0;
				}
				else
				{
					buffer.surface->data = 0;
					buffer.surface->data_phys = 0;
				}
			}
			else
			{
				buffer.surface->data = 0;
				buffer.surface->data_phys = 0;
			}
		}

		if (buffer.data && buffer.data != MAP_FAILED)
			munmap(buffer.data, buffer.size);
		if (buffer.fd >= 0)
			close(buffer.fd);
		if (buffer.handle)
		{
			int ion_fd = getIONFd();
			if (ion_fd >= 0)
			{
				struct dream_ion_handle_data h;
				memset(&h, 0, sizeof(h));
				h.handle = buffer.handle;
				ioctl(ion_fd, DREAM_ION_IOC_FREE, &h);
			}
		}
	}

	bool configureOSDToOSD(int fd, int width, int virtual_height)
	{
		struct dream_config_ge2d_para_ex_s wrap;
		memset(&wrap, 0, sizeof(wrap));

		struct dream_config_para_ex_memtype_s *mem = &wrap.para_config_memtype;
		struct dream_config_para_ex_ion_s *cfg = &mem->_ge2d_config_ex;

		mem->ge2d_magic = sizeof(struct dream_config_para_ex_memtype_s);
		setupOSDPara(&cfg->src_para, width, virtual_height);
		cfg->src2_para.mem_type = DREAM_CANVAS_TYPE_INVALID;
		setupOSDPara(&cfg->dst_para, width, virtual_height);
		mem->src1_mem_alloc_type = DREAM_AML_GE2D_MEM_INVALID;
		mem->src2_mem_alloc_type = DREAM_AML_GE2D_MEM_INVALID;
		mem->dst_mem_alloc_type = DREAM_AML_GE2D_MEM_INVALID;

		if (ioctl(fd, DREAM_GE2D_CONFIG_EX_MEM, &wrap) < 0)
		{
			if (!s_ge2d_logged_copy_failure)
			{
				eDebug("[dreamGE2D] GE2D_CONFIG_EX_MEM osd-to-osd failed: %m");
				s_ge2d_logged_copy_failure = true;
			}
			return false;
		}
		return true;
	}

	void setSubmitRect(struct dream_ge2d_rectangle_s *rect, int x, int y, int w, int h)
	{
		rect->x = x;
		rect->y = y;
		rect->w = w;
		rect->h = h;
	}

	void setSubmitRectFromERect(struct dream_ge2d_rectangle_s *rect, const eRect &area)
	{
		setSubmitRect(rect, area.left(), area.top(), area.width(), area.height());
	}

	void setupDreamOSFillSubmit(struct dream_ge2d_para_s *para, const eRect &area, unsigned int color)
	{
		memset(para, 0, sizeof(*para));
		para->color = dreamOSSubmitColor(color);
		/* Dump v4/v5 layout: color at 0x00, rect1 at 0x04, rect2 at 0x14, rect3/dst at 0x24, mode/op at 0x34. */
		setSubmitRectFromERect(&para->src1_rect, area);
		setSubmitRectFromERect(&para->src2_rect, area);
		setSubmitRectFromERect(&para->dst_rect, area);
		para->op = DREAM_GE2D_FILL_SUBMIT_OP_DREAMOS;
	}

	void setupDreamOSBlitSubmit(struct dream_ge2d_para_s *para, const eRect &dst_rect, const eRect &src_rect)
	{
		memset(para, 0, sizeof(*para));
		setSubmitRectFromERect(&para->src1_rect, src_rect);
		/*
		 * Dump-v4 BLIT submits also carry the DreamOS mode field 0x00100010 at offset 0x34.
		 * Keep the three-rect submit shape aligned with DreamOS.
		 */
		setSubmitRectFromERect(&para->src2_rect, dst_rect);
		setSubmitRectFromERect(&para->dst_rect, dst_rect);
		para->op = DREAM_GE2D_FILL_SUBMIT_OP_DREAMOS;
	}

	void setupDreamOSBlendSubmit(struct dream_ge2d_para_s *para, const eRect &dst_rect, const eRect &src_rect, unsigned int op)
	{
		memset(para, 0, sizeof(*para));
		setSubmitRectFromERect(&para->src1_rect, src_rect);
		setSubmitRectFromERect(&para->src2_rect, dst_rect);
		setSubmitRectFromERect(&para->dst_rect, dst_rect);
		para->op = (int)op;
	}

	bool configureFillTarget(int fd, const DreamGE2DTarget &dst, bool dreamos_submit, unsigned int color)
	{
		struct dream_config_para_ex_s cfg;
		configClear(&cfg);
		if (dreamos_submit)
		{
			/* DreamOS FillContext shape: source fill descriptor plus physical destination, then the real color/rect/mode in GE2D_FILLRECTANGLE. */
			const unsigned int submit_color = dreamOSSubmitColor(color);
			setupTargetParaFormat(&cfg.src_para, dst, s_fb_fill_dreamos_format);
			setupTargetParaFormat(&cfg.dst_para, dst, s_fb_fill_dreamos_format);
			cfg.src_para.color = (int)submit_color;
			cfg.dst_para.color = (int)submit_color;
			cfg.src_para.fill_color_en = 1;
			cfg.src_para.fill_mode = 0;
			cfg.src2_gb_alpha = 0xff;
			setupTargetPlane(&cfg.src_planes[0], dst);
			setupTargetPlane(&cfg.dst_planes[0], dst);
		}
		else
		{
			setupTargetPara(&cfg.dst_para, dst);
			setupTargetPlane(&cfg.dst_planes[0], dst);
		}
		return ioctl(fd, DREAM_GE2D_CONFIG_EX, &cfg) == 0;
	}

	bool configureBlitTarget(int fd, const DreamGE2DTarget &src, const DreamGE2DTarget &dst)
	{
		struct dream_config_para_ex_s cfg;
		configClear(&cfg);
		setupTargetParaDreamOS(&cfg.src_para, src, true);
		setupTargetParaDreamOS(&cfg.dst_para, dst, false);
		setupTargetPlane(&cfg.src_planes[0], src);
		setupTargetPlane(&cfg.dst_planes[0], dst);
		return ioctl(fd, DREAM_GE2D_CONFIG_EX, &cfg) == 0;
	}

	bool configureBlendTarget(int fd, const DreamGE2DTarget &src, const DreamGE2DTarget &src2, const DreamGE2DTarget &dst)
	{
		struct dream_config_para_ex_s cfg;
		configClear(&cfg);
		setupTargetParaDreamOS(&cfg.src_para, src, true);
		setupTargetParaDreamOS(&cfg.src2_para, src2, false);
		setupTargetParaDreamOS(&cfg.dst_para, dst, false);
		setupTargetPlane(&cfg.src_planes[0], src);
		setupTargetPlane(&cfg.src2_planes[0], src2);
		setupTargetPlane(&cfg.dst_planes[0], dst);
		return ioctl(fd, DREAM_GE2D_CONFIG_EX, &cfg) == 0;
	}

	bool ionGetPhys(int ion_fd, DreamGE2DBuffer &buffer)
	{
		struct dream_meson_phys_data phys;
		struct dream_ion_custom_data custom;
		memset(&phys, 0, sizeof(phys));
		memset(&custom, 0, sizeof(custom));
		phys.share_fd = buffer.fd;
		custom.cmd = DREAM_ION_IOC_MESON_PHYS_ADDR;
		custom.arg = (unsigned long)&phys;

		if (ioctl(ion_fd, DREAM_ION_IOC_CUSTOM, &custom) < 0)
			return false;

		buffer.phys = phys.phys_addr;
		buffer.phys_size = phys.size;
		return buffer.phys != 0;
	}
}


void dreamGE2DRegisterFramebuffer(void *base_data, unsigned long base_phys, int width, int height, int stride, int pages)
{
	initRuntimeOptions();
	if (!base_data || !base_phys || width <= 0 || height <= 0 || stride <= 0 || pages <= 0)
	{
		memset(&s_fb, 0, sizeof(s_fb));
		return;
	}
	s_fb.base_data = base_data;
	s_fb.base_phys = base_phys;
	s_fb.width = width;
	s_fb.height = height;
	s_fb.stride = stride;
	s_fb.pages = pages;
	s_fb.bytes = (size_t)stride * (size_t)height * (size_t)pages;
	s_fb.valid = true;
	if (!s_fb_logged_register)
	{
		eTrace("[dreamGE2D] framebuffer registered base=%p phys=0x%lx size=%dx%d stride=%d pages=%d bytes=%u", base_data, base_phys, width, height, stride, pages, (unsigned int)s_fb.bytes);
		s_fb_logged_register = true;
	}
}

bool dreamGE2DCopyOSD(int src_y, int dst_y, int width, int height, int virtual_height)
{
	initRuntimeOptions();
	if (!s_flush_enabled)
	{
		if (!s_logged_flush_disabled)
		{
			eDebug("[dreamGE2D] flush/page-copy acceleration disabled; set DREAM_GE2D_FLUSH=1 to enable it");
			s_logged_flush_disabled = true;
		}
		return false;
	}

	if (src_y < 0 || dst_y < 0 || width <= 0 || height <= 0 || virtual_height <= 0)
		return false;
	if (src_y + height > virtual_height || dst_y + height > virtual_height)
		return false;

	int fd = getGE2DFd();
	if (fd < 0)
		return false;

	if (!configureOSDToOSD(fd, width, virtual_height))
		return false;

	struct dream_ge2d_para_s para;
	memset(&para, 0, sizeof(para));
	para.src1_rect.x = 0;
	para.src1_rect.y = src_y;
	para.src1_rect.w = width;
	para.src1_rect.h = height;
	para.dst_rect.x = 0;
	para.dst_rect.y = dst_y;
	para.dst_rect.w = width;
	para.dst_rect.h = height;

	if (ioctl(fd, DREAM_GE2D_BLIT, &para) < 0)
	{
		if (!s_ge2d_logged_copy_failure)
		{
			eDebug("[dreamGE2D] GE2D_BLIT osd-to-osd failed: %m");
			s_ge2d_logged_copy_failure = true;
		}
		return false;
	}

	return true;
}

bool dreamGE2DCopySurface(gUnmanagedSurface *dst, const gUnmanagedSurface *src, int width, int height)
{
	initRuntimeOptions();
	if (!s_fb_pagecopy_enabled)
	{
		if (!s_fb_pagecopy_warning_logged)
		{
			eTrace("[dreamGE2D] framebuffer page-copy acceleration disabled");
			s_fb_pagecopy_warning_logged = true;
		}
		++s_stats.pagecopy_fallback;
		statsEvent("pagecopy-disabled");
		return false;
	}
	if (!dst || !src || width <= 0 || height <= 0)
	{
		++s_stats.pagecopy_fallback;
		statsEvent("pagecopy-invalid");
		return false;
	}
	if (dst == src || dst->data == src->data || dst->data_phys == src->data_phys)
	{
		++s_stats.pagecopy_fallback;
		statsEvent("pagecopy-same-surface");
		return false;
	}
	if (dst->bpp != 32 || src->bpp != 32 || dst->stride != src->stride || dst->x != src->x || dst->y != src->y)
	{
		traceSurface("pagecopy", "src", "format", src, 0);
		traceSurface("pagecopy", "dst", "format", dst, 0);
		++s_stats.pagecopy_fallback;
		statsEvent("pagecopy-format");
		return false;
	}
	if (width > dst->x || height > dst->y || width > src->x || height > src->y)
	{
		++s_stats.pagecopy_fallback;
		statsEvent("pagecopy-size");
		return false;
	}

	DreamGE2DTarget src_target;
	DreamGE2DTarget dst_target;
	if (!getFramebufferTargetStrict(src, src_target) || !getFramebufferTargetStrict(dst, dst_target))
	{
		traceSurface("pagecopy", "src", "not-fb", src, 0);
		traceSurface("pagecopy", "dst", "not-fb", dst, 0);
		++s_stats.pagecopy_fallback;
		statsEvent("pagecopy-not-fb");
		return false;
	}

	int fd = getGE2DFd();
	if (fd < 0)
	{
		++s_stats.pagecopy_fail;
		statsEvent("pagecopy-open-fail");
		return false;
	}

	if (s_fb_msync_enabled)
		msyncFramebufferTarget(src_target, MS_SYNC);

	if (!configureBlitTarget(fd, src_target, dst_target))
	{
		++s_stats.pagecopy_fail;
		statsEvent("pagecopy-config-fail");
		return false;
	}

	struct dream_ge2d_para_s para;
	memset(&para, 0, sizeof(para));
	para.src1_rect.x = 0;
	para.src1_rect.y = 0;
	para.src1_rect.w = width;
	para.src1_rect.h = height;
	para.dst_rect.x = 0;
	para.dst_rect.y = 0;
	para.dst_rect.w = width;
	para.dst_rect.h = height;

	if (ioctl(fd, DREAM_GE2D_BLIT, &para) < 0)
	{
		++s_stats.pagecopy_fail;
		statsEvent("pagecopy-ioctl-fail");
		return false;
	}

	if (s_fb_msync_enabled)
		msyncFramebufferTarget(dst_target, MS_INVALIDATE);

	++s_stats.pagecopy_ok;
	++s_stats.blit_ok;
	++s_stats.blit_fb_ok;
	statsEvent("pagecopy-ok");
	if (!s_fb_pagecopy_logged)
	{
		eDebug("[dreamGE2D] framebuffer page-copy acceleration active via GE2D_CONFIG_EX phys path size=%dx%d stride=%d msync=%d", width, height, dst->stride, s_fb_msync_enabled ? 1 : 0);
		s_fb_pagecopy_logged = true;
	}
	return true;
}

bool dreamGE2DAllocSurface(gUnmanagedSurface *surface, int stride, int size)
{
	initRuntimeOptions();
	if (!surface || surface->bpp != 32 || surface->x <= 0 || surface->y <= 0 || stride <= 0 || size <= 0)
		return false;
	if (!s_surface_accel_enabled)
	{
		if (!s_ge2d_logged_accel_disabled)
		{
			eDebug("[dreamGE2D] ION surface acceleration disabled; set DREAM_GE2D_SURFACE_ACCEL=1 to enable it");
			s_ge2d_logged_accel_disabled = true;
		}
		++s_stats.alloc_fail;
		statsEvent("alloc-disabled");
		return false;
	}
	if (size < s_min_surface_size)
	{
		++s_stats.alloc_fail;
		statsEvent("alloc-threshold");
		return false;
	}
	if (findBuffer(surface) != s_buffers.end())
		return false;

	int ge2d_fd = getGE2DFd();
	int ion_fd = getIONFd();
	if (ge2d_fd < 0 || ion_fd < 0)
	{
		++s_stats.alloc_fail;
		statsEvent("alloc-open-fail");
		return false;
	}

	DreamGE2DBuffer buffer;
	memset(&buffer, 0, sizeof(buffer));
	buffer.surface = surface;
	buffer.handle = 0;
	buffer.fd = -1;
	buffer.width = surface->x;
	buffer.height = surface->y;
	buffer.stride = stride;
	buffer.size = size;
	buffer.phys = 0;
	buffer.phys_size = 0;
	buffer.data = 0;

	struct dream_ion_allocation_data alloc;
	memset(&alloc, 0, sizeof(alloc));
	alloc.len = (size_t)buffer.size;
	alloc.align = s_ion_align;
	alloc.heap_id_mask = s_ion_heap_mask;
	alloc.flags = s_ion_flags;

	if (ioctl(ion_fd, DREAM_ION_IOC_ALLOC, &alloc) < 0)
	{
		if (!s_ge2d_logged_alloc_failure)
		{
			eDebug("[dreamGE2D] ION_IOC_ALLOC failed: %m");
			s_ge2d_logged_alloc_failure = true;
		}
		++s_stats.alloc_fail;
		statsEvent("alloc-ioctl-fail");
		return false;
	}
	buffer.handle = alloc.handle;

	struct dream_ion_fd_data share;
	memset(&share, 0, sizeof(share));
	share.handle = buffer.handle;
	if (ioctl(ion_fd, DREAM_ION_IOC_SHARE, &share) < 0)
	{
		if (!s_ge2d_logged_alloc_failure)
		{
			eDebug("[dreamGE2D] ION_IOC_SHARE failed: %m");
			s_ge2d_logged_alloc_failure = true;
		}
		struct dream_ion_handle_data h;
		memset(&h, 0, sizeof(h));
		h.handle = buffer.handle;
		ioctl(ion_fd, DREAM_ION_IOC_FREE, &h);
		++s_stats.alloc_fail;
		statsEvent("share-fail");
		return false;
	}
	buffer.fd = share.fd;

	if (!ionGetPhys(ion_fd, buffer))
	{
		if (!s_ge2d_logged_alloc_failure)
		{
			eDebug("[dreamGE2D] ION_IOC_CUSTOM phys failed");
			s_ge2d_logged_alloc_failure = true;
		}
		close(buffer.fd);
		struct dream_ion_handle_data h;
		memset(&h, 0, sizeof(h));
		h.handle = buffer.handle;
		ioctl(ion_fd, DREAM_ION_IOC_FREE, &h);
		++s_stats.alloc_fail;
		statsEvent("phys-fail");
		return false;
	}

	if (!s_keep_ion_handle)
	{
		struct dream_ion_handle_data h;
		memset(&h, 0, sizeof(h));
		h.handle = buffer.handle;
		if (ioctl(ion_fd, DREAM_ION_IOC_FREE, &h) == 0)
			buffer.handle = 0;
	}

	buffer.data = mmap(0, buffer.size, PROT_READ | PROT_WRITE, MAP_SHARED, buffer.fd, 0);
	if (buffer.data == MAP_FAILED)
	{
		if (!s_ge2d_logged_alloc_failure)
		{
			eDebug("[dreamGE2D] mmap ION fd failed: %m");
			s_ge2d_logged_alloc_failure = true;
		}
		close(buffer.fd);
		if (buffer.handle)
		{
			struct dream_ion_handle_data h;
			memset(&h, 0, sizeof(h));
			h.handle = buffer.handle;
			ioctl(ion_fd, DREAM_ION_IOC_FREE, &h);
		}
		++s_stats.alloc_fail;
		statsEvent("mmap-fail");
		return false;
	}

	surface->stride = stride;
	surface->data = buffer.data;
	surface->data_phys = (int)buffer.phys;
	s_buffers[surface] = buffer;
	if (s_trace_enabled && s_trace_count < s_trace_limit)
	{
		++s_trace_count;
		eTrace("[dreamGE2D] trace %d alloc surface=%p data=%p phys=0x%lx size=%d stride=%d fd=%d",
			s_trace_count, surface, buffer.data, buffer.phys, buffer.size, buffer.stride, buffer.fd);
	}

	if (!s_ge2d_logged_accel_active)
	{
		eDebug("[dreamGE2D] acceleration active: ion=1 pagecopy=%d dreamos_submit=%d fbfill=%d fbblit=%d fbblend=%d blend_scale=%d msync=%d",
			s_fb_pagecopy_enabled ? 1 : 0, s_fb_submit_dreamos_enabled ? 1 : 0,
			s_fb_fill_enabled ? 1 : 0, s_fb_blit_enabled ? 1 : 0, s_fb_blend_enabled ? 1 : 0,
			s_blend_scale_enabled ? 1 : 0, s_fb_msync_enabled ? 1 : 0);
		s_ge2d_logged_accel_active = true;
	}

	++s_stats.alloc_ok;
	statsEvent("alloc-ok");
	return true;
}

bool dreamGE2DFreeSurface(gUnmanagedSurface *surface)
{
	std::map<const gUnmanagedSurface *, DreamGE2DBuffer>::iterator it = findBuffer(surface);
	if (it == s_buffers.end())
		return false;
	if (s_trace_enabled && s_trace_count < s_trace_limit)
	{
		const DreamGE2DBuffer &buffer = it->second;
		++s_trace_count;
		eTrace("[dreamGE2D] trace %d free surface=%p data=%p phys=0x%lx size=%d fd=%d",
			s_trace_count, surface, buffer.data, buffer.phys, buffer.size, buffer.fd);
	}
	freeBuffer(it, false);
	++s_stats.free_ok;
	statsEvent("free-ok");
	return true;
}

bool dreamGE2DIsManagedSurface(const gUnmanagedSurface *surface)
{
	return findBuffer(surface) != s_buffers.end();
}

void dreamGE2DReleaseAccelMemory()
{
	while (!s_buffers.empty())
		freeBuffer(s_buffers.begin(), true);
}

bool dreamGE2DFill(gUnmanagedSurface *dst, const eRect &area, unsigned long col)
{
	initRuntimeOptions();
	if (!s_fill_accel_enabled)
	{
		++s_stats.fill_fallback;
		statsEvent("fill-disabled");
		return false;
	}
	DreamGE2DTarget dst_target;
	if (!getSurfaceTarget(dst, dst_target))
	{
		traceSurface("fill", "dst", "no-target", dst, &area);
		++s_stats.fill_fallback;
		statsEvent("fill-no-phys");
		return false;
	}
	const bool fb_dreamos_submit = dst_target.framebuffer && s_fb_submit_dreamos_fill_enabled;
	if (dst_target.framebuffer && !s_fb_fill_enabled)
	{
		++s_stats.fill_fallback;
		statsEvent("fill-fb-disabled");
		return false;
	}
	if (area.empty() || area.left() < 0 || area.top() < 0 || area.right() > dst->x || area.bottom() > dst->y)
	{
		++s_stats.fill_fallback;
		statsEvent("fill-clip");
		return false;
	}
	const int fill_bytes = rectBytes(dst, area);
	if (fill_bytes < s_min_operation_size)
	{
		++s_stats.fill_fallback;
		statsEvent("fill-threshold");
		return false;
	}
	int fd = getGE2DFd();
	if (fd < 0)
	{
		++s_stats.fill_fail;
		statsEvent("fill-open-fail");
		return false;
	}

	if (!configureFillTarget(fd, dst_target, fb_dreamos_submit, (unsigned int)col))
	{
		++s_stats.fill_fail;
		statsEvent("fill-config-fail");
		return false;
	}

	struct dream_ge2d_para_s para;
	if (fb_dreamos_submit)
		setupDreamOSFillSubmit(&para, area, (unsigned int)col);
	else
	{
		memset(&para, 0, sizeof(para));
		para.color = (unsigned int)col;
		setSubmitRectFromERect(&para.dst_rect, area);
	}

	if (ioctl(fd, DREAM_GE2D_FILLRECTANGLE, &para) < 0)
	{
		++s_stats.fill_fail;
		statsEvent("fill-ioctl-fail");
		return false;
	}

	syncTargetCPU(dst_target);
	++s_stats.fill_ok;
	if (dst_target.managed)
		++s_stats.fill_ion_ok;
	else if (dst_target.framebuffer)
		++s_stats.fill_fb_ok;
	else
		++s_stats.fill_raw_ok;
	statsEvent("fill-ok");
	return true;
}

bool dreamGE2DBlit(gUnmanagedSurface *dst, gUnmanagedSurface *src, const eRect &p, const eRect &area, int flags)
{
	initRuntimeOptions();
	bool blend = (flags & DREAM_BLIT_ALPHA_BLEND) != 0;
	const bool scaled = (flags & DREAM_BLIT_SCALE) != 0;
	if (scaled && !(blend && s_blend_scale_enabled))
	{
		statsBlitFallback(blend, blend ? "blend-scale" : "blit-scale");
		return false;
	}
	if ((flags & DREAM_BLIT_ALPHA_TEST) && !blend)
	{
		++s_stats.blit_fallback;
		statsEvent("blit-alpha-test");
		return false;
	}
	if (blend && !s_blend_accel_enabled)
	{
		++s_stats.blend_fallback;
		statsEvent("blend-disabled");
		return false;
	}
	if (!blend && !s_blit_accel_enabled)
	{
		++s_stats.blit_fallback;
		statsEvent("blit-disabled");
		return false;
	}
	if (p.empty() || area.empty())
	{
		statsBlitFallback(blend, blend ? "blend-geometry" : "blit-geometry");
		return false;
	}
	if ((p.width() != area.width() || p.height() != area.height()) && !(blend && s_blend_scale_enabled))
	{
		statsBlitFallback(blend, blend ? "blend-geometry" : "blit-geometry");
		return false;
	}
	if (!dst || !src || dst->bpp != 32 || src->bpp != 32)
	{
		statsBlitFallback(blend, blend ? "blend-format" : "blit-format");
		return false;
	}
	if (area.left() < 0 || area.top() < 0 || area.right() > src->x || area.bottom() > src->y)
	{
		statsBlitFallback(blend, blend ? "blend-src-clip" : "blit-src-clip");
		return false;
	}
	if (p.left() < 0 || p.top() < 0 || p.right() > dst->x || p.bottom() > dst->y)
	{
		statsBlitFallback(blend, blend ? "blend-dst-clip" : "blit-dst-clip");
		return false;
	}
	if (rectBytes(dst, p) < s_min_operation_size)
	{
		statsBlitFallback(blend, blend ? "blend-threshold" : "blit-threshold");
		return false;
	}

	DreamGE2DTarget src_target;
	DreamGE2DTarget dst_target;
	const bool src_ok = getSurfaceTarget(src, src_target);
	const bool dst_ok = getSurfaceTarget(dst, dst_target);
	if (!src_ok || !dst_ok)
	{
		if (!src_ok)
			traceSurface(blend ? "blend" : "blit", "src", "no-target", src, &area);
		if (!dst_ok)
			traceSurface(blend ? "blend" : "blit", "dst", "no-target", dst, &p);
		statsBlitFallback(blend, blend ? "blend-no-phys" : "blit-no-phys");
		return false;
	}
	if ((src_target.framebuffer || dst_target.framebuffer) && blend && !s_fb_blend_enabled)
	{
		statsBlitFallback(true, "blend-fb-disabled");
		return false;
	}
	if ((src_target.framebuffer || dst_target.framebuffer) && !blend && !s_fb_blit_enabled)
	{
		statsBlitFallback(false, "blit-fb-disabled");
		return false;
	}

	int fd = getGE2DFd();
	if (fd < 0)
	{
		statsBlitFail(blend, blend ? "blend-open-fail" : "blit-open-fail");
		return false;
	}

	syncTargetDevice(src_target);
	syncTargetDevice(dst_target);

	struct dream_ge2d_para_s para;
	const bool fb_operation = src_target.framebuffer || dst_target.framebuffer;
	const bool dreamos_blit_submit = fb_operation && !blend && s_fb_submit_dreamos_blit_enabled;
	const bool dreamos_blend_submit = fb_operation && blend && s_fb_submit_dreamos_blend_enabled;
	if (blend && dreamos_blend_submit)
		setupDreamOSBlendSubmit(&para, p, area, DREAM_GE2D_BLEND_SRC_OVER);
	else if (!blend && dreamos_blit_submit)
		setupDreamOSBlitSubmit(&para, p, area);
	else
	{
		memset(&para, 0, sizeof(para));
		setSubmitRectFromERect(&para.src1_rect, area);
		setSubmitRectFromERect(&para.dst_rect, p);
	}

	if (blend)
	{
		if (!configureBlendTarget(fd, src_target, dst_target, dst_target))
		{
			++s_stats.blend_fail;
			statsEvent("blend-config-fail");
			return false;
		}
		if (!dreamos_blend_submit)
		{
			setSubmitRectFromERect(&para.src2_rect, p);
			para.op = DREAM_GE2D_BLEND_SRC_OVER;
		}
		if (ioctl(fd, DREAM_GE2D_BLEND, &para) < 0)
		{
			++s_stats.blend_fail;
			statsEvent("blend-ioctl-fail");
			return false;
		}
		++s_stats.blend_ok;
		if (src_target.managed && dst_target.managed)
			++s_stats.blend_ion_ok;
		else if (src_target.framebuffer || dst_target.framebuffer)
			++s_stats.blend_fb_ok;
		else
			++s_stats.blend_raw_ok;
		statsEvent("blend-ok");
	}
	else
	{
		if (!configureBlitTarget(fd, src_target, dst_target))
		{
			++s_stats.blit_fail;
			statsEvent("blit-config-fail");
			return false;
		}
		if (ioctl(fd, DREAM_GE2D_BLIT, &para) < 0)
		{
			++s_stats.blit_fail;
			statsEvent("blit-ioctl-fail");
			return false;
		}
		++s_stats.blit_ok;
		if (src_target.managed && dst_target.managed)
			++s_stats.blit_ion_ok;
		else if (src_target.framebuffer || dst_target.framebuffer)
			++s_stats.blit_fb_ok;
		else
			++s_stats.blit_raw_ok;
		statsEvent("blit-ok");
	}

	syncTargetCPU(dst_target);
	return true;
}

bool dreamGE2DHasAlphaBlendingSupport()
{
	initRuntimeOptions();
	return s_surface_accel_enabled && s_blend_accel_enabled;
}

void dreamGE2DReset()
{
	statsLog("reset", false);
	dreamGE2DReleaseAccelMemory();
	if (s_ge2d_fd >= 0)
	{
		close(s_ge2d_fd);
		s_ge2d_fd = -1;
	}
	if (s_ion_fd >= 0)
	{
		close(s_ion_fd);
		s_ion_fd = -1;
	}
	s_ge2d_disabled = false;
	s_ion_disabled = false;
	s_ge2d_logged_copy_failure = false;
	s_ge2d_logged_alloc_failure = false;
	s_ge2d_logged_accel_active = false;
	s_ge2d_logged_accel_disabled = false;
	s_logged_flush_disabled = false;
	s_fb_warning_logged = false;
	s_fb_pagecopy_logged = false;
	s_fb_pagecopy_warning_logged = false;
	s_fb_logged_register = false;
	s_trace_count = 0;
}

#else

void dreamGE2DRegisterFramebuffer(void *base_data, unsigned long base_phys, int width, int height, int stride, int pages)
{
	(void)base_data;
	(void)base_phys;
	(void)width;
	(void)height;
	(void)stride;
	(void)pages;
}

bool dreamGE2DCopyOSD(int src_y, int dst_y, int width, int height, int virtual_height)
{
	(void)src_y;
	(void)dst_y;
	(void)width;
	(void)height;
	(void)virtual_height;
	return false;
}

bool dreamGE2DCopySurface(gUnmanagedSurface *dst, const gUnmanagedSurface *src, int width, int height)
{
	(void)dst;
	(void)src;
	(void)width;
	(void)height;
	return false;
}

bool dreamGE2DAllocSurface(gUnmanagedSurface *surface, int stride, int size)
{
	(void)surface;
	(void)stride;
	(void)size;
	return false;
}

bool dreamGE2DFreeSurface(gUnmanagedSurface *surface)
{
	(void)surface;
	return false;
}

bool dreamGE2DIsManagedSurface(const gUnmanagedSurface *surface)
{
	(void)surface;
	return false;
}

void dreamGE2DReleaseAccelMemory()
{
}

bool dreamGE2DFill(gUnmanagedSurface *dst, const eRect &area, unsigned long col)
{
	(void)dst;
	(void)area;
	(void)col;
	return false;
}

bool dreamGE2DBlit(gUnmanagedSurface *dst, gUnmanagedSurface *src, const eRect &p, const eRect &area, int flags)
{
	(void)dst;
	(void)src;
	(void)p;
	(void)area;
	(void)flags;
	return false;
}

bool dreamGE2DHasAlphaBlendingSupport()
{
	return false;
}

void dreamGE2DReset()
{
}

#endif
