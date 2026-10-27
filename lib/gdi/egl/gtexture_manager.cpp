#include <lib/base/eerror.h>
#include <lib/gdi/egl/gles_version.h>
#include <lib/gdi/egl/gtexture_manager.h>
#include <lib/gdi/region.h>
#include <algorithm>
#include <cstdlib>
#include <cstring>
#include <mutex>

static gTextureManager* s_active_manager = nullptr;

// Guards s_active_manager: surfaces queue deletions from any thread while the manager may be torn down.
// Leaked on purpose so it outlives static destructors that free pixmaps.
static std::mutex& activeManagerMutex() {
	static std::mutex* m = new std::mutex();
	return *m;
}

gTextureManager::gTextureManager() : m_egl_display(EGL_NO_DISPLAY), m_content_texture_use_counter(0), m_content_texture_bytes(0), m_offscreen_advanced_shader_initialized(false),
	m_offscreen_texture_shader_initialized(false), m_context_generation(1) {
	std::lock_guard<std::mutex> guard(activeManagerMutex());
	s_active_manager = this;
}

gTextureManager::~gTextureManager() {
	std::lock_guard<std::mutex> guard(activeManagerMutex());
	if (s_active_manager == this)
		s_active_manager = nullptr;
}

void gTextureManager::recordUpload(int width, int height, int bytes, bool dmabuf, bool upload32_direct, bool upload32_converted, bool upload8_clut, bool upload8_luma) {
	m_upload_stats.textures++;
	if (dmabuf)
		m_upload_stats.dmabuf++;
	if (upload32_direct)
		m_upload_stats.upload32_direct++;
	if (upload32_converted)
		m_upload_stats.upload32_converted++;
	if (upload8_clut)
		m_upload_stats.upload8_clut++;
	if (upload8_luma)
		m_upload_stats.upload8_luma++;
	m_upload_stats.pixels += (unsigned long long)std::max(0, width) * (unsigned long long)std::max(0, height);
	m_upload_stats.bytes += (unsigned long long)std::max(0, bytes);
}

void gTextureManager::takeUploadStats(gTextureUploadStats& stats) {
	stats = m_upload_stats;
	m_upload_stats = gTextureUploadStats();
}

static void fnvMixByte(uint64_t& hash, uint8_t value)
{
	hash ^= value;
	hash *= 1099511628211ULL;
}

static void fnvMixU32(uint64_t& hash, uint32_t value)
{
	for (int i = 0; i < 4; ++i)
		fnvMixByte(hash, (uint8_t)(value >> (i * 8)));
}

static size_t contentTextureCacheMaxEntries()
{
	static int entries = -1;
	if (entries < 0) {
		const char* env = getenv("E2EGL_TEXTURE_CACHE_ENTRIES");
		entries = env && *env ? atoi(env) : 256;
		entries = std::max(32, std::min(entries, 1024));
	}
	return (size_t)entries;
}

static unsigned long long contentTextureCacheMaxBytes()
{
	static long long megabytes = -1;
	if (megabytes < 0) {
		const char* env = getenv("E2EGL_TEXTURE_CACHE_MB");
		megabytes = env && *env ? atoll(env) : 48;
		megabytes = std::max(4LL, std::min(megabytes, 256LL));
	}
	return (unsigned long long)megabytes * 1024ULL * 1024ULL;
}

#ifndef EGL_LINUX_DMA_BUF_EXT
#define EGL_LINUX_DMA_BUF_EXT 0x3270
#endif
#ifndef EGL_LINUX_DRM_FOURCC_EXT
#define EGL_LINUX_DRM_FOURCC_EXT 0x3271
#endif
#ifndef EGL_DMA_BUF_PLANE0_FD_EXT
#define EGL_DMA_BUF_PLANE0_FD_EXT 0x3272
#endif
#ifndef EGL_DMA_BUF_PLANE0_OFFSET_EXT
#define EGL_DMA_BUF_PLANE0_OFFSET_EXT 0x3273
#endif
#ifndef EGL_DMA_BUF_PLANE0_PITCH_EXT
#define EGL_DMA_BUF_PLANE0_PITCH_EXT 0x3274
#endif
// DRM FourCC formats
#define DRM_FORMAT_ARGB8888 0x34325241

typedef void (*gEGLImageTargetTexture2DOESProc)(GLenum target, void *image);

static bool hasExtension(const char* extensions, const char* name) {
	if (!extensions || !name || !*name)
		return false;

	const char* start = extensions;
	const size_t name_len = strlen(name);
	while ((start = strstr(start, name))) {
		const char before = start == extensions ? ' ' : *(start - 1);
		const char after = *(start + name_len);
		if ((before == ' ' || before == '\0') && (after == ' ' || after == '\0'))
			return true;
		start += name_len;
	}
	return false;
}

static float textureColorAlpha(const gRGB& color)
{
	return 1.0f - (color.a / 255.0f);
}

static bool regionCoversRect(const gRegion& region, const eRect& bounds)
{
	if (bounds.empty())
		return false;

	long long covered = 0;
	for (unsigned int i = 0; i < region.rects.size(); ++i) {
		eRect rect = region.rects[i] & bounds;
		if (!rect.empty())
			covered += (long long)rect.width() * rect.height();
	}
	return covered >= (long long)bounds.width() * bounds.height();
}

#include <lib/gdi/fb.h>
#ifdef DREAMNEXTGEN
#include <lib/gdi/dreamge2d.h>
#endif

static bool shouldUseDirectBGRAUpload()
{
#ifdef DREAMNEXTGEN
	return false;
#elif defined(HAVE_VUPLUS_EGL)
	return false;
#elif defined(HAVE_VUPLUS_MIPSEL_EGL)
	return false;
#elif defined(HAVE_NXPL_EGL)
	return false;
#elif defined(HAVE_V3DPLATFORM_EGL)
	return false;
#elif defined(HAVE_HISILICON_EGL)
	return false;
#elif defined(HAVE_DREAMBCM_EGL)
	return false;
#else
	return hasExtension((const char*)glGetString(GL_EXTENSIONS), "GL_EXT_texture_format_BGRA8888");
#endif
}

