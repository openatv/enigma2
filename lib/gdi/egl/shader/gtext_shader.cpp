#include <lib/gdi/egl/shader/gtext_shader.h>
#include <lib/gdi/egl/gles_version.h>
#include <lib/base/eerror.h>

// ---------------------------------------------------------------------------
// GLES 3.0 shader sources
// Two vertex attributes: pos_uv (location 0) and color (location 1)
// ---------------------------------------------------------------------------
#if defined(HAVE_GLES3)
static const char *vertex_shader_es3 = R"(#version 300 es
    layout(location = 0) in vec4 pos_uv;
    layout(location = 1) in vec4 color;
    
    uniform mat4 u_projection;
    
    out vec2 v_uv;
    out vec4 v_color;
    
    void main() {
        gl_Position = u_projection * vec4(pos_uv.xy, 0.0, 1.0);
        v_uv    = pos_uv.zw;
        v_color = color;
    }
)";

static const char *fragment_shader_es3 = R"(#version 300 es
    precision mediump float;
    
    in vec2 v_uv;
    in vec4 v_color;
    
    uniform sampler2D u_texture;
    out vec4 frag_color;
    
    void main() {
        float mask = texture(u_texture, v_uv).r;
        frag_color = vec4(v_color.rgb, v_color.a * mask);
    }
)";
#endif

// ---------------------------------------------------------------------------
// GLES 2.0 shader sources
// Note: texture().r is replaced with texture2D().r; with GL_LUMINANCE the
// luminance value is replicated into r, g and b, so .r still returns the mask.
// ---------------------------------------------------------------------------
static const char *vertex_shader_es2 = R"(#version 100
    attribute vec4 pos_uv;
    attribute vec4 color;
    
    uniform mat4 u_projection;
    
    varying vec2 v_uv;
    varying vec4 v_color;
    
    void main() {
        gl_Position = u_projection * vec4(pos_uv.xy, 0.0, 1.0);
        v_uv    = pos_uv.zw;
        v_color = color;
    }
)";

static const char *fragment_shader_es2 = R"(#version 100
    precision mediump float;
    
    varying vec2 v_uv;
    varying vec4 v_color;
    
    uniform sampler2D u_texture;
    
    void main() {
        // In GL_LUMINANCE textures the single channel is replicated into r/g/b
        float mask = texture2D(u_texture, v_uv).r;
        gl_FragColor = vec4(v_color.rgb, v_color.a * mask);
    }
)";

// ---------------------------------------------------------------------------

gTextShader::gTextShader() : m_program_id(0), m_vbo(0), m_vbo_capacity_bytes(0)
{
}

gTextShader::~gTextShader()
{
	release();
}

void gTextShader::release()
{
	if (m_vbo) {
		glDeleteBuffers(1, &m_vbo);
		m_vbo = 0;
	}
	if (m_program_id) {
		glDeleteProgram(m_program_id);
		m_program_id = 0;
	}
	m_vbo_capacity_bytes = 0;
}

GLuint gTextShader::compileShader(GLenum type, const char *source)
{
    GLuint shader = glCreateShader(type);
    glShaderSource(shader, 1, &source, nullptr);
    glCompileShader(shader);

    GLint success;
    glGetShaderiv(shader, GL_COMPILE_STATUS, &success);
    if (!success) {
        GLchar info_log[512];
        glGetShaderInfoLog(shader, 512, nullptr, info_log);
        eDebug("[gTextShader] shader compilation failed: %s", info_log);
        return 0;
    }
    return shader;
}

