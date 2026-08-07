#pragma once

#ifdef HAVE_GLES3
#include <GLES3/gl3.h>
#else
#include <GLES2/gl2.h>
#include <GLES2/gl2ext.h>
#endif
#include <stddef.h>

class gShader {
private:
	GLuint m_program_id;
	GLuint m_colored_program_id;
	GLuint m_vbo;
	size_t m_vbo_capacity_bytes;

	GLint m_projection_location;
	GLint m_color_location;
	GLint m_colored_projection_location;

	GLuint compileShader(GLenum type, const char* source);
	GLuint linkProgram(const char* vertex_source, const char* fragment_source, bool colored);
	void bindVAO();
	void unbindVAO();
	void bindColoredVAO();
	void unbindColoredVAO();
	void ensureVboCapacity(size_t bytes);

public:
	gShader();
	~gShader();

	bool init();
	void release();
	void bind();

	void setResolution(float width, float height);
	void drawRect(float x, float y, float width, float height, float r, float g, float b, float a);
	void drawRectBatch(const float* vertices, size_t vertex_count, float r, float g, float b, float a);
	void drawColoredRectBatch(const float* vertices, size_t vertex_count);
	void drawLine(float x1, float y1, float x2, float y2, float r, float g, float b, float a);
};
