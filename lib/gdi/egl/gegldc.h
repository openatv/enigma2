#pragma once

#include <EGL/egl.h>
#ifdef HAVE_GLES3
#include <GLES3/gl3.h>
#else
#include <GLES2/gl2.h>
#include <GLES2/gl2ext.h>
#endif
#include <lib/gdi/egl/gtexture_manager.h>
#include <lib/gdi/egl/inative_window_provider.h>
#include <lib/gdi/egl/shader/gadvanced_shader.h>
#include <lib/gdi/egl/shader/gshader.h>
#include <lib/gdi/egl/shader/gtext_shader.h>
#include <lib/gdi/egl/shader/gtexture_shader.h>
#include <lib/gdi/gfont_atlas.h>
#include <lib/gdi/gmaindc.h>
#include <atomic>
#include <mutex>
#include <pthread.h>
#include <vector>

class gEGLDCAutoInit;
class fbClass;

class gEGLDC : public gMainDC {
private:
	INativeWindowProvider* m_window_provider;
	fbClass* m_fb;
	EGLDisplay m_egl_display;
	EGLConfig m_egl_config;
	EGLSurface m_egl_surface;
	EGLContext m_egl_context;

	int m_width;
	int m_height;
	int m_surface_width;
	int m_surface_height;
	int m_osd_left;
	int m_osd_top;
	int m_osd_width;
	int m_osd_height;
	int m_egl_major;
	int m_egl_minor;
	int m_gles_version; // 2 or 3
	GLint m_max_texture_size;
	int m_flip_count;
	bool m_preserved_swap;
	bool m_native_window_ready;
	bool m_video_mode_surface_active;
	bool m_graphics_suspended;
	bool m_egl_client_released;
	bool m_surface_lost;
	unsigned long long m_surface_retry_us;
	std::recursive_mutex m_egl_mutex;

	gShader m_basic_shader;
	gAdvancedShader m_advanced_shader;
	gTextureShader m_texture_shader;
	gTextShader m_text_shader;

	gFontAtlas m_font_atlas;
	gTextureManager m_texture_manager;

	struct PendingWindowAnimation {
		bool active;
		bool show;
		eRect rect;
		PendingWindowAnimation() : active(false), show(true), rect(eRect()) {}
	};

	PendingWindowAnimation m_pending_window_animation;
	struct PendingListboxAnimation {
		bool active;
		eRect from;
		eRect to;
		gRGB background_color;
		std::vector<gRGB> gradient_colors;
		uint8_t gradient_orientation;
		bool gradient_alpha_blend;
		int radius;
		uint8_t radius_edges;
		ePtr<gPixmap> selection_pixmap;
		PendingListboxAnimation() : active(false), from(eRect()), to(eRect()), background_color(gRGB()),
			gradient_orientation(0), gradient_alpha_blend(false), radius(0), radius_edges(0) {}
	};

	PendingListboxAnimation m_pending_listbox_animation;
	GLuint m_last_frame_texture;
	GLuint m_animation_frame_texture;
	GLuint m_scene_frame_texture;
	GLuint m_scene_framebuffer;
	GLuint m_scene_spare_frame_texture;
	GLuint m_scene_spare_framebuffer;
	GLuint m_scene_animation_old_texture;
	bool m_last_frame_valid;
	bool m_frame_restore_pending;
	bool m_frame_texture_surface;
	bool m_frame_texture_scene_scaled;
	int m_frame_texture_width;
	int m_frame_texture_height;
	int m_scene_frame_width;
	int m_scene_frame_height;
	bool m_scene_frame_valid;
	bool m_scene_spare_frame_valid;
	bool m_scene_animation_old_valid;
	bool m_scene_framebuffer_unavailable;
	bool m_spinner_background_valid;
	int m_spinner_background_width;
	int m_spinner_background_height;
	bool m_spinner_background_clear;
	bool m_spinner_clear_pending;
	int m_capture_socket_fd;
	pthread_t m_capture_thread;
	bool m_capture_thread_started;
	std::atomic<bool> m_capture_thread_stop;