GLuint gTextureManager::createTextureFromDmabuf(gUnmanagedSurface* surface) {
	if (!surface || m_egl_display == EGL_NO_DISPLAY)
		return 0;

	if (surface->bpp != 32 || surface->data_phys == 0)
		return 0;

	const char* egl_extensions = eglQueryString(m_egl_display, EGL_EXTENSIONS);
	const char* gl_extensions = (const char*)glGetString(GL_EXTENSIONS);
	if (!hasExtension(egl_extensions, "EGL_EXT_image_dma_buf_import") || !hasExtension(gl_extensions, "GL_OES_EGL_image"))
		return 0;

	int width = surface->x;
	int height = surface->y;
	int stride = surface->stride;
	int dma_fd = -1;
	int offset = 0;

#ifdef DREAMNEXTGEN
	if (!dreamGE2DGetDmabuf(surface, &dma_fd, &width, &height, &stride, &offset))
#endif
	{
#ifdef CONFIG_ION
		fbClass* fb = fbClass::getInstance();
		if (!fb || fb->m_accel_fd < 0)
			return 0;
		dma_fd = fb->m_accel_fd;
		offset = surface->data_phys - fb->getAccelPhysAddr();
#else
		return 0;
#endif
	}

	EGLint attribs[] = {
		EGL_WIDTH, width,
		EGL_HEIGHT, height,
		EGL_LINUX_DRM_FOURCC_EXT, DRM_FORMAT_ARGB8888,
		EGL_DMA_BUF_PLANE0_FD_EXT, dma_fd,
		EGL_DMA_BUF_PLANE0_OFFSET_EXT, (EGLint)offset,
		EGL_DMA_BUF_PLANE0_PITCH_EXT, stride,
		EGL_NONE
	};

	PFNEGLCREATEIMAGEKHRPROC eglCreateImageKHR = (PFNEGLCREATEIMAGEKHRPROC)eglGetProcAddress("eglCreateImageKHR");
	gEGLImageTargetTexture2DOESProc glEGLImageTargetTexture2DOES = (gEGLImageTargetTexture2DOESProc)eglGetProcAddress("glEGLImageTargetTexture2DOES");

	if (!eglCreateImageKHR || !glEGLImageTargetTexture2DOES) {
		eDebug("[gTextureManager] EGL dmabuf extensions not available");
		return 0;
	}

	EGLImageKHR image = eglCreateImageKHR(m_egl_display, EGL_NO_CONTEXT, EGL_LINUX_DMA_BUF_EXT, (EGLClientBuffer)NULL, attribs);
	if (image == EGL_NO_IMAGE_KHR) {
		eDebug("[gTextureManager] eglCreateImageKHR failed: 0x%x", eglGetError());
		return 0;
	}

	GLuint texture_id;
	glGenTextures(1, &texture_id);
	glBindTexture(GL_TEXTURE_2D, texture_id);
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE);
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE);

	glEGLImageTargetTexture2DOES(GL_TEXTURE_2D, (void *)image);
	glBindTexture(GL_TEXTURE_2D, 0);

	m_texture_to_image_map[texture_id] = image;
	recordUpload(width, height, stride * height, true, false, false, false, false);
	return texture_id;
}

