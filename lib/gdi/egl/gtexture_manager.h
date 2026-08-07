#pragma once

#ifdef HAVE_GLES3
#include <GLES3/gl3.h>
#else
#include <GLES2/gl2.h>
#include <GLES2/gl2ext.h>
#endif

#include <EGL/egl.h>
#include <EGL/eglext.h>
#include <lib/gdi/egl/shader/gadvanced_shader.h>
#include <lib/gdi/egl/shader/gtexture_shader.h>
#include <lib/gdi/gpixmap.h>
#include <mutex>
#include <stdint.h>
#include <unordered_map>
#include <vector>

class gRegion;

struct gTextureUploadStats {
	unsigned int textures = 0;
	unsigned int dmabuf = 0;
	unsigned int upload32_direct = 0;
	unsigned int upload32_converted = 0;
	unsigned int upload8_clut = 0;
	unsigned int upload8_luma = 0;
	unsigned int content_cache_hits = 0;
	unsigned int content_cache_misses = 0;
	unsigned long long pixels = 0;
	unsigned long long bytes = 0;
};

class gTextureManager {
private:
	// thread safe garbage collection for destroyed pixmaps
	std::vector<GLuint> m_pending_deletions;
	std::vector<GLuint> m_pending_framebuffer_deletions;
	std::mutex m_deletion_mutex;
	EGLDisplay m_egl_display;
	std::unordered_map<GLuint, EGLImageKHR> m_texture_to_image_map;
	gTextureUploadStats m_upload_stats;
	struct ContentTextureEntry {
		GLuint texture_id = 0;
		unsigned long long bytes = 0;
		unsigned int last_used = 0;
	};
	std::unordered_map<uint64_t, ContentTextureEntry> m_content_texture_cache;
	unsigned int m_content_texture_use_counter;
	unsigned long long m_content_texture_bytes;
	gAdvancedShader m_offscreen_advanced_shader;
	gTextureShader m_offscreen_texture_shader;
	bool m_offscreen_advanced_shader_initialized;
	bool m_offscreen_texture_shader_initialized;
	unsigned int m_context_generation;

	// unified method to generate and upload the texture based on bpp
	GLuint createTextureFromSurface(gUnmanagedSurface* surface);
	GLuint getSurfaceTexture(gUnmanagedSurface* surface);
	GLuint createTextureFromDmabuf(gUnmanagedSurface* surface);
	void recordUpload(int width, int height, int bytes, bool dmabuf, bool upload32_direct, bool upload32_converted, bool upload8_clut, bool upload8_luma);
	bool ensureFramebuffer(gUnmanagedSurface* surface, bool preserve_cpu_content);
	bool canContentCacheSurface(const gUnmanagedSurface* surface) const;
	uint64_t hashContentTextureSurface(const gUnmanagedSurface* surface) const;
	GLuint findContentTexture(uint64_t key);
	GLuint storeContentTexture(uint64_t key, GLuint texture_id, unsigned long long bytes);
	void trimContentTextureCache();
	bool ensureOffscreenAdvancedShader();
	bool ensureOffscreenTextureShader();

public:
	gTextureManager();
	~gTextureManager();

	void setDisplay(EGLDisplay display) { m_egl_display = display; }

	// returns the gl texture id, creating it on the fly if not cached
	GLuint getTexture(gPixmap* pixmap);

	// called by enigma2 main thread when a pixmap dies
	void queueForDeletion(GLuint texture_id, unsigned int context_generation = 0);
	void queueFramebufferForDeletion(GLuint framebuffer_id, unsigned int context_generation = 0);

	// called by our egl context thread at the start of exec() to free vram
	void processDeletions();
	void clearContentTextureCache();
	void releaseGLResources();
	void resetContextGeneration();
	void prepareSurface(gUnmanagedSurface* surface);

	void takeUploadStats(gTextureUploadStats& stats);
	bool fillSurface(gUnmanagedSurface* surface, const eRect& area, uint32_t color);
	bool drawRectangleSurface(gUnmanagedSurface* surface, const gRegion& region, const eRect& area, const gRGB& background_color, const gRGB& border_color, int border_width,
		const std::vector<gRGB>& gradient_colors, uint8_t direction, int radius, uint8_t edges, bool alphablend, int gradient_full_size, bool use_new);
	bool blitSurface(gUnmanagedSurface* dst, gUnmanagedSurface* src, const eRect& dest_rect, const eRect& area, int flags, int radius, uint8_t edges);
	bool syncSurfaceToCPU(gUnmanagedSurface* surface);
};