	struct FrameStats {
		unsigned int fill_ops = 0;
		unsigned int fill_rects = 0;
		unsigned int solid_batches = 0;
		unsigned int solid_vertices = 0;
		unsigned int clear_ops = 0;
		unsigned int clear_rects = 0;
		unsigned int rect_ops = 0;
		unsigned int rect_rects = 0;
		unsigned int gradient_ops = 0;
		unsigned int rounded_ops = 0;
		unsigned int line_ops = 0;
		unsigned int line_rects = 0;
		unsigned int blit_ops = 0;
		unsigned int blit_rects = 0;
		unsigned int glyphs = 0;
		unsigned int text_ops = 0;
		unsigned int text_batches = 0;
		unsigned int text_draw_rects = 0;
		unsigned int text_flush_fill = 0;
		unsigned int text_flush_rect = 0;
		unsigned int text_flush_line = 0;
		unsigned int text_flush_blit = 0;
		unsigned int text_flush_clear = 0;
		unsigned int text_flush_state = 0;
		unsigned int text_flush_atlas = 0;
		unsigned int text_flush_limit = 0;
		unsigned int text_overlap_checks = 0;
		unsigned int text_overlap_rect_tests = 0;
		unsigned int font_uploads = 0;
		unsigned int frame_captures = 0;
		unsigned int frame_restores = 0;
		unsigned int frame_copy_draws = 0;
		unsigned int texture_uploads = 0;
		unsigned int texture_dmabuf_uploads = 0;
		unsigned int texture_32_direct_uploads = 0;
		unsigned int texture_32_converted_uploads = 0;
		unsigned int texture_8_clut_uploads = 0;
		unsigned int texture_8_luma_uploads = 0;
		unsigned int texture_content_cache_hits = 0;
		unsigned int texture_content_cache_misses = 0;
		unsigned int context_make_calls = 0;
		unsigned int context_release_calls = 0;
		unsigned long long fill_pixels = 0;
		unsigned long long clear_pixels = 0;
		unsigned long long rect_pixels = 0;
		unsigned long long blit_pixels = 0;
		unsigned long long font_upload_pixels = 0;
		unsigned long long frame_copy_pixels = 0;
		unsigned long long texture_upload_pixels = 0;
		unsigned long long texture_upload_bytes = 0;
		unsigned long long frame_start_us = 0;
		unsigned long long draw_us = 0;
		unsigned long long swap_us = 0;
		unsigned long long capture_us = 0;
		unsigned long long restore_us = 0;
		unsigned long long fill_us = 0;
		unsigned long long rect_us = 0;
		unsigned long long clear_us = 0;
		unsigned long long line_us = 0;
		unsigned long long blit_us = 0;
		unsigned long long text_build_us = 0;
		unsigned long long text_us = 0;
		unsigned long long state_us = 0;
		unsigned long long overlap_us = 0;
		unsigned long long texture_gc_us = 0;
		unsigned long long copy_us = 0;
		unsigned long long context_make_us = 0;
		unsigned long long context_release_us = 0;
	};
	FrameStats m_frame_stats;
	unsigned int m_frame_stats_index;

	std::vector<float> m_text_batch_buffer;
	std::vector<eRect> m_text_batch_rects;
	eRect m_text_batch_bounds;
	bool m_text_batch_bounds_valid;
	std::vector<float> m_fill_batch_buffer;
	eRect m_fill_batch_bounds;
	gRGB m_fill_batch_color;
	bool m_fill_batch_blend;
	bool m_fill_batch_valid;
	const size_t MAX_BATCH_GLYPHS = 4096;

	enum TextFlushReason {
		textFlushFill,
		textFlushRectangle,
		textFlushLine,
		textFlushBlit,
		textFlushClear,
		textFlushState,
		textFlushAtlas,
		textFlushLimit
	};