GLuint gTextureManager::createTextureFromSurface(gUnmanagedSurface* surface) {
	if (!surface)
		return 0;
	if (!surface->cpu_content_valid)
		return 0;

	GLuint texture_id = createTextureFromDmabuf(surface);
	if (texture_id != 0)
		return texture_id;

	int width = surface->x;
	int height = surface->y;

	glGenTextures(1, &texture_id);
	glBindTexture(GL_TEXTURE_2D, texture_id);

	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE);
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE);

	if (surface->bpp == 32) {
#ifndef GL_BGRA_EXT
#define GL_BGRA_EXT 0x80E1
#endif
		const uint8_t* src = (const uint8_t*)surface->data;
		const bool can_upload_bgra = shouldUseDirectBGRAUpload();
		std::vector<uint8_t> upload_buffer;
		const void* upload_data = surface->data;
		GLenum upload_format = GL_BGRA_EXT;
		bool converted_upload = false;

		auto convert_to_rgba = [&]() {
			upload_buffer.resize(width * height * 4);
			for (int y = 0; y < height; ++y) {
				const uint8_t* row = src + y * surface->stride;
				uint8_t* dst = upload_buffer.data() + y * width * 4;
				for (int x = 0; x < width; ++x) {
					dst[x * 4 + 0] = row[x * 4 + 2];
					dst[x * 4 + 1] = row[x * 4 + 1];
					dst[x * 4 + 2] = row[x * 4 + 0];
					dst[x * 4 + 3] = row[x * 4 + 3];
				}
			}
			upload_data = upload_buffer.data();
			upload_format = GL_RGBA;
			converted_upload = true;
		};

		if (can_upload_bgra) {
			if (surface->stride != width * 4) {
				upload_buffer.resize(width * height * 4);
				for (int y = 0; y < height; ++y)
					memcpy(upload_buffer.data() + y * width * 4, src + y * surface->stride, width * 4);
				upload_data = upload_buffer.data();
			}
		} else {
#ifdef DREAMNEXTGEN
			static int rgba_upload_log_count = 0;
			if (rgba_upload_log_count < 4) {
				++rgba_upload_log_count;
				eDebug("[gTextureManager] using RGBA texture upload for 32-bit pixmap %dx%d stride=%d", width, height, surface->stride);
			}
#endif
			convert_to_rgba();
		}

		glPixelStorei(GL_UNPACK_ALIGNMENT, 4);
		glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0, upload_format, GL_UNSIGNED_BYTE, upload_data);
		GLenum err = glGetError();
		if (err != GL_NO_ERROR && can_upload_bgra && !converted_upload) {
			static int bgra_retry_log_count = 0;
			if (bgra_retry_log_count < 8) {
				++bgra_retry_log_count;
				eDebug("[gTextureManager] BGRA texture upload failed: 0x%x, retrying RGBA for %dx%d stride=%d", err, width, height, surface->stride);
			}
			convert_to_rgba();
			glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0, GL_RGBA, GL_UNSIGNED_BYTE, upload_data);
			err = glGetError();
		}
		if (err == GL_OUT_OF_MEMORY && !m_content_texture_cache.empty()) {
			const size_t cached_entries = m_content_texture_cache.size();
			const unsigned long long cached_bytes = m_content_texture_bytes;
			clearContentTextureCache();
			processDeletions();
			eDebug("[gTextureManager] texture memory pressure: released %zu cached texture(s), %llu KiB; retrying %dx%d upload",
				cached_entries, cached_bytes / 1024ULL, width, height);
			glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0, upload_format, GL_UNSIGNED_BYTE, upload_data);
			err = glGetError();
		}
		if (err != GL_NO_ERROR) {
			eDebug("[gTextureManager] glTexImage2D 32-bit upload failed: 0x%x for %dx%d stride=%d", err, width, height, surface->stride);
			glBindTexture(GL_TEXTURE_2D, 0);
			glDeleteTextures(1, &texture_id);
			return 0;
		}
		recordUpload(width, height, width * height * 4, false, !converted_upload, converted_upload, false, false);
	} else if (surface->bpp == 8 && surface->clut.data) {
		std::vector<uint8_t> rgba_buffer(width * height * 4);
		uint8_t* src_pixels = (uint8_t*)surface->data;
		gRGB* palette = surface->clut.data;

		for (int y = 0; y < height; ++y) {
			const uint8_t* src_row = src_pixels + y * surface->stride;
			uint8_t* dst = rgba_buffer.data() + y * width * 4;
			for (int x = 0; x < width; ++x) {
				gRGB color = palette[src_row[x]];
				dst[x * 4 + 0] = color.r;
				dst[x * 4 + 1] = color.g;
				dst[x * 4 + 2] = color.b;
				dst[x * 4 + 3] = 255 - color.a;
			}
		}

		glPixelStorei(GL_UNPACK_ALIGNMENT, 1);
		glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0, GL_RGBA, GL_UNSIGNED_BYTE, rgba_buffer.data());
		if (glGetError() == GL_NO_ERROR)
			recordUpload(width, height, width * height * 4, false, false, false, true, false);
		glPixelStorei(GL_UNPACK_ALIGNMENT, 4);
	} else if (surface->bpp == 8) {
		const uint8_t* upload_data = (const uint8_t*)surface->data;
		std::vector<uint8_t> upload_buffer;
		if (surface->stride != width) {
			upload_buffer.resize(width * height);
			for (int y = 0; y < height; ++y)
				memcpy(upload_buffer.data() + y * width, upload_data + y * surface->stride, width);
			upload_data = upload_buffer.data();
		}

		glPixelStorei(GL_UNPACK_ALIGNMENT, 1);
		GLenum internal_fmt = GL_LUMINANCE;
		GLenum src_fmt = GL_LUMINANCE;
#ifdef HAVE_GLES3
		if (gles::isGLES3()) {
			internal_fmt = GL_R8;
			src_fmt = GL_RED;
		}
#endif
		glTexImage2D(GL_TEXTURE_2D, 0, internal_fmt, width, height, 0, src_fmt, GL_UNSIGNED_BYTE, upload_data);
		GLenum err = glGetError();
		if (err == GL_NO_ERROR)
			recordUpload(width, height, width * height, false, false, false, false, true);
		else
			eDebug("[gTextureManager] glTexImage2D 8-bit luminance upload failed: 0x%x", err);
		glPixelStorei(GL_UNPACK_ALIGNMENT, 4);
	} else {
		eDebug("[gTextureManager] unsupported surface format (bpp: %d)", surface->bpp);
		glDeleteTextures(1, &texture_id);
		return 0;
	}

	glBindTexture(GL_TEXTURE_2D, 0);
	return texture_id;
}

GLuint gTextureManager::getTexture(gPixmap* pixmap) {
	if (!pixmap || !pixmap->surface)
		return 0;

	return getSurfaceTexture(pixmap->surface);
}

GLuint gTextureManager::getSurfaceTexture(gUnmanagedSurface* surface) {
	if (!surface)
		return 0;
	prepareSurface(surface);

	if (surface->gl_texture_id != 0 && surface->gl_content_valid) {
		return surface->gl_texture_id;
	}
	if (surface->gl_texture_id != 0) {
		queueForDeletion(surface->gl_texture_id);
		surface->gl_texture_id = 0;
	}
	if (surface->gl_framebuffer_id != 0) {
		queueFramebufferForDeletion(surface->gl_framebuffer_id);
		surface->gl_framebuffer_id = 0;
	}

	const bool use_content_cache = canContentCacheSurface(surface);
	uint64_t content_key = 0;
	if (use_content_cache) {
		content_key = hashContentTextureSurface(surface);
		GLuint cached_texture = findContentTexture(content_key);
		if (cached_texture) {
			++m_upload_stats.content_cache_hits;
			return cached_texture;
		}
		++m_upload_stats.content_cache_misses;
	}

	GLuint new_texture = createTextureFromSurface(surface);
	if (new_texture && use_content_cache) {
		unsigned long long bytes = (unsigned long long)std::max(0, surface->x) * (unsigned long long)std::max(0, surface->y);
		if (surface->clut.data)
			bytes *= 4;
		return storeContentTexture(content_key, new_texture, bytes);
	}
	if (new_texture) {
		surface->gl_texture_id = new_texture;
		surface->gl_content_valid = true;
	}
	return new_texture;
}

