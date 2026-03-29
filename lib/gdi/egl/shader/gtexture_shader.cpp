#include <lib/gdi/egl/shader/gtexture_shader.h>
#include <lib/gdi/egl/gles_version.h>
#include <lib/base/eerror.h>

// ---------------------------------------------------------------------------
// GLES 3.0 shader sources
// ---------------------------------------------------------------------------
#if defined(HAVE_GLES3)
static const char *vertex_shader_es3 = R"(
    #version 300 es
    layout(location = 0) in vec4 pos_uv;
    uniform mat4 u_projection;
    out vec2 v_uv;
    out vec2 v_pos;
    void main() {
        gl_Position = u_projection * vec4(pos_uv.xy, 0.0, 1.0);
        v_uv  = pos_uv.zw;
        v_pos = pos_uv.xy;
    }
)";

static const char *fragment_shader_es3 = R"(
    #version 300 es
    precision mediump float;
    
    in vec2 v_uv;
    in vec2 v_pos;
    out vec4 frag_color;
    
    uniform sampler2D u_texture;
    uniform float u_global_alpha;
    
    uniform vec4 u_rect_size;
    uniform float u_radius;
    uniform int u_edges;

    float udRoundBox(vec2 p, vec2 b, float r) {
        vec2 d = abs(p) - b + vec2(r);
        return min(max(d.x, d.y), 0.0) + length(max(d, 0.0)) - r;
    }

    void main() {
        if (u_radius > 0.0) {
            vec2 half_size = u_rect_size.zw * 0.5;
            vec2 center = vec2(u_rect_size.x, u_rect_size.y) + half_size;
            vec2 p = v_pos - center;
            float r = u_radius;

            if (p.x < 0.0 && p.y < 0.0 && (u_edges & 1) == 0) r = 0.0;
            if (p.x > 0.0 && p.y < 0.0 && (u_edges & 2) == 0) r = 0.0;
            if (p.x < 0.0 && p.y > 0.0 && (u_edges & 4) == 0) r = 0.0;
            if (p.x > 0.0 && p.y > 0.0 && (u_edges & 8) == 0) r = 0.0;

            float dist = udRoundBox(p, half_size, r);
            if (dist > 0.5) discard;
        }

        vec4 tex_color = texture(u_texture, v_uv);
        frag_color = vec4(tex_color.rgb, tex_color.a * u_global_alpha);
    }
)";
#endif

// ---------------------------------------------------------------------------
// GLES 2.0 shader sources
// ---------------------------------------------------------------------------
static const char *vertex_shader_es2 = R"(
    #version 100
    attribute vec4 pos_uv;
    uniform mat4 u_projection;
    varying vec2 v_uv;
    varying vec2 v_pos;
    void main() {
        gl_Position = u_projection * vec4(pos_uv.xy, 0.0, 1.0);
        v_uv  = pos_uv.zw;
        v_pos = pos_uv.xy;
    }
)";

static const char *fragment_shader_es2 = R"(
    #version 100
    precision mediump float;
    
    varying vec2 v_uv;
    varying vec2 v_pos;
    
    uniform sampler2D u_texture;
    uniform float u_global_alpha;
    
    uniform vec4 u_rect_size;
    uniform float u_radius;
    // Per-corner radii (GLSL ES 1.00 has no bitwise ops on integers)
    uniform float u_r_tl;
    uniform float u_r_tr;
    uniform float u_r_bl;
    uniform float u_r_br;

    float udRoundBox(vec2 p, vec2 b, float r) {
        vec2 d = abs(p) - b + vec2(r);
        return min(max(d.x, d.y), 0.0) + length(max(d, 0.0)) - r;
    }

    void main() {
        if (u_radius > 0.0) {
            vec2 half_size = u_rect_size.zw * 0.5;
            vec2 center = vec2(u_rect_size.x, u_rect_size.y) + half_size;
            vec2 p = v_pos - center;
            float r = u_radius;

            if (p.x < 0.0 && p.y < 0.0) r = u_r_tl;
            if (p.x > 0.0 && p.y < 0.0) r = u_r_tr;
            if (p.x < 0.0 && p.y > 0.0) r = u_r_bl;
            if (p.x > 0.0 && p.y > 0.0) r = u_r_br;

            float dist = udRoundBox(p, half_size, r);
            if (dist > 0.5) discard;
        }

        vec4 tex_color = texture2D(u_texture, v_uv);
        gl_FragColor = vec4(tex_color.rgb, tex_color.a * u_global_alpha);
    }
)";

// ---------------------------------------------------------------------------

#if defined(HAVE_GLES3)
gTextureShader::gTextureShader() : m_program_id(0), m_vao(0), m_vbo(0)
#else
gTextureShader::gTextureShader() : m_program_id(0), m_vbo(0)
#endif
{
}

gTextureShader::~gTextureShader()
{
#if defined(HAVE_GLES3)
    if (gles::isGLES3() && m_vao) glDeleteVertexArrays(1, &m_vao);
#endif
    if (m_vbo) glDeleteBuffers(1, &m_vbo);
    if (m_program_id) glDeleteProgram(m_program_id);
}

