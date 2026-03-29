#pragma once

#ifdef HAVE_GLES3
#include <GLES3/gl3.h>
#else
#include <GLES2/gl2.h>
#include <GLES2/gl2ext.h>
#endif

class gTextureShader {
private:
	GLuint m_program_id;
#if defined(HAVE_GLES3)
	GLuint m_vao; // GLES3 only; 0 in GLES2 mode
#endif
	GLuint m_vbo;

	GLint m_projection_location;
	GLint m_texture_location;
	GLint m_alpha_location;

	GLint m_rect_size_location;
	GLint m_radius_location;
	GLint m_edges_location;

	// ES2-only per-corner radius uniforms (replaces integer bitmask u_edges)
	GLint m_edges_tl_location;
	GLint m_edges_tr_location;
	GLint m_edges_bl_location;
	GLint m_edges_br_location;

	GLuint compileShader(GLenum type, const char* source);
	void bindVAO();
	void unbindVAO();

public:
	gTextureShader();
	~gTextureShader();

	bool init();
	void bind();

	void setResolution(float width, float height);
	void drawTexture(float x, float y, float width, float height, GLuint texture_id, float global_alpha = 1.0f, float radius = 0.0f, uint8_t edges = 0);
};