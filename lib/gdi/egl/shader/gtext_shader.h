#pragma once
#ifdef HAVE_GLES3
#include <GLES3/gl3.h>
#else
#include <GLES2/gl2.h>
#include <GLES2/gl2ext.h>
#endif
#include <lib/gdi/gfont_atlas.h>
#include <stddef.h>

class gTextShader {
private:
	GLuint m_program_id;
	GLuint m_vbo;
	size_t m_vbo_capacity_bytes;

	GLint m_projection_location;
	GLint m_color_location;
	GLint m_texture_location;

	GLuint compileShader(GLenum type, const char* source);
	void bindVAO();
	void unbindVAO();
	void ensureVboCapacity(size_t bytes);

public:
	gTextShader();
	~gTextShader();

	bool init();
	void release();
	void bind();

	void setResolution(float width, float height);
	void drawGlyph(float x, float y, const glyph_uv& uv, float r, float g, float b, float a);
	void drawBatch(const float* vertices, size_t float_count);
};
