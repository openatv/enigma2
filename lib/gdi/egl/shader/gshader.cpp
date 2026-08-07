#include <lib/base/eerror.h>
#include <lib/gdi/egl/gles_version.h>
#include <lib/gdi/egl/shader/gshader.h>
#include <vector>

// ---------------------------------------------------------------------------
// GLES 3.0 shader sources
// Uses layout(location=N), out vec4 frag_color
// ---------------------------------------------------------------------------
#if defined(HAVE_GLES3)
static const char* vertex_shader_es3 = R"(#version 300 es
    layout(location = 0) in vec2 position;
    uniform mat4 u_projection;
    void main() {
        gl_Position = u_projection * vec4(position, 0.0, 1.0);
    }
)";

static const char* fragment_shader_es3 = R"(#version 300 es
    precision mediump float;
    uniform vec4 u_color;
    out vec4 frag_color;
    void main() {
        frag_color = u_color;
    }
)";

static const char* colored_vertex_shader_es3 = R"(#version 300 es
    layout(location = 0) in vec2 position;
    layout(location = 1) in vec4 color;
    uniform mat4 u_projection;
    out vec4 v_color;
    void main() {
        v_color = color;
        gl_Position = u_projection * vec4(position, 0.0, 1.0);
    }
)";

static const char* colored_fragment_shader_es3 = R"(#version 300 es
    precision mediump float;
    in vec4 v_color;
    out vec4 frag_color;
    void main() {
        frag_color = v_color;
    }
)";
#endif

// ---------------------------------------------------------------------------
// GLES 2.0 shader sources
// Uses attribute/varying, gl_FragColor
// ---------------------------------------------------------------------------
static const char* vertex_shader_es2 = R"(#version 100
    attribute vec2 position;
    uniform mat4 u_projection;
    void main() {
        gl_Position = u_projection * vec4(position, 0.0, 1.0);
    }
)";

static const char* fragment_shader_es2 = R"(#version 100
    precision mediump float;
    uniform vec4 u_color;
    void main() {
        gl_FragColor = u_color;
    }
)";

static const char* colored_vertex_shader_es2 = R"(#version 100
    attribute vec2 position;
    attribute vec4 color;
    uniform mat4 u_projection;
    varying vec4 v_color;
    void main() {
        v_color = color;
        gl_Position = u_projection * vec4(position, 0.0, 1.0);
    }
)";

static const char* colored_fragment_shader_es2 = R"(#version 100
    precision mediump float;
    varying vec4 v_color;
    void main() {
        gl_FragColor = v_color;
    }
)";

// ---------------------------------------------------------------------------

gShader::gShader() : m_program_id(0), m_colored_program_id(0), m_vbo(0), m_vbo_capacity_bytes(0) {}

gShader::~gShader() {
	release();
}

void gShader::release() {
	if (m_vbo) {
		glDeleteBuffers(1, &m_vbo);
		m_vbo = 0;
	}
	if (m_program_id) {
		glDeleteProgram(m_program_id);
		m_program_id = 0;
	}
	if (m_colored_program_id) {
		glDeleteProgram(m_colored_program_id);
		m_colored_program_id = 0;
	}
	m_vbo_capacity_bytes = 0;
}

GLuint gShader::compileShader(GLenum type, const char* source) {
	GLuint shader = glCreateShader(type);
	glShaderSource(shader, 1, &source, nullptr);
	glCompileShader(shader);

	GLint success;
	glGetShaderiv(shader, GL_COMPILE_STATUS, &success);
	if (!success) {
		GLchar info_log[512];
		glGetShaderInfoLog(shader, 512, nullptr, info_log);
		eDebug("[gShader] shader compilation failed: %s", info_log);
		return 0;
	}
	return shader;
}

GLuint gShader::linkProgram(const char* vertex_source, const char* fragment_source, bool colored) {
	GLuint vertex_shader = compileShader(GL_VERTEX_SHADER, vertex_source);
	GLuint fragment_shader = compileShader(GL_FRAGMENT_SHADER, fragment_source);

	if (!vertex_shader || !fragment_shader)
		return 0;

	GLuint program = glCreateProgram();

	// For GLES2 we must bind attribute locations before linking
	if (!gles::isGLES3()) {
		glBindAttribLocation(program, 0, "position");
		if (colored)
			glBindAttribLocation(program, 1, "color");
	}

	glAttachShader(program, vertex_shader);
	glAttachShader(program, fragment_shader);
	glLinkProgram(program);

	glDeleteShader(vertex_shader);
	glDeleteShader(fragment_shader);

	GLint success;
	glGetProgramiv(program, GL_LINK_STATUS, &success);
	if (!success) {
		GLchar info_log[512];
		glGetProgramInfoLog(program, 512, nullptr, info_log);
		eDebug("[gShader] shader link failed: %s", info_log);
		glDeleteProgram(program);
		return 0;
	}
	return program;
}

