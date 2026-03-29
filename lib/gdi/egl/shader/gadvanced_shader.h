#pragma once

#ifdef HAVE_GLES3
#include <GLES3/gl3.h>
#else
#include <GLES2/gl2.h>
#include <GLES2/gl2ext.h>
#endif
#include <lib/gdi/gpixmap.h>
#include <vector>

class gAdvancedShader {
private:
	GLuint m_program_id;
#if defined(HAVE_GLES3)
	GLuint m_vao; // GLES3 only; 0 in GLES2 mode
#endif
	GLuint m_vbo;

	GLint m_projection_location;
	GLint m_rect_size_location;
	GLint m_radius_location;
	GLint m_edges_location;
	GLint m_solid_color_location;
	GLint m_alphablend_location;

	// Gradient uniforms
	GLint m_gradient_colors_location;
	GLint m_gradient_stops_location; // array of floats
	GLint m_num_stops_location;
	GLint m_gradient_orientation_location;

	// ES2-only per-corner radius uniforms (replaces integer bitmask u_edges)
	// GLSL ES 1.00 does not support bitwise operations on integer uniforms.
	GLint m_edges_tl_location; // u_r_tl
	GLint m_edges_tr_location; // u_r_tr
	GLint m_edges_bl_location; // u_r_bl
	GLint m_edges_br_location; // u_r_br

	GLuint compileShader(GLenum type, const char* source);
	void bindVAO();
	void unbindVAO();

public:
	gAdvancedShader();
	~gAdvancedShader();

	bool init();
	void bind();

	void setResolution(float width, float height);

	void drawAdvancedRect(float x, float y, float width, float height, int radius, uint8_t edges, const std::vector<gRGB>& gradient_colors, uint8_t orientation, bool alphablend, float alpha,
						  const gRGB& solid_color);
};
