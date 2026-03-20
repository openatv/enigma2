#include <lib/base/eerror.h>
#include <lib/base/init.h>
#include <lib/base/init_num.h>
#include <lib/gdi/egl/gegldc.h>
#include <lib/gdi/egl/gles_version.h>
#include <lib/gdi/fb.h>

#ifndef EGL_OPENGL_ES3_BIT_KHR
#define EGL_OPENGL_ES3_BIT_KHR 0x00000040
#endif

#ifdef HWDREAMONE
#include "amlogic/amlogic_window_provider.h"
eAutoInitPtr<gEGLDC> init_gEGLDC(eAutoInitNumbers::graphic - 1, "gEGLDC");
#endif

// ---------------------------------------------------------------------------
// tryInitEGL – attempts to create an EGL context for a specific GLES version.
// Returns true on success.  On failure the EGL state is left clean so that the
// caller can immediately try again with a different version.
// ---------------------------------------------------------------------------
bool gEGLDC::tryInitEGL(int version) {
	// 1. get the native display from our platform provider
	EGLNativeDisplayType native_display = m_window_provider->getNativeDisplay();

	m_egl_display = eglGetDisplay(native_display);
	if (m_egl_display == EGL_NO_DISPLAY) {
		eDebug("[gEGLDC] error: eglGetDisplay failed.");
		return false;
	}

	// 2. initialize EGL (only on first call; harmless to call again)
	EGLint major, minor;
	if (!eglInitialize(m_egl_display, &major, &minor)) {
		eDebug("[gEGLDC] error: eglInitialize failed.");
		return false;
	}
	eDebug("[gEGLDC] EGL version %d.%d initialised", major, minor);

	// 3. choose EGL config for the requested GLES version
	EGLint renderable_type = (version >= 3) ? EGL_OPENGL_ES3_BIT_KHR : EGL_OPENGL_ES2_BIT;

	const EGLint config_attribs[] = {
		EGL_SURFACE_TYPE, EGL_WINDOW_BIT, EGL_RENDERABLE_TYPE, renderable_type, EGL_RED_SIZE, 8, EGL_GREEN_SIZE, 8, EGL_BLUE_SIZE, 8, EGL_ALPHA_SIZE, 8, EGL_DEPTH_SIZE, 0, EGL_STENCIL_SIZE, 0,
		EGL_NONE};

	EGLint num_configs = 0;
	if (!eglChooseConfig(m_egl_display, config_attribs, &m_egl_config, 1, &num_configs) || num_configs == 0) {
		eDebug("[gEGLDC] no suitable EGL config found for GLES%d.", version);
		return false;
	}

	// 4. create the context
	const EGLint context_attribs[] = {EGL_CONTEXT_CLIENT_VERSION, version, EGL_NONE};

	m_egl_context = eglCreateContext(m_egl_display, m_egl_config, EGL_NO_CONTEXT, context_attribs);
	if (m_egl_context == EGL_NO_CONTEXT) {
		eDebug("[gEGLDC] eglCreateContext for GLES%d failed.", version);
		return false;
	}

	// 5. create the window surface
	EGLNativeWindowType native_window = m_window_provider->getNativeWindow();
	m_egl_surface = eglCreateWindowSurface(m_egl_display, m_egl_config, native_window, nullptr);
	if (m_egl_surface == EGL_NO_SURFACE) {
		eDebug("[gEGLDC] eglCreateWindowSurface failed. EGL error: 0x%x", eglGetError());
		eglDestroyContext(m_egl_display, m_egl_context);
		m_egl_context = EGL_NO_CONTEXT;
		return false;
	}

	// 6. make context current
	if (!eglMakeCurrent(m_egl_display, m_egl_surface, m_egl_surface, m_egl_context)) {
		eDebug("[gEGLDC] eglMakeCurrent failed.");
		eglDestroySurface(m_egl_display, m_egl_surface);
		eglDestroyContext(m_egl_display, m_egl_context);
		m_egl_surface = EGL_NO_SURFACE;
		m_egl_context = EGL_NO_CONTEXT;
		return false;
	}

	m_gles_version = version;
	return true;
}