bool gShader::init() {
#if defined(HAVE_GLES3)
	const char* vs_src = gles::isGLES3() ? vertex_shader_es3 : vertex_shader_es2;
	const char* fs_src = gles::isGLES3() ? fragment_shader_es3 : fragment_shader_es2;
	const char* colored_vs_src = gles::isGLES3() ? colored_vertex_shader_es3 : colored_vertex_shader_es2;
	const char* colored_fs_src = gles::isGLES3() ? colored_fragment_shader_es3 : colored_fragment_shader_es2;
#else
	const char* vs_src = vertex_shader_es2;
	const char* fs_src = fragment_shader_es2;
	const char* colored_vs_src = colored_vertex_shader_es2;
	const char* colored_fs_src = colored_fragment_shader_es2;
#endif

	m_program_id = linkProgram(vs_src, fs_src, false);
	m_colored_program_id = linkProgram(colored_vs_src, colored_fs_src, true);
	if (!m_program_id || !m_colored_program_id)
		return false;

	m_projection_location = glGetUniformLocation(m_program_id, "u_projection");
	m_color_location = glGetUniformLocation(m_program_id, "u_color");
	m_colored_projection_location = glGetUniformLocation(m_colored_program_id, "u_projection");

	glGenBuffers(1, &m_vbo);
	glBindBuffer(GL_ARRAY_BUFFER, m_vbo);
	m_vbo_capacity_bytes = sizeof(float) * 6 * 2;
	glBufferData(GL_ARRAY_BUFFER, m_vbo_capacity_bytes, nullptr, GL_DYNAMIC_DRAW);

	glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, 2 * sizeof(float), (void*)0);
	glEnableVertexAttribArray(0);

	glBindBuffer(GL_ARRAY_BUFFER, 0);

	return true;
}

void gShader::bind() {
	glUseProgram(m_program_id);
}

void gShader::bindVAO() {
	glBindBuffer(GL_ARRAY_BUFFER, m_vbo);
	glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, 2 * sizeof(float), (void*)0);
	glEnableVertexAttribArray(0);
}

void gShader::unbindVAO() {
	glDisableVertexAttribArray(0);
}

void gShader::bindColoredVAO() {
	glBindBuffer(GL_ARRAY_BUFFER, m_vbo);
	glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, 6 * sizeof(float), (void*)0);
	glEnableVertexAttribArray(0);
	glVertexAttribPointer(1, 4, GL_FLOAT, GL_FALSE, 6 * sizeof(float), (void*)(2 * sizeof(float)));
	glEnableVertexAttribArray(1);
}

void gShader::unbindColoredVAO() {
	glDisableVertexAttribArray(1);
	glDisableVertexAttribArray(0);
}

void gShader::ensureVboCapacity(size_t bytes) {
	if (bytes <= m_vbo_capacity_bytes)
		return;

	size_t new_capacity = m_vbo_capacity_bytes ? m_vbo_capacity_bytes : sizeof(float) * 6 * 2;
	while (new_capacity < bytes)
		new_capacity *= 2;

	glBufferData(GL_ARRAY_BUFFER, new_capacity, nullptr, GL_DYNAMIC_DRAW);
	m_vbo_capacity_bytes = new_capacity;
}

void gShader::setResolution(float width, float height) {
	float ortho[16] = {2.0f / width, 0.0f, 0.0f, 0.0f, 0.0f, -2.0f / height, 0.0f, 0.0f, 0.0f, 0.0f, -1.0f, 0.0f, -1.0f, 1.0f, 0.0f, 1.0f};
	bind();
	glUniformMatrix4fv(m_projection_location, 1, GL_FALSE, ortho);
	glUseProgram(m_colored_program_id);
	glUniformMatrix4fv(m_colored_projection_location, 1, GL_FALSE, ortho);
}

void gShader::drawRect(float x, float y, float width, float height, float r, float g, float b, float a) {
	bind();
	glUniform4f(m_color_location, r, g, b, a);

	float vertices[12] = {x, y, x, y + height, x + width, y, x + width, y, x, y + height, x + width, y + height};

	bindVAO();
	glBindBuffer(GL_ARRAY_BUFFER, m_vbo);
	glBufferSubData(GL_ARRAY_BUFFER, 0, sizeof(vertices), vertices);
	glDrawArrays(GL_TRIANGLES, 0, 6);
	unbindVAO();
}

void gShader::drawRectBatch(const float* vertices, size_t vertex_count, float r, float g, float b, float a) {
	if (!vertices || !vertex_count)
		return;

	bind();
	glUniform4f(m_color_location, r, g, b, a);

	bindVAO();
	glBindBuffer(GL_ARRAY_BUFFER, m_vbo);
	const size_t bytes = vertex_count * 2 * sizeof(float);
	ensureVboCapacity(bytes);
	glBufferSubData(GL_ARRAY_BUFFER, 0, bytes, vertices);
	glDrawArrays(GL_TRIANGLES, 0, static_cast<GLsizei>(vertex_count));
	unbindVAO();
}

void gShader::drawColoredRectBatch(const float* vertices, size_t vertex_count) {
	if (!vertices || !vertex_count)
		return;

	glUseProgram(m_colored_program_id);

	bindColoredVAO();
	glBindBuffer(GL_ARRAY_BUFFER, m_vbo);
	const size_t bytes = vertex_count * 6 * sizeof(float);
	ensureVboCapacity(bytes);
	glBufferSubData(GL_ARRAY_BUFFER, 0, bytes, vertices);
	glDrawArrays(GL_TRIANGLES, 0, static_cast<GLsizei>(vertex_count));
	unbindColoredVAO();
}

void gShader::drawLine(float x1, float y1, float x2, float y2, float r, float g, float b, float a) {
	bind();
	glUniform4f(m_color_location, r, g, b, a);

	float vertices[4] = {x1, y1, x2, y2};

	bindVAO();
	glBindBuffer(GL_ARRAY_BUFFER, m_vbo);
	glBufferSubData(GL_ARRAY_BUFFER, 0, sizeof(vertices), vertices);
	glDrawArrays(GL_LINES, 0, 2);
	unbindVAO();
}
