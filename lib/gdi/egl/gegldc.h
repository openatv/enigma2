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

class gEGLDCAutoInit;

class gEGLDC : public gMainDC {
private:
	INativeWindowProvider* m_window_provider;
	EGLDisplay m_egl_display;
	EGLConfig m_egl_config;
	EGLSurface m_egl_surface;
	EGLContext m_egl_context;

	int m_width;
	int m_height;
	int m_gles_version; // 2 or 3
	GLint m_max_texture_size;

	gShader m_basic_shader;
	gAdvancedShader m_advanced_shader;
	gTextureShader m_texture_shader;
	gTextShader m_text_shader;

	gFontAtlas m_font_atlas;
	gTextureManager m_texture_manager;

	std::vector<float> m_text_batch_buffer;
	const size_t MAX_BATCH_GLYPHS = 1024;

	bool tryInitEGL(int version);
	void cleanupEGL();

	// dedicated opcode handlers
	void executeFill(const gOpcode* op);
	void executeFillRegion(const gOpcode* op);
	void executeRectangle(const gOpcode* op);
	void executeLine(const gOpcode* op);
	void executeBlit(const gOpcode* op);
	void executeDrawGlyph(const gOpcode* op);
	void executeClear(const gOpcode* op);
	void flushTextBatch();
	void setGlScissor(const eRect& rect);

	bool isHardwareAccelerated() const override { return true; }
	void renderGlyph(const ePoint& pos, gPixmap* glyph_mask, const gRGB& color) override;

public:
	bool initEGL();
	gEGLDC(INativeWindowProvider* window_provider = nullptr, int width = 1280, int height = 720);
	virtual ~gEGLDC();

	virtual void setResolution(int xres, int yres, int bpp = 32) override;
	virtual void exec(const gOpcode* opcode);

	void flip();
	bool isInitialized() const { return m_egl_context != EGL_NO_CONTEXT; }
	int getGLESVersion() const { return m_gles_version; }
};