// ---------------------------------------------------------------------------
// initEGL – cascades from GLES3 down to GLES2, then initialises shaders.
// ---------------------------------------------------------------------------
bool gEGLDC::initEGL() {
	// Try GLES3 first, fall back to GLES2
	if (!tryInitEGL(3)) {
		eDebug("[gEGLDC] GLES3 not available, falling back to GLES2.");
		if (!tryInitEGL(2)) {
			eDebug("[gEGLDC] error: neither GLES3 nor GLES2 could be initialised.");
			return false;
		}
	}

	// Publish the detected version so all shaders can query it
	gles::version = m_gles_version;
	eDebug("[gEGLDC] GLES%d context created.", m_gles_version);

	// 7. basic GL state
	glViewport(0, 0, m_width, m_height);
	eglSwapInterval(m_egl_display, 1);

	// 8. initialise shaders and resources
	if (!m_basic_shader.init()) {
		eFatal("[gEGLDC] failed to initialise basic shader!");
		return false;
	}
	if (!m_advanced_shader.init()) {
		eFatal("[gEGLDC] failed to initialise advanced shader!");
		return false;
	}
	if (!m_texture_shader.init()) {
		eFatal("[gEGLDC] failed to initialise texture shader!");
		return false;
	}
	if (!m_text_shader.init()) {
		eFatal("[gEGLDC] failed to initialise text shader!");
		return false;
	}
	if (!m_font_atlas.init()) {
		eFatal("[gEGLDC] failed to initialise font atlas!");
		return false;
	}

	// 9. upload projection matrices
	m_basic_shader.setResolution((float)m_width, (float)m_height);
	m_advanced_shader.setResolution((float)m_width, (float)m_height);
	m_texture_shader.setResolution((float)m_width, (float)m_height);
	m_text_shader.setResolution((float)m_width, (float)m_height);

	eDebug("[gEGLDC] GLES%d successfully initialised (%dx%d)", m_gles_version, m_width, m_height);
	return true;
}

void gEGLDC::setGlScissor(const eRect& rect) {
	int sx = rect.x();
	int sy = m_height - (rect.y() + rect.height());
	glScissor(sx, sy, rect.width(), rect.height());
}

void gEGLDC::executeFill(const gOpcode* op) {
	float r = m_foreground_color_rgb.r / 255.0f;
	float g = m_foreground_color_rgb.g / 255.0f;
	float b = m_foreground_color_rgb.b / 255.0f;
	float a = 1.0f - (m_foreground_color_rgb.a / 255.0f);

	eRect area = op->parm.fill->area;
	area.moveBy(m_current_offset);
	gRegion clip = m_current_clip & area;

	for (unsigned int i = 0; i < clip.rects.size(); ++i) {
		eRect r_area = clip.rects[i];
		m_basic_shader.drawRect(r_area.x(), r_area.y(), r_area.width(), r_area.height(), r, g, b, a);
	}
}

void gEGLDC::executeFillRegion(const gOpcode* op) {
	float r = m_foreground_color_rgb.r / 255.0f;
	float g = m_foreground_color_rgb.g / 255.0f;
	float b = m_foreground_color_rgb.b / 255.0f;
	float a = 1.0f - (m_foreground_color_rgb.a / 255.0f);

	gRegion region = op->parm.fillRegion->region;
	region.moveBy(m_current_offset);
	gRegion clip = m_current_clip & region;

	for (unsigned int i = 0; i < clip.rects.size(); ++i) {
		eRect r_area = clip.rects[i];
		m_basic_shader.drawRect(r_area.x(), r_area.y(), r_area.width(), r_area.height(), r, g, b, a);
	}
}