bool gTextureManager::canContentCacheSurface(const gUnmanagedSurface* surface) const
{
	if (!surface || !surface->data || !surface->cpu_content_valid || surface->data_phys || surface->gl_framebuffer_id)
		return false;
	if (surface->bpp != 8 || surface->x <= 0 || surface->y <= 0 || surface->stride == 0)
		return false;

	const unsigned long long pixels = (unsigned long long)surface->x * (unsigned long long)surface->y;
	return pixels <= 262144ULL;
}

uint64_t gTextureManager::hashContentTextureSurface(const gUnmanagedSurface* surface) const
{
	uint64_t hash = 1469598103934665603ULL;
	fnvMixU32(hash, (uint32_t)surface->x);
	fnvMixU32(hash, (uint32_t)surface->y);
	fnvMixU32(hash, (uint32_t)surface->bpp);
	fnvMixU32(hash, surface->clut.data ? (uint32_t)surface->clut.start : 0);
	fnvMixU32(hash, surface->clut.data ? (uint32_t)surface->clut.colors : 0);
	fnvMixU32(hash, surface->transparent ? 1U : 0U);

	if (surface->clut.data) {
		for (int i = 0; i < surface->clut.colors; ++i)
			fnvMixU32(hash, surface->clut.data[i].argb());
	}

	const uint8_t* data = (const uint8_t*)surface->data;
	const int row_bytes = surface->x;
	const int stride = surface->stride;
	for (int y = 0; y < surface->y; ++y) {
		const uint8_t* row = stride > 0 ? data + y * stride : data + (surface->y - 1 - y) * -stride;
		for (int x = 0; x < row_bytes; ++x)
			fnvMixByte(hash, row[x]);
	}
	return hash;
}

GLuint gTextureManager::findContentTexture(uint64_t key)
{
	auto it = m_content_texture_cache.find(key);
	if (it == m_content_texture_cache.end())
		return 0;
	it->second.last_used = ++m_content_texture_use_counter;
	return it->second.texture_id;
}

GLuint gTextureManager::storeContentTexture(uint64_t key, GLuint texture_id, unsigned long long bytes)
{
	auto it = m_content_texture_cache.find(key);
	if (it != m_content_texture_cache.end()) {
		queueForDeletion(texture_id);
		it->second.last_used = ++m_content_texture_use_counter;
		return it->second.texture_id;
	}

	ContentTextureEntry entry;
	entry.texture_id = texture_id;
	entry.bytes = bytes;
	entry.last_used = ++m_content_texture_use_counter;
	m_content_texture_cache[key] = entry;
	m_content_texture_bytes += bytes;
	trimContentTextureCache();
	return texture_id;
}

void gTextureManager::trimContentTextureCache()
{
	const size_t max_entries = contentTextureCacheMaxEntries();
	const unsigned long long max_bytes = contentTextureCacheMaxBytes();
	while (m_content_texture_cache.size() > max_entries || m_content_texture_bytes > max_bytes) {
		auto oldest = m_content_texture_cache.end();
		for (auto it = m_content_texture_cache.begin(); it != m_content_texture_cache.end(); ++it) {
			if (oldest == m_content_texture_cache.end() || it->second.last_used < oldest->second.last_used)
				oldest = it;
		}
		if (oldest == m_content_texture_cache.end())
			break;
		queueForDeletion(oldest->second.texture_id);
		m_content_texture_bytes -= std::min(m_content_texture_bytes, oldest->second.bytes);
		m_content_texture_cache.erase(oldest);
	}
}

void gTextureManager::clearContentTextureCache()
{
	for (auto &entry : m_content_texture_cache)
		queueForDeletion(entry.second.texture_id);
	m_content_texture_cache.clear();
	m_content_texture_bytes = 0;
	m_content_texture_use_counter = 0;
}

bool gTextureManager::ensureOffscreenAdvancedShader()
{
	if (m_offscreen_advanced_shader_initialized && m_offscreen_advanced_shader.isInitialized())
		return true;
	if (eglGetCurrentContext() == EGL_NO_CONTEXT)
		return false;
	m_offscreen_advanced_shader.release();
	if (!m_offscreen_advanced_shader.init()) {
		eDebug("[gTextureManager] failed to initialise offscreen advanced shader");
		return false;
	}
	m_offscreen_advanced_shader_initialized = true;
	return true;
}

bool gTextureManager::ensureOffscreenTextureShader()
{
	if (m_offscreen_texture_shader_initialized && m_offscreen_texture_shader.isInitialized())
		return true;
	if (eglGetCurrentContext() == EGL_NO_CONTEXT)
		return false;
	m_offscreen_texture_shader.release();
	if (!m_offscreen_texture_shader.init()) {
		eDebug("[gTextureManager] failed to initialise offscreen texture shader");
		return false;
	}
	m_offscreen_texture_shader_initialized = true;
	return true;
}

void gTextureManager::releaseGLResources()
{
	clearContentTextureCache();
	processDeletions();
	m_offscreen_advanced_shader.release();
	m_offscreen_texture_shader.release();
	m_offscreen_advanced_shader_initialized = false;
	m_offscreen_texture_shader_initialized = false;
}

void gTextureManager::resetContextGeneration()
{
	std::lock_guard<std::mutex> lock(m_deletion_mutex);
	m_pending_deletions.clear();
	m_pending_framebuffer_deletions.clear();
	m_texture_to_image_map.clear();
	m_content_texture_cache.clear();
	m_content_texture_bytes = 0;
	m_content_texture_use_counter = 0;
	if (++m_context_generation == 0)
		m_context_generation = 1;
}