bool gTextShader::init()
{
    const size_t max_glyphs = 1024;
    const size_t floats_per_vertex = 8;  // x, y, u, v, r, g, b, a
    const size_t vertices_per_glyph = 6;
    const size_t buffer_size = max_glyphs * vertices_per_glyph * floats_per_vertex * sizeof(float);

#if defined(HAVE_GLES3)
    const char *vs_src = gles::isGLES3() ? vertex_shader_es3   : vertex_shader_es2;
    const char *fs_src = gles::isGLES3() ? fragment_shader_es3 : fragment_shader_es2;
#else
    const char *vs_src = vertex_shader_es2;
    const char *fs_src = fragment_shader_es2;
#endif

    GLuint vertex_shader   = compileShader(GL_VERTEX_SHADER,   vs_src);
    GLuint fragment_shader = compileShader(GL_FRAGMENT_SHADER, fs_src);

    if (!vertex_shader || !fragment_shader) return false;

    m_program_id = glCreateProgram();

    if (!gles::isGLES3()) {
        glBindAttribLocation(m_program_id, 0, "pos_uv");
        glBindAttribLocation(m_program_id, 1, "color");
    }

    glAttachShader(m_program_id, vertex_shader);
    glAttachShader(m_program_id, fragment_shader);
    glLinkProgram(m_program_id);

    glDeleteShader(vertex_shader);
    glDeleteShader(fragment_shader);

    m_projection_location = glGetUniformLocation(m_program_id, "u_projection");
    m_color_location      = glGetUniformLocation(m_program_id, "u_text_color");
    m_texture_location    = glGetUniformLocation(m_program_id, "u_texture");

    glGenBuffers(1, &m_vbo);
    glBindBuffer(GL_ARRAY_BUFFER, m_vbo);
    m_vbo_capacity_bytes = buffer_size;
    glBufferData(GL_ARRAY_BUFFER, m_vbo_capacity_bytes, nullptr, GL_DYNAMIC_DRAW);

    // Attribute 0: pos_uv (4 floats)
    glVertexAttribPointer(0, 4, GL_FLOAT, GL_FALSE, floats_per_vertex * sizeof(float), (void*)0);
    glEnableVertexAttribArray(0);

    // Attribute 1: color (4 floats)
    glVertexAttribPointer(1, 4, GL_FLOAT, GL_FALSE, floats_per_vertex * sizeof(float), (void*)(4 * sizeof(float)));
    glEnableVertexAttribArray(1);
    
    glBindBuffer(GL_ARRAY_BUFFER, 0);

    return true;
}

void gTextShader::bind()
{
    glUseProgram(m_program_id);
}

void gTextShader::bindVAO()
{
    int floats_per_vertex = 8;
    glBindBuffer(GL_ARRAY_BUFFER, m_vbo);
    glVertexAttribPointer(0, 4, GL_FLOAT, GL_FALSE, floats_per_vertex * sizeof(float), (void*)0);
    glEnableVertexAttribArray(0);
    glVertexAttribPointer(1, 4, GL_FLOAT, GL_FALSE, floats_per_vertex * sizeof(float), (void*)(4 * sizeof(float)));
    glEnableVertexAttribArray(1);
}

void gTextShader::unbindVAO()
{
    glDisableVertexAttribArray(0);
    glDisableVertexAttribArray(1);
}

void gTextShader::ensureVboCapacity(size_t bytes)
{
    if (bytes <= m_vbo_capacity_bytes)
        return;

    size_t new_capacity = m_vbo_capacity_bytes ? m_vbo_capacity_bytes : sizeof(float) * 6 * 8;
    while (new_capacity < bytes)
        new_capacity *= 2;

    glBufferData(GL_ARRAY_BUFFER, new_capacity, nullptr, GL_DYNAMIC_DRAW);
    m_vbo_capacity_bytes = new_capacity;
}

void gTextShader::setResolution(float width, float height)
{
    bind();
    float ortho[16] = {
        2.0f / width,  0.0f,           0.0f,  0.0f,
        0.0f,         -2.0f / height,  0.0f,  0.0f,
        0.0f,          0.0f,          -1.0f,  0.0f,
       -1.0f,          1.0f,           0.0f,  1.0f
    };
    glUniformMatrix4fv(m_projection_location, 1, GL_FALSE, ortho);
}

void gTextShader::drawGlyph(float x, float y, const glyph_uv& uv, float r, float g, float b, float a)
{
    bind();
    glUniform4f(m_color_location, r, g, b, a);
    glUniform1i(m_texture_location, 0);

    float w = (float)uv.width;
    float h = (float)uv.height;

    // 6 vertices × 8 floats: x, y, u, v, r, g, b, a
    float vertices[48] = {
        x,     y,     uv.u0, uv.v0, r, g, b, a,
        x,     y + h, uv.u0, uv.v1, r, g, b, a,
        x + w, y,     uv.u1, uv.v0, r, g, b, a,
        x + w, y,     uv.u1, uv.v0, r, g, b, a,
        x,     y + h, uv.u0, uv.v1, r, g, b, a,
        x + w, y + h, uv.u1, uv.v1, r, g, b, a
    };

    bindVAO();
    glBindBuffer(GL_ARRAY_BUFFER, m_vbo);
    glBufferSubData(GL_ARRAY_BUFFER, 0, sizeof(vertices), vertices);
    glDrawArrays(GL_TRIANGLES, 0, 6);
    unbindVAO();
}

void gTextShader::drawBatch(const float* vertices, size_t float_count)
{
    if (!vertices || !float_count)
        return;

    bind();
    glUniform1i(m_texture_location, 0);

    bindVAO();
    glBindBuffer(GL_ARRAY_BUFFER, m_vbo);
    const size_t bytes = float_count * sizeof(float);
    ensureVboCapacity(bytes);
    glBufferSubData(GL_ARRAY_BUFFER, 0, bytes, vertices);
    glDrawArrays(GL_TRIANGLES, 0, static_cast<GLsizei>(float_count / 8));
    unbindVAO();
}