	bool tryInitEGL(int version);
	bool makeCurrent();
	bool releaseCurrent(bool force = false);
	void applySwapBehavior();
	void primeEGLSurface(bool preserve_scene = false);
	void cleanupEGL();
	// Frees the surface and GL objects; releaseClient also terminates the EGL display and context.
	bool releaseGraphics(bool releaseClient);

	// dedicated opcode handlers
	void executeFill(const gOpcode* op);
	void executeFillRegion(const gOpcode* op);
	void executeRectangle(const gOpcode* op);
	void executeLine(const gOpcode* op);
	void executeBlit(const gOpcode* op);
	void executeDrawGlyph(const gOpcode* op);
	void executeClear(const gOpcode* op);
	void drawRegion(const gRegion& region, const gRGB& color, bool blend = false, bool count_stats = true);
	void flushFillBatch();
	void flushFillBatchIfOverlaps(const eRect& area);
	void flushFillBatchIfOverlaps(const gRegion& region);
	bool fillBatchIntersects(const eRect& area) const;
	bool fillBatchIntersects(const gRegion& region) const;
	void drawPixmap(gPixmap* pixmap, const eRect& pos, int flags);
	bool readFramebufferRegion(const eRect& pos, gPixmap* pixmap);
	bool readOSDToBGRA(std::vector<unsigned char>& pixels, int& width, int& height);
	bool writeCaptureFrame(int client_fd);
	void startCaptureServer();
	void stopCaptureServer();
	static void* captureServerThreadEntry(void* arg);
	void captureServerThread();
	bool ensureFrameTexture(GLuint& texture);
	bool copyCurrentFrameToTexture(GLuint& texture);
	void deleteFrameTextures();
	bool sceneFramebufferWanted() const;
	bool sceneFramebufferActive() const;
	bool sceneFramebufferUsesSurfaceScale() const;
	int sceneFramebufferWidth() const;
	int sceneFramebufferHeight() const;
	eRect logicalToSceneRect(const eRect& rect) const;
	bool currentFramebufferIsScene() const;
	bool ensureSceneFramebufferObject(GLuint& texture, GLuint& framebuffer, bool& valid, int width, int height, const char* label);
	bool ensureSceneFramebuffer();
	bool ensureSpareSceneFramebuffer();
	void deleteSceneFramebuffer();
	void markSurfaceLost();
	bool bindSceneFramebuffer();
	void bindWindowFramebuffer();
	eRect osdDestinationLogical() const;
	eRect osdDestinationSurface() const;
	eRect logicalToSurfaceRect(const eRect& rect) const;
	void applyWindowViewport();
	void clearSceneFramebuffer();
	bool presentSceneFramebuffer();
	bool beginSceneFramebufferAnimation();
	void finishSceneFramebufferAnimation();
	bool swapWindowFramebuffer();
	void captureCurrentFrameAsLast();
	void restoreFrameIfNeeded();
	void executeWindowAnimationOpcode(const gOpcode* op, bool show);
	bool runPendingWindowAnimation();
	void executeListboxAnimationOpcode(const gOpcode* op);
	bool runPendingListboxAnimation();
	void drawListboxSelection(const eRect& area, const PendingListboxAnimation& animation);
	void copiedTextureSize(GLuint texture, int& width, int& height) const;
	void drawCopiedFrameTexture(GLuint texture, const eRect& dest, const eRect& source, float alpha, bool blend);
	eRect animatedWindowDestRect(const eRect& source, float visible_progress, bool show, float* alpha = 0) const;
	eRect stripedWindowDamageRect(const eRect& source) const;
	void drawAnimatedWindowTexture(GLuint texture, const eRect& source, float visible_progress, bool show);
	void drawStripedWindowTexture(GLuint texture, const eRect& source, float visible_progress);
	eRect clampToScreen(const eRect& rect) const;
	eRect currentSpinnerRect() const;
	gPixmap* currentSpinnerBackground() const;
	void clearSpinnerRect(const eRect& rect);
	bool clearSpinnerBackgroundPixmap(gPixmap* background);
	bool captureSpinnerBackground();
	void invalidateSpinnerBackground(bool clear_pending = false);
	void resetRectangleState();
	void resetBlitState();
	void flushTextBatch();
	void flushTextBatchForReason(TextFlushReason reason);
	void flushTextBatchIfOverlaps(const eRect& area, TextFlushReason reason);
	void flushTextBatchIfOverlaps(const gRegion& region, TextFlushReason reason);
	void addTextBatchRect(const eRect& rect);
	void noteTextFlushReason(TextFlushReason reason);
	bool textBatchIntersects(const eRect& area);
	bool textBatchIntersects(const gRegion& region);
	eRect lineDrawBounds(const gOpcode::para::pline* op) const;
	eRect blitDrawBounds(const gOpcode::para::pblit* op) const;
	void setGlScissor(const eRect& rect);
	void setTextureFiltering(GLuint texture, bool linear);
	bool currentFramebufferUsesSurface() const;
	int surfaceWidth() const;
	int surfaceHeight() const;
	bool updateVideoModeSurfaceSize(const char* reason);
	int scaleSurfaceFloorX(int value) const;
	int scaleSurfaceCeilX(int value) const;
	int scaleSurfaceFloorY(int value) const;
	int scaleSurfaceCeilY(int value) const;
	void resetFrameStats(unsigned long long now_us = 0);
	void addTextureUploadStats();
	void logAndResetFrameStats();