void gTextureManager::prepareSurface(gUnmanagedSurface* surface)
{
	if (!surface || surface->gl_context_generation == m_context_generation)
		return;
	surface->gl_texture_id = 0;
	surface->gl_framebuffer_id = 0;
	surface->gl_content_valid = false;
	surface->gl_context_generation = m_context_generation;
}

void gTextureManager::queueForDeletion(GLuint texture_id, unsigned int context_generation) {
	if (texture_id == 0)
		return;
	if (context_generation && context_generation != m_context_generation)
		return;

	std::lock_guard<std::mutex> lock(m_deletion_mutex);
	m_pending_deletions.push_back(texture_id);
}

void gTextureManager::queueFramebufferForDeletion(GLuint framebuffer_id, unsigned int context_generation) {
	if (framebuffer_id == 0)
		return;
	if (context_generation && context_generation != m_context_generation)
		return;

	std::lock_guard<std::mutex> lock(m_deletion_mutex);
	m_pending_framebuffer_deletions.push_back(framebuffer_id);
}

void gTextureManager::processDeletions() {
	std::lock_guard<std::mutex> lock(m_deletion_mutex);
	if (!m_pending_framebuffer_deletions.empty()) {
		glDeleteFramebuffers(m_pending_framebuffer_deletions.size(), m_pending_framebuffer_deletions.data());
		m_pending_framebuffer_deletions.clear();
	}
	if (!m_pending_deletions.empty()) {
		glDeleteTextures(m_pending_deletions.size(), m_pending_deletions.data());

		PFNEGLDESTROYIMAGEKHRPROC eglDestroyImageKHR = (PFNEGLDESTROYIMAGEKHRPROC)eglGetProcAddress("eglDestroyImageKHR");
		for (GLuint texture_id : m_pending_deletions) {
			auto it = m_texture_to_image_map.find(texture_id);
			if (it != m_texture_to_image_map.end()) {
				if (eglDestroyImageKHR && m_egl_display != EGL_NO_DISPLAY) {
					eglDestroyImageKHR(m_egl_display, it->second);
				}
				m_texture_to_image_map.erase(it);
			}
		}

		m_pending_deletions.clear();
	}
}

bool gTextureManager::ensureFramebuffer(gUnmanagedSurface* surface, bool preserve_cpu_content) {
	if (!surface || surface->bpp != 32 || surface->x <= 0 || surface->y <= 0)
		return false;
	prepareSurface(surface);
	if (eglGetCurrentContext() == EGL_NO_CONTEXT)
		return false;

	if (surface->gl_texture_id && preserve_cpu_content && !surface->gl_content_valid) {
		if (!surface->cpu_content_valid)
			return false;
		if (surface->gl_framebuffer_id) {
			queueFramebufferForDeletion(surface->gl_framebuffer_id);
			surface->gl_framebuffer_id = 0;
		}
		queueForDeletion(surface->gl_texture_id);
		surface->gl_texture_id = 0;
	}

	if (!surface->gl_texture_id) {
		GLuint texture_id = 0;
		if (preserve_cpu_content) {
			if (!surface->cpu_content_valid)
				return false;
			texture_id = createTextureFromSurface(surface);
		} else {
			glGenTextures(1, &texture_id);
			glBindTexture(GL_TEXTURE_2D, texture_id);
			glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
			glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
			glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE);
			glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE);
			glPixelStorei(GL_UNPACK_ALIGNMENT, 4);
			glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, surface->x, surface->y, 0, GL_RGBA, GL_UNSIGNED_BYTE, nullptr);
			if (glGetError() != GL_NO_ERROR) {
				glDeleteTextures(1, &texture_id);
				return false;
			}
			glBindTexture(GL_TEXTURE_2D, 0);
		}

		if (!texture_id)
			return false;
		surface->gl_texture_id = texture_id;
		surface->gl_content_valid = preserve_cpu_content;
	}

	if (!surface->gl_framebuffer_id) {
		glGenFramebuffers(1, &surface->gl_framebuffer_id);
		glBindFramebuffer(GL_FRAMEBUFFER, surface->gl_framebuffer_id);
		glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, surface->gl_texture_id, 0);
		if (glCheckFramebufferStatus(GL_FRAMEBUFFER) != GL_FRAMEBUFFER_COMPLETE) {
			glBindFramebuffer(GL_FRAMEBUFFER, 0);
			glDeleteFramebuffers(1, &surface->gl_framebuffer_id);
			surface->gl_framebuffer_id = 0;
			return false;
		}
		glBindFramebuffer(GL_FRAMEBUFFER, 0);
	}

	return true;
}

bool gTextureManager::fillSurface(gUnmanagedSurface* surface, const eRect& area, uint32_t color) {
	if (!surface || area.empty() || surface->bpp != 32)
		return false;

	eRect clipped = area & eRect(0, 0, surface->x, surface->y);
	if (clipped.empty())
		return true;

	const bool full_surface = clipped.left() == 0 && clipped.top() == 0 && clipped.width() == surface->x && clipped.height() == surface->y;
	if (!ensureFramebuffer(surface, !full_surface && !surface->gl_content_valid))
		return false;

	GLint previous_framebuffer = 0;
	GLint previous_viewport[4] = {0, 0, 0, 0};
	GLint previous_scissor[4] = {0, 0, 0, 0};
	GLboolean scissor_enabled = glIsEnabled(GL_SCISSOR_TEST);
	GLfloat previous_clear_color[4] = {0.0f, 0.0f, 0.0f, 0.0f};

	glGetIntegerv(GL_FRAMEBUFFER_BINDING, &previous_framebuffer);
	glGetIntegerv(GL_VIEWPORT, previous_viewport);
	glGetIntegerv(GL_SCISSOR_BOX, previous_scissor);
	glGetFloatv(GL_COLOR_CLEAR_VALUE, previous_clear_color);

	glBindFramebuffer(GL_FRAMEBUFFER, surface->gl_framebuffer_id);
	glViewport(0, 0, surface->x, surface->y);
	glEnable(GL_SCISSOR_TEST);
	glScissor(clipped.left(), clipped.top(), clipped.width(), clipped.height());
	glClearColor(((color >> 16) & 0xff) / 255.0f, ((color >> 8) & 0xff) / 255.0f, (color & 0xff) / 255.0f, ((color >> 24) & 0xff) / 255.0f);
	glClear(GL_COLOR_BUFFER_BIT);

	if (scissor_enabled)
		glEnable(GL_SCISSOR_TEST);
	else
		glDisable(GL_SCISSOR_TEST);
	glScissor(previous_scissor[0], previous_scissor[1], previous_scissor[2], previous_scissor[3]);
	glViewport(previous_viewport[0], previous_viewport[1], previous_viewport[2], previous_viewport[3]);
	glClearColor(previous_clear_color[0], previous_clear_color[1], previous_clear_color[2], previous_clear_color[3]);
	glBindFramebuffer(GL_FRAMEBUFFER, previous_framebuffer);

	if (glGetError() != GL_NO_ERROR)
		return false;

	surface->gl_content_valid = true;
	surface->cpu_content_valid = false;
	return true;
}

