#pragma once
#ifdef HAVE_GLES3
#include <GLES3/gl3.h>
#else
#include <GLES2/gl2.h>
#include <GLES2/gl2ext.h>
#endif
#include <lib/gdi/gfont_atlas.h>

class gTextShader {
private:
	GLuint m_program_id;
#if defined(HAVE_GLES3)
	GLuint m_vao; // GLES3 only; 0 in GLES2 mode
#endif
	GLuint m_vbo;

	GLint m_projection_location;
	GLint m_color_location;
	GLint m_texture_location;

	GLuint compileShader(GLenum type, const char* source);
	void bindVAO();
	void unbindVAO();

public:
	gTextShader();
	~gTextShader();

	bool init();
	void bind();

	void setResolution(float width, float height);
	void drawGlyph(float x, float y, const glyph_uv& uv, float r, float g, float b, float a);
};