void gEGLDC::executeRectangle(const gOpcode* op) {
	if (m_current_clip.rects.empty())
		return;

	if (m_radius > 0 || m_gradient_colors.size() > 0) {
		glEnable(GL_BLEND);
		glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);
		glEnable(GL_SCISSOR_TEST);
		for (unsigned int i = 0; i < m_current_clip.rects.size(); ++i) {
			setGlScissor(m_current_clip.rects[i]);
			m_advanced_shader.drawAdvancedRect(op->parm.rectangle->area.x() + m_current_offset.x(), op->parm.rectangle->area.y() + m_current_offset.y(), op->parm.rectangle->area.width(),
											   op->parm.rectangle->area.height(), m_radius, m_radius_edges, m_gradient_colors, m_gradient_orientation, m_gradient_alphablend > 0,
											   1.0f - (m_background_color_rgb.a / 255.0f), m_background_color_rgb);
		}
		glDisable(GL_SCISSOR_TEST);
		glDisable(GL_BLEND);
	} else {
		float r = m_background_color_rgb.r / 255.0f;
		float g = m_background_color_rgb.g / 255.0f;
		float b = m_background_color_rgb.b / 255.0f;
		float a = 1.0f - (m_background_color_rgb.a / 255.0f);

		glEnable(GL_SCISSOR_TEST);
		for (unsigned int i = 0; i < m_current_clip.rects.size(); ++i) {
			setGlScissor(m_current_clip.rects[i]);
			m_basic_shader.drawRect(op->parm.rectangle->area.x() + m_current_offset.x(), op->parm.rectangle->area.y() + m_current_offset.y(), op->parm.rectangle->area.width(),
									op->parm.rectangle->area.height(), r, g, b, a);
		}
		glDisable(GL_SCISSOR_TEST);
	}
}

void gEGLDC::executeClear(const gOpcode* op) {
	float r = m_background_color_rgb.r / 255.0f;
	float g = m_background_color_rgb.g / 255.0f;
	float b = m_background_color_rgb.b / 255.0f;
	float a = 1.0f - (m_background_color_rgb.a / 255.0f);

	for (unsigned int i = 0; i < m_current_clip.rects.size(); ++i) {
		eRect area = m_current_clip.rects[i];
		m_basic_shader.drawRect(area.x(), area.y(), area.width(), area.height(), r, g, b, a);
	}
}

void gEGLDC::executeLine(const gOpcode* op) {
	float r = m_foreground_color_rgb.r / 255.0f;
	float g = m_foreground_color_rgb.g / 255.0f;
	float b = m_foreground_color_rgb.b / 255.0f;
	float a = 1.0f - (m_foreground_color_rgb.a / 255.0f);

	if (m_current_clip.rects.empty())
		return;

	glEnable(GL_SCISSOR_TEST);
	for (unsigned int i = 0; i < m_current_clip.rects.size(); ++i) {
		setGlScissor(m_current_clip.rects[i]);
		m_basic_shader.drawLine(op->parm.line->start.x() + m_current_offset.x(), op->parm.line->start.y() + m_current_offset.y(), op->parm.line->end.x() + m_current_offset.x(),
								op->parm.line->end.y() + m_current_offset.y(), r, g, b, a);
	}
	glDisable(GL_SCISSOR_TEST);
}

void gEGLDC::executeBlit(const gOpcode* opcode) {
	const gOpcode::para::pblit* op = opcode->parm.blit;
	if (!op->pixmap)
		return;

	GLuint tex_id = m_texture_manager.getTexture(op->pixmap);
	if (tex_id == 0)
		return;

	eRect pos = op->position;
	pos.moveBy(m_current_offset);

	gRegion clip;
	if (op->clip.valid()) {
		eRect c = op->clip;
		c.moveBy(m_current_offset);
		clip = gRegion(c) & m_current_clip;
	} else {
		clip = m_current_clip;
	}

	if (clip.rects.empty())
		return;

	bool enable_blend = (op->flags & (gPixmap::blitAlphaBlend | gPixmap::blitAlphaTest)) || (m_radius > 0);
	if (enable_blend) {
		glEnable(GL_BLEND);
		glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);
	}

	float x = pos.x();
	float y = pos.y();
	float width = pos.width() > 0 ? pos.width() : op->pixmap->size().width();
	float height = pos.height() > 0 ? pos.height() : op->pixmap->size().height();

	glEnable(GL_SCISSOR_TEST);
	for (unsigned int i = 0; i < clip.rects.size(); ++i) {
		setGlScissor(clip.rects[i]);
		m_texture_shader.drawTexture(x, y, width, height, tex_id, 1.0f, m_radius, m_radius_edges);
	}
	glDisable(GL_SCISSOR_TEST);

	if (enable_blend) {
		glDisable(GL_BLEND);
	}
}