bool gTextureManager::drawRectangleSurface(gUnmanagedSurface* surface, const gRegion& region, const eRect& area, const gRGB& background_color, const gRGB& border_color, int border_width,
	const std::vector<gRGB>& gradient_colors, uint8_t direction, int radius, uint8_t edges, bool alphablend, int gradient_full_size, bool use_new)
{
	if (!surface || surface->bpp != 32 || area.empty())
		return false;
	if (direction && gradient_colors.size() < 2)
		return false;

	const eRect surface_rect(0, 0, surface->x, surface->y);
	eRect draw_area = area & surface_rect;
	if (draw_area.empty())
		return true;

	gRegion draw_region = (region & draw_area) & surface_rect;
	if (draw_region.rects.empty())
		return true;

	const bool blend_border = border_width > 0 && (use_new || radius > 0);
	const bool blend_rect = use_new || radius > 0 || (!gradient_colors.empty() && alphablend);
	const bool full_overwrite = !blend_border && !blend_rect && radius <= 0 && regionCoversRect(draw_region, surface_rect);
	if (!ensureFramebuffer(surface, !full_overwrite && !surface->gl_content_valid))
		return false;
	if (!ensureOffscreenAdvancedShader())
		return false;

	GLint previous_framebuffer = 0;
	GLint previous_viewport[4] = {0, 0, 0, 0};
	GLint previous_scissor[4] = {0, 0, 0, 0};
	GLint previous_blend_src_rgb = GL_ONE;
	GLint previous_blend_dst_rgb = GL_ZERO;
	GLint previous_blend_src_alpha = GL_ONE;
	GLint previous_blend_dst_alpha = GL_ZERO;
	GLint previous_blend_equation_rgb = GL_FUNC_ADD;
	GLint previous_blend_equation_alpha = GL_FUNC_ADD;
	GLboolean scissor_enabled = glIsEnabled(GL_SCISSOR_TEST);
	GLboolean blend_enabled = glIsEnabled(GL_BLEND);

	glGetIntegerv(GL_FRAMEBUFFER_BINDING, &previous_framebuffer);
	glGetIntegerv(GL_VIEWPORT, previous_viewport);
	glGetIntegerv(GL_SCISSOR_BOX, previous_scissor);
	glGetIntegerv(GL_BLEND_SRC_RGB, &previous_blend_src_rgb);
	glGetIntegerv(GL_BLEND_DST_RGB, &previous_blend_dst_rgb);
	glGetIntegerv(GL_BLEND_SRC_ALPHA, &previous_blend_src_alpha);
	glGetIntegerv(GL_BLEND_DST_ALPHA, &previous_blend_dst_alpha);
	glGetIntegerv(GL_BLEND_EQUATION_RGB, &previous_blend_equation_rgb);
	glGetIntegerv(GL_BLEND_EQUATION_ALPHA, &previous_blend_equation_alpha);

	glBindFramebuffer(GL_FRAMEBUFFER, surface->gl_framebuffer_id);
	glViewport(0, 0, surface->x, surface->y);
	glEnable(GL_SCISSOR_TEST);
	m_offscreen_advanced_shader.setFramebufferResolution((float)surface->x, (float)surface->y);

	auto setBlend = [](bool enable) {
		if (enable) {
			glEnable(GL_BLEND);
			glBlendFuncSeparate(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA, GL_ONE, GL_ONE_MINUS_SRC_ALPHA);
			glBlendEquationSeparate(GL_FUNC_ADD, GL_FUNC_ADD);
		} else {
			glDisable(GL_BLEND);
		}
	};

	auto drawClippedRect = [&](const eRect& rect, int rect_radius, uint8_t rect_edges, const std::vector<gRGB>& rect_gradient, uint8_t rect_direction, bool rect_alphablend,
								int rect_gradient_full_size, const gRGB& color) {
		if (rect.empty())
			return;
		for (unsigned int i = 0; i < draw_region.rects.size(); ++i) {
			eRect clipped = draw_region.rects[i] & rect;
			if (clipped.empty())
				continue;
			glScissor(clipped.left(), clipped.top(), clipped.width(), clipped.height());
			m_offscreen_advanced_shader.drawAdvancedRect(rect.x(), rect.y(), rect.width(), rect.height(), rect_radius, rect_edges, rect_gradient, rect_direction, rect_alphablend,
				rect_gradient_full_size, textureColorAlpha(color), color);
		}
	};

	eRect body_area = area;
	const int clamped_border_width = std::max(0, std::min(border_width, std::min(body_area.width(), body_area.height()) / 2));
	if (clamped_border_width > 0) {
		setBlend(blend_border);
		drawClippedRect(body_area, radius, edges, std::vector<gRGB>(), 0, false, 0, border_color);
		body_area = eRect(body_area.left() + clamped_border_width, body_area.top() + clamped_border_width,
			body_area.width() - 2 * clamped_border_width, body_area.height() - 2 * clamped_border_width);
	}

	if (!body_area.empty()) {
		setBlend(blend_rect);
		int inner_radius = radius;
		if (clamped_border_width > 0)
			inner_radius = std::max(0, radius - clamped_border_width);
		drawClippedRect(body_area, inner_radius, edges, gradient_colors, direction, alphablend, gradient_full_size, background_color);
	}

	GLenum err = glGetError();
	if (blend_enabled)
		glEnable(GL_BLEND);
	else
		glDisable(GL_BLEND);
	glBlendFuncSeparate(previous_blend_src_rgb, previous_blend_dst_rgb, previous_blend_src_alpha, previous_blend_dst_alpha);
	glBlendEquationSeparate(previous_blend_equation_rgb, previous_blend_equation_alpha);
	if (scissor_enabled)
		glEnable(GL_SCISSOR_TEST);
	else
		glDisable(GL_SCISSOR_TEST);
	glScissor(previous_scissor[0], previous_scissor[1], previous_scissor[2], previous_scissor[3]);
	glViewport(previous_viewport[0], previous_viewport[1], previous_viewport[2], previous_viewport[3]);
	glBindFramebuffer(GL_FRAMEBUFFER, previous_framebuffer);

	if (err != GL_NO_ERROR)
		return false;

	surface->gl_content_valid = true;
	surface->cpu_content_valid = false;
	return true;
}

