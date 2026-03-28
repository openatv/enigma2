#include <lib/base/eerror.h>
#include <lib/gdi/egl/gles_version.h>
#include <lib/gdi/egl/shader/gshader.h>
#include <vector>

// ---------------------------------------------------------------------------
// GLES 3.0 shader sources
// Uses layout(location=N), out vec4 frag_color
// ---------------------------------------------------------------------------
#if defined(HAVE_GLES3)
static const char* vertex_shader_es3 = R"(
    #version 300 es
    layout(location = 0) in vec2 position;
    uniform mat4 u_projection;
    void main() {
        gl_Position = u_projection * vec4(position, 0.0, 1.0);
    }
)";

static const char* fragment_shader_es3 = R"(
    #version 300 es
    precision mediump float;
    uniform vec4 u_color;
    out vec4 frag_color;
    void main() {
        frag_color = u_color;
    }
)";
#endif

// ---------------------------------------------------------------------------
// GLES 2.0 shader sources
// Uses attribute/varying, gl_FragColor
// ---------------------------------------------------------------------------
static const char* vertex_shader_es2 = R"(
    #version 100
    attribute vec2 position;
    uniform mat4 u_projection;
    void main() {
        gl_Position = u_projection * vec4(position, 0.0, 1.0);
    }
)";

static const char* fragment_shader_es2 = R"(
    #version 100
    precision mediump float;
    uniform vec4 u_color;
    void main() {
        gl_FragColor = u_color;
    }
)";

// ---------------------------------------------------------------------------

#if defined(HAVE_GLES3)
gShader::gShader() : m_program_id(0), m_vao(0), m_vbo(0) {}
#else
gShader::gShader() : m_program_id(0), m_vbo(0) {}
#endif

gShader::~gShader() {
#if defined(HAVE_GLES3)
	if (gles::isGLES3() && m_vao)
		glDeleteVertexArrays(1, &m_vao);
#endif
	if (m_vbo)
		glDeleteBuffers(1, &m_vbo);
	if (m_program_id)
		glDeleteProgram(m_program_id);
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

bool gShader::init() {
#if defined(HAVE_GLES3)
	const char* vs_src = gles::isGLES3() ? vertex_shader_es3 : vertex_shader_es2;
	const char* fs_src = gles::isGLES3() ? fragment_shader_es3 : fragment_shader_es2;
#else
	const char* vs_src = vertex_shader_es2;
	const char* fs_src = fragment_shader_es2;
#endif

	GLuint vertex_shader = compileShader(GL_VERTEX_SHADER, vs_src);
	GLuint fragment_shader = compileShader(GL_FRAGMENT_SHADER, fs_src);

	if (!vertex_shader || !fragment_shader)
		return false;

	m_program_id = glCreateProgram();

	// For GLES2 we must bind attribute locations before linking
	if (!gles::isGLES3()) {
		glBindAttribLocation(m_program_id, 0, "position");
	}

	glAttachShader(m_program_id, vertex_shader);
	glAttachShader(m_program_id, fragment_shader);
	glLinkProgram(m_program_id);

	glDeleteShader(vertex_shader);
	glDeleteShader(fragment_shader);

	m_projection_location = glGetUniformLocation(m_program_id, "u_projection");
	m_color_location = glGetUniformLocation(m_program_id, "u_color");

	// VAO is a GLES3 core feature; in GLES2 we re-specify attribs per draw call
#if defined(HAVE_GLES3)
	if (gles::isGLES3()) {
		glGenVertexArrays(1, &m_vao);
		glBindVertexArray(m_vao);
	}
#endif

	glGenBuffers(1, &m_vbo);
	glBindBuffer(GL_ARRAY_BUFFER, m_vbo);
	glBufferData(GL_ARRAY_BUFFER, sizeof(float) * 6 * 2, nullptr, GL_DYNAMIC_DRAW);

	glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, 2 * sizeof(float), (void*)0);
	glEnableVertexAttribArray(0);

	glBindBuffer(GL_ARRAY_BUFFER, 0);
#if defined(HAVE_GLES3)
	if (gles::isGLES3())
		glBindVertexArray(0);
#endif

	return true;
}

void gShader::bind() {
	glUseProgram(m_program_id);
}

void gShader::bindVAO() {
#if defined(HAVE_GLES3)
	if (gles::isGLES3()) {
		glBindVertexArray(m_vao);
	} else
#endif
	{
		// Re-specify vertex layout each draw call (no VAO support in core ES2)
		glBindBuffer(GL_ARRAY_BUFFER, m_vbo);
		glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, 2 * sizeof(float), (void*)0);
		glEnableVertexAttribArray(0);
	}
}

void gShader::unbindVAO() {
#if defined(HAVE_GLES3)
	if (gles::isGLES3()) {
		glBindVertexArray(0);
	} else
#endif
	{
		glDisableVertexAttribArray(0);
	}
}

void gShader::setResolution(float width, float height) {
	bind();
	float ortho[16] = {2.0f / width, 0.0f, 0.0f, 0.0f, 0.0f, -2.0f / height, 0.0f, 0.0f, 0.0f, 0.0f, -1.0f, 0.0f, -1.0f, 1.0f, 0.0f, 1.0f};
	glUniformMatrix4fv(m_projection_location, 1, GL_FALSE, ortho);
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