GLuint gTextureShader::compileShader(GLenum type, const char *source)
{
    GLuint shader = glCreateShader(type);
    glShaderSource(shader, 1, &source, nullptr);
    glCompileShader(shader);

    GLint success;
    glGetShaderiv(shader, GL_COMPILE_STATUS, &success);
    if (!success) {
        GLchar info_log[512];
        glGetShaderInfoLog(shader, 512, nullptr, info_log);
        eDebug("[gTextureShader] compilation failed: %s", info_log);
        return 0;
    }
    return shader;
}

bool gTextureShader::init()
{
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
    }

    glAttachShader(m_program_id, vertex_shader);
    glAttachShader(m_program_id, fragment_shader);
    glLinkProgram(m_program_id);

    glDeleteShader(vertex_shader);
    glDeleteShader(fragment_shader);

    m_projection_location  = glGetUniformLocation(m_program_id, "u_projection");
    m_texture_location     = glGetUniformLocation(m_program_id, "u_texture");
    m_alpha_location       = glGetUniformLocation(m_program_id, "u_global_alpha");
    m_rect_size_location   = glGetUniformLocation(m_program_id, "u_rect_size");
    m_radius_location      = glGetUniformLocation(m_program_id, "u_radius");
    m_edges_location       = glGetUniformLocation(m_program_id, "u_edges");

    if (!gles::isGLES3()) {
        m_edges_tl_location = glGetUniformLocation(m_program_id, "u_r_tl");
        m_edges_tr_location = glGetUniformLocation(m_program_id, "u_r_tr");
        m_edges_bl_location = glGetUniformLocation(m_program_id, "u_r_bl");
        m_edges_br_location = glGetUniformLocation(m_program_id, "u_r_br");
    }

#if defined(HAVE_GLES3)
    if (gles::isGLES3()) {
        glGenVertexArrays(1, &m_vao);
        glBindVertexArray(m_vao);
    }
#endif

    glGenBuffers(1, &m_vbo);
    glBindBuffer(GL_ARRAY_BUFFER, m_vbo);
    // 6 vertices × 4 floats (x, y, u, v)
    glBufferData(GL_ARRAY_BUFFER, sizeof(float) * 6 * 4, nullptr, GL_DYNAMIC_DRAW);
    
    glVertexAttribPointer(0, 4, GL_FLOAT, GL_FALSE, 4 * sizeof(float), (void*)0);
    glEnableVertexAttribArray(0);
    
    glBindBuffer(GL_ARRAY_BUFFER, 0);
#if defined(HAVE_GLES3)
    if (gles::isGLES3()) glBindVertexArray(0);
#endif

    return true;
}

void gTextureShader::bind()
{
    glUseProgram(m_program_id);
}

void gTextureShader::bindVAO()
{
#if defined(HAVE_GLES3)
    if (gles::isGLES3()) {
        glBindVertexArray(m_vao);
    } else
#endif
    {
        glBindBuffer(GL_ARRAY_BUFFER, m_vbo);
        glVertexAttribPointer(0, 4, GL_FLOAT, GL_FALSE, 4 * sizeof(float), (void*)0);
        glEnableVertexAttribArray(0);
    }
}

void gTextureShader::unbindVAO()
{
#if defined(HAVE_GLES3)
    if (gles::isGLES3()) {
        glBindVertexArray(0);
    } else
#endif
    {
        glDisableVertexAttribArray(0);
    }
}

void gTextureShader::setResolution(float width, float height)
{
    bind();
    float ortho[16] = {
        2.0f / width, 0.0f, 0.0f, 0.0f,
        0.0f, -2.0f / height, 0.0f, 0.0f,
        0.0f, 0.0f, -1.0f, 0.0f,
        -1.0f, 1.0f, 0.0f, 1.0f
    };
    glUniformMatrix4fv(m_projection_location, 1, GL_FALSE, ortho);
}

void gTextureShader::drawTexture(float x, float y, float width, float height, GLuint texture_id, float global_alpha, float radius, uint8_t edges)
{
    bind();
    
    glActiveTexture(GL_TEXTURE0);
    glBindTexture(GL_TEXTURE_2D, texture_id);
    glUniform1i(m_texture_location, 0);
    glUniform1f(m_alpha_location, global_alpha);
    
    glUniform4f(m_rect_size_location, x, y, width, height);
    glUniform1f(m_radius_location, radius);

    if (gles::isGLES3()) {
        glUniform1i(m_edges_location, (int)edges);
    } else {
        glUniform1f(m_edges_tl_location, (edges & 1) ? radius : 0.0f);
        glUniform1f(m_edges_tr_location, (edges & 2) ? radius : 0.0f);
        glUniform1f(m_edges_bl_location, (edges & 4) ? radius : 0.0f);
        glUniform1f(m_edges_br_location, (edges & 8) ? radius : 0.0f);
    }

    // x, y, u, v
    float vertices[24] = {
        x,         y,          0.0f, 0.0f,
        x,         y + height, 0.0f, 1.0f,
        x + width, y,          1.0f, 0.0f,
        x + width, y,          1.0f, 0.0f,
        x,         y + height, 0.0f, 1.0f,
        x + width, y + height, 1.0f, 1.0f
    };

    bindVAO();
    glBindBuffer(GL_ARRAY_BUFFER, m_vbo);
    glBufferSubData(GL_ARRAY_BUFFER, 0, sizeof(vertices), vertices);
    glDrawArrays(GL_TRIANGLES, 0, 6);
    unbindVAO();
}