void gEGLDC::renderGlyph(const ePoint& pos, gPixmap* glyph_mask, const gRGB& color) {
	if (!glyph_mask)
		return;

	glyph_uv uv;
	glyph_key_t key = reinterpret_cast<glyph_key_t>(glyph_mask->surface->data);

	if (!m_font_atlas.getGlyph(key, uv)) {
		// Flush the current batch before uploading a new glyph to the atlas.
		flushTextBatch();

		int w = glyph_mask->size().width();
		int h = glyph_mask->size().height();
		uint8_t* data = (uint8_t*)glyph_mask->surface->data;
		m_font_atlas.addGlyph(key, w, h, data, uv);
	}

	float r = color.r / 255.0f;
	float g = color.g / 255.0f;
	float b = color.b / 255.0f;
	float a = 1.0f - (color.a / 255.0f);

	float x = pos.x() + m_current_offset.x();
	float y = pos.y() + m_current_offset.y();
	float w = (float)uv.width;
	float h = (float)uv.height;

	// 6 vertices × 8 floats: x, y, u, v, r, g, b, a
	float vertices[48] = {x,	 y, uv.u0, uv.v0, r, g, b, a, x, y + h, uv.u0, uv.v1, r, g, b, a, x + w, y,		uv.u1, uv.v0, r, g, b, a,
						  x + w, y, uv.u1, uv.v0, r, g, b, a, x, y + h, uv.u0, uv.v1, r, g, b, a, x + w, y + h, uv.u1, uv.v1, r, g, b, a};

	m_text_batch_buffer.insert(m_text_batch_buffer.end(), vertices, vertices + 48);

	if (m_text_batch_buffer.size() >= MAX_BATCH_GLYPHS * 48) {
		flushTextBatch();
	}
}

void gEGLDC::flushTextBatch() {
	if (m_text_batch_buffer.empty())
		return;
	if (m_current_clip.rects.empty()) {
		m_text_batch_buffer.clear();
		return;
	}

	glEnable(GL_BLEND);
	glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);

	m_text_shader.bind();

	// Bind the atlas pixmap
	gPixmap* atlas_pix = m_font_atlas.getPixmap();
	GLuint tex_id = m_texture_manager.getTexture(atlas_pix);
	glActiveTexture(GL_TEXTURE0);
	glBindTexture(GL_TEXTURE_2D, tex_id);

	if (m_font_atlas.isDirty()) {
		eRect dirty = m_font_atlas.getDirtyRect();

		// GLES 2.0 does not support GL_UNPACK_ROW_LENGTH, so we cannot easily upload
		// an arbitrary sub-rectangle. Instead, we upload full contiguous scanlines
		// for the dirty Y range.
		int start_y = dirty.top();
		int height = dirty.height();
		int stride = atlas_pix->size().width();

		const uint8_t* data = (const uint8_t*)atlas_pix->surface->data;
		data += (start_y * stride);

		glPixelStorei(GL_UNPACK_ALIGNMENT, 1);
		GLenum src_fmt = gles::isGLES3() ? GL_RED : GL_LUMINANCE;
		glTexSubImage2D(GL_TEXTURE_2D, 0, 0, start_y, stride, height, src_fmt, GL_UNSIGNED_BYTE, data);
		glPixelStorei(GL_UNPACK_ALIGNMENT, 4);

		m_font_atlas.clearDirty();
	}

	glBufferSubData(GL_ARRAY_BUFFER, 0, m_text_batch_buffer.size() * sizeof(float), m_text_batch_buffer.data());

	int vertex_count = m_text_batch_buffer.size() / 8; // 8 floats per vertex

	glEnable(GL_SCISSOR_TEST);
	for (unsigned int i = 0; i < m_current_clip.rects.size(); ++i) {
		setGlScissor(m_current_clip.rects[i]);
		glDrawArrays(GL_TRIANGLES, 0, vertex_count);
	}
	glDisable(GL_SCISSOR_TEST);

	glDisable(GL_BLEND);

	m_text_batch_buffer.clear();
}