bool gTextureManager::blitSurface(gUnmanagedSurface* dst, gUnmanagedSurface* src, const eRect& dest_rect, const eRect& area, int flags, int radius, uint8_t edges)
{
	if (!dst || !src || dst == src || dst->bpp != 32 || src->bpp != 32 || dest_rect.empty() || area.empty())
		return false;

	const eRect dst_rect(0, 0, dst->x, dst->y);
	const eRect src_rect(0, 0, src->x, src->y);
	eRect clipped_area = area & dst_rect;
	if (clipped_area.empty() || src_rect.empty())
		return true;

	const bool alpha_blend = (flags & gPixmap::blitAlphaBlend) || radius > 0;
	const bool alpha_test = flags & gPixmap::blitAlphaTest;
	const bool full_overwrite = !alpha_blend && !alpha_test && radius <= 0 && clipped_area == dst_rect && dest_rect == dst_rect;
	if (!ensureFramebuffer(dst, !full_overwrite && !dst->gl_content_valid))
		return false;

	GLuint texture_id = getSurfaceTexture(src);
	if (!texture_id)
		return false;
	if (!ensureOffscreenTextureShader())
		return false;

	GLint previous_framebuffer = 0;
	GLint previous_viewport[4] = {0, 0, 0, 0};
	GLint previous_scissor[4] = {0, 0, 0, 0};
	GLint previous_blend_src_rgb = GL_ONE;
	GLint previous_blend_dst_rgb = GL_ZERO;
	GLint previous_blend_src_alpha = GL_ONE;
	GLint previous_blend_dst_alpha = GL_ZERO;
	GLint previous_blend_equation_rgb = GL_FUNC_ADD;
	GLint previous_blend_equation_alpha = GL_FUNC_ADD;
	GLboolean scissor_enabled = glIsEnabled(GL_SCISSOR_TEST);
	GLboolean blend_enabled = glIsEnabled(GL_BLEND);

	glGetIntegerv(GL_FRAMEBUFFER_BINDING, &previous_framebuffer);
	glGetIntegerv(GL_VIEWPORT, previous_viewport);
	glGetIntegerv(GL_SCISSOR_BOX, previous_scissor);
	glGetIntegerv(GL_BLEND_SRC_RGB, &previous_blend_src_rgb);
	glGetIntegerv(GL_BLEND_DST_RGB, &previous_blend_dst_rgb);
	glGetIntegerv(GL_BLEND_SRC_ALPHA, &previous_blend_src_alpha);
	glGetIntegerv(GL_BLEND_DST_ALPHA, &previous_blend_dst_alpha);
	glGetIntegerv(GL_BLEND_EQUATION_RGB, &previous_blend_equation_rgb);
	glGetIntegerv(GL_BLEND_EQUATION_ALPHA, &previous_blend_equation_alpha);

	glBindFramebuffer(GL_FRAMEBUFFER, dst->gl_framebuffer_id);
	glViewport(0, 0, dst->x, dst->y);
	glEnable(GL_SCISSOR_TEST);
	glScissor(clipped_area.left(), clipped_area.top(), clipped_area.width(), clipped_area.height());
	if (alpha_blend) {
		glEnable(GL_BLEND);
		glBlendFuncSeparate(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA, GL_ONE, GL_ONE_MINUS_SRC_ALPHA);
		glBlendEquationSeparate(GL_FUNC_ADD, GL_FUNC_ADD);
	} else {
		glDisable(GL_BLEND);
	}

	m_offscreen_texture_shader.setFramebufferResolution((float)dst->x, (float)dst->y);
	m_offscreen_texture_shader.drawTexture(dest_rect.x(), dest_rect.y(), dest_rect.width(), dest_rect.height(), texture_id, 1.0f, (float)radius, edges, 0.0f, 0.0f, 1.0f, 1.0f,
		alpha_test, false);

	GLenum err = glGetError();
	if (blend_enabled)
		glEnable(GL_BLEND);
	else
		glDisable(GL_BLEND);
	glBlendFuncSeparate(previous_blend_src_rgb, previous_blend_dst_rgb, previous_blend_src_alpha, previous_blend_dst_alpha);
	glBlendEquationSeparate(previous_blend_equation_rgb, previous_blend_equation_alpha);
	if (scissor_enabled)
		glEnable(GL_SCISSOR_TEST);
	else
		glDisable(GL_SCISSOR_TEST);
	glScissor(previous_scissor[0], previous_scissor[1], previous_scissor[2], previous_scissor[3]);
	glViewport(previous_viewport[0], previous_viewport[1], previous_viewport[2], previous_viewport[3]);
	glBindFramebuffer(GL_FRAMEBUFFER, previous_framebuffer);

	if (err != GL_NO_ERROR)
		return false;

	dst->gl_content_valid = true;
	dst->cpu_content_valid = false;
	return true;
}