	bool isHardwareAccelerated() const override { return true; }
	bool supportsShowHideAnimations() const override { return true; }
	bool supportsListboxAnimations() const override;
	void fillTextBackground(const gRegion& clip) override;
	void renderGlyph(const ePoint& pos, gPixmap* glyph_mask, const gRGB& color) override;
	void enableSpinner() override;
	void disableSpinner() override;
	void incrementSpinner() override;

public:
	bool initEGL();
	gEGLDC(INativeWindowProvider* window_provider = nullptr, int width = 1280, int height = 720);
	virtual ~gEGLDC();

	virtual void setResolution(int xres, int yres, int bpp = 32) override;
	virtual void refresh() override;
	virtual void exec(const gOpcode* opcode);
	int islocked() const override;
	std::string getGraphicsBackend() const override { return "e2egl"; }
	std::string getGraphicsWindowProvider() const override;
	std::string getGraphicsAccelerator() const override;
	std::string getGraphicsBuffering() const override;
	int getGraphicsBufferPages() const override;
	int getGraphicsLogicalWidth() const override { return m_width; }
	int getGraphicsLogicalHeight() const override { return m_height; }
	int getGraphicsSurfaceWidth() const override { return surfaceWidth(); }
	int getGraphicsSurfaceHeight() const override { return surfaceHeight(); }
	int getGraphicsEGLMajor() const override { return m_egl_major; }
	int getGraphicsEGLMinor() const override { return m_egl_minor; }
	int getGraphicsGLESVersion() const override { return m_gles_version; }
	bool getGraphicsPreservedSwap() const override;
	bool suspendGraphics() override;
	bool resumeGraphics() override;
	bool isGraphicsSuspended() const override { return m_graphics_suspended; }
	std::string getOSDAxis() const override;
	bool hasOSDPosition() const override { return true; }
	bool setOSDPosition(int left, int top, int width, int height) override;

	void flip();
	bool isInitialized() const { return m_egl_context != EGL_NO_CONTEXT; }
	int getGLESVersion() const { return m_gles_version; }
};

void gEGLDCSetAnimationCurrent(int animation);
void gEGLDCSetAnimationSpeed(int speed);
void gEGLDCSetToastAnimationSpeed(int speed);
void gEGLDCSetAnimationListbox(int animation);
void gEGLDCSetAnimationProfiles(int enabled, int dialog, int popup, int toast);