void gEGLDC::exec(const gOpcode* opcode) {
	if (!isInitialized())
		return;

	m_texture_manager.processDeletions();

	switch (opcode->opcode) {
		case gOpcode::fill:
			executeFill(opcode);
			break;

		case gOpcode::fillRegion:
			executeFillRegion(opcode);
			break;

		case gOpcode::rectangle:
			executeRectangle(opcode);
			break;

		case gOpcode::line:
			executeLine(opcode);
			break;

		case gOpcode::blit:
			executeBlit(opcode);
			break;

		case gOpcode::clear:
			executeClear(opcode);
			gDC::exec(opcode);
			break;

		case gOpcode::flush:
		case gOpcode::flip:
			flushTextBatch();
			gDC::exec(opcode);
			break;

		default:
			gDC::exec(opcode);
			flushTextBatch();
			break;
	}
}

gEGLDC::gEGLDC(INativeWindowProvider* window_provider, int width, int height) : gMainDC() {
	int xres = width, yres = height, bpp = 32;

	if (!window_provider) {
		if (fbClass::getInstance()) {
			fbClass::getInstance()->getMode(xres, yres, bpp);
		}
		width = xres;
		height = yres;
#ifdef HWDREAMONE
		window_provider = new AmlogicWindowProvider(width, height);
#endif
	}

	m_window_provider = window_provider;
	m_width = width;
	m_height = height;
	m_gles_version = 0;
	m_egl_display = EGL_NO_DISPLAY;
	m_egl_surface = EGL_NO_SURFACE;
	m_egl_context = EGL_NO_CONTEXT;

	m_pixmap = new gPixmap(eSize(width, height), 32);
}

gEGLDC::~gEGLDC() {
	cleanupEGL();
}

void gEGLDC::cleanupEGL() {
	if (m_egl_display != EGL_NO_DISPLAY) {
		eglMakeCurrent(m_egl_display, EGL_NO_SURFACE, EGL_NO_SURFACE, EGL_NO_CONTEXT);
		if (m_egl_context != EGL_NO_CONTEXT) {
			eglDestroyContext(m_egl_display, m_egl_context);
		}
		if (m_egl_surface != EGL_NO_SURFACE) {
			eglDestroySurface(m_egl_display, m_egl_surface);
		}
		eglTerminate(m_egl_display);
	}
	m_egl_display = EGL_NO_DISPLAY;
	m_egl_surface = EGL_NO_SURFACE;
	m_egl_context = EGL_NO_CONTEXT;
	m_gles_version = 0;
	gles::version = 0;
}

void gEGLDC::setResolution(int xres, int yres, int bpp) {
	if (m_width == xres && m_height == yres)
		return;

	m_width = xres;
	m_height = yres;
	m_pixmap = new gPixmap(eSize(xres, yres), bpp);

	if (isInitialized()) {
		m_basic_shader.setResolution((float)m_width, (float)m_height);
		m_texture_shader.setResolution((float)m_width, (float)m_height);
		m_text_shader.setResolution((float)m_width, (float)m_height);
	}
}

void gEGLDC::flip() {
	if (isInitialized() && m_egl_display != EGL_NO_DISPLAY && m_egl_surface != EGL_NO_SURFACE) {
		eglSwapBuffers(m_egl_display, m_egl_surface);
	}
}