bool gTextureManager::syncSurfaceToCPU(gUnmanagedSurface* surface) {
	if (!surface)
		return false;
	prepareSurface(surface);
	if (surface->cpu_content_valid)
		return true;
	if (!surface->gl_texture_id || !surface->gl_content_valid || surface->bpp != 32 || !surface->data)
		return false;
	if (!ensureFramebuffer(surface, false))
		return false;

	GLint previous_framebuffer = 0;
	GLint previous_pack_alignment = 4;
	glGetIntegerv(GL_FRAMEBUFFER_BINDING, &previous_framebuffer);
	glGetIntegerv(GL_PACK_ALIGNMENT, &previous_pack_alignment);

	std::vector<uint8_t> rgba(surface->x * surface->y * 4);
	glBindFramebuffer(GL_FRAMEBUFFER, surface->gl_framebuffer_id);
	glPixelStorei(GL_PACK_ALIGNMENT, 4);
	glReadPixels(0, 0, surface->x, surface->y, GL_RGBA, GL_UNSIGNED_BYTE, rgba.data());
	GLenum err = glGetError();
	glPixelStorei(GL_PACK_ALIGNMENT, previous_pack_alignment);
	glBindFramebuffer(GL_FRAMEBUFFER, previous_framebuffer);
	if (err != GL_NO_ERROR)
		return false;

	for (int y = 0; y < surface->y; ++y) {
		const uint8_t* src = rgba.data() + y * surface->x * 4;
		uint8_t* dst = (uint8_t*)surface->data + y * surface->stride;
		for (int x = 0; x < surface->x; ++x) {
			dst[x * 4 + 0] = src[x * 4 + 2];
			dst[x * 4 + 1] = src[x * 4 + 1];
			dst[x * 4 + 2] = src[x * 4 + 0];
			dst[x * 4 + 3] = src[x * 4 + 3];
		}
	}

	surface->cpu_content_valid = true;
	return true;
}

extern "C" void egl_queue_texture_deletion(unsigned int gl_texture_id, unsigned int context_generation);
void egl_queue_texture_deletion(unsigned int gl_texture_id, unsigned int context_generation) {
	std::lock_guard<std::mutex> guard(activeManagerMutex());
	if (s_active_manager) {
		s_active_manager->queueForDeletion(gl_texture_id, context_generation);
	}
}

extern "C" void egl_queue_framebuffer_deletion(unsigned int gl_framebuffer_id, unsigned int context_generation);
void egl_queue_framebuffer_deletion(unsigned int gl_framebuffer_id, unsigned int context_generation) {
	std::lock_guard<std::mutex> guard(activeManagerMutex());
	if (s_active_manager) {
		s_active_manager->queueFramebufferForDeletion(gl_framebuffer_id, context_generation);
	}
}

extern "C" bool egl_gpixmap_fill(gUnmanagedSurface* surface, int x, int y, int w, int h, uint32_t color);
bool egl_gpixmap_fill(gUnmanagedSurface* surface, int x, int y, int w, int h, uint32_t color) {
	return s_active_manager && s_active_manager->fillSurface(surface, eRect(x, y, w, h), color);
}

extern "C" bool egl_gpixmap_draw_rectangle(gUnmanagedSurface* surface, const gRegion* region, int x, int y, int w, int h, uint32_t background_color, uint32_t border_color, int border_width,
	const gRGB* gradient_colors, int gradient_count, uint8_t direction, int radius, uint8_t edges, bool alphablend, int gradient_full_size, bool use_new);
bool egl_gpixmap_draw_rectangle(gUnmanagedSurface* surface, const gRegion* region, int x, int y, int w, int h, uint32_t background_color, uint32_t border_color, int border_width,
	const gRGB* gradient_colors, int gradient_count, uint8_t direction, int radius, uint8_t edges, bool alphablend, int gradient_full_size, bool use_new)
{
	if (!s_active_manager || !region)
		return false;
	std::vector<gRGB> colors;
	if (gradient_colors && gradient_count > 0)
		colors.assign(gradient_colors, gradient_colors + gradient_count);
	return s_active_manager->drawRectangleSurface(surface, *region, eRect(x, y, w, h), gRGB(background_color), gRGB(border_color), border_width, colors, direction, radius, edges, alphablend,
		gradient_full_size, use_new);
}

extern "C" bool egl_gpixmap_blit(gUnmanagedSurface* dst, gUnmanagedSurface* src, int dx, int dy, int dw, int dh, int ax, int ay, int aw, int ah, int flags, int radius, uint8_t edges);
bool egl_gpixmap_blit(gUnmanagedSurface* dst, gUnmanagedSurface* src, int dx, int dy, int dw, int dh, int ax, int ay, int aw, int ah, int flags, int radius, uint8_t edges)
{
	return s_active_manager && s_active_manager->blitSurface(dst, src, eRect(dx, dy, dw, dh), eRect(ax, ay, aw, ah), flags, radius, edges);
}

extern "C" bool egl_sync_surface_to_cpu(gUnmanagedSurface* surface);
bool egl_sync_surface_to_cpu(gUnmanagedSurface* surface) {
	return s_active_manager && s_active_manager->syncSurfaceToCPU(surface);
}
