#include <lib/gdi/egl/shader/gtexture_shader.h>
#include <lib/gdi/egl/gles_version.h>
#include <lib/base/eerror.h>
#include <EGL/egl.h>

// ---------------------------------------------------------------------------
// GLES 3.0 shader sources
// ---------------------------------------------------------------------------
#if defined(HAVE_GLES3)
static const char *vertex_shader_es3 = R"(#version 300 es
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

static const char *fragment_shader_es3 = R"(#version 300 es
    precision mediump float;
    
    in vec2 v_uv;
    in vec2 v_pos;
    out vec4 frag_color;
    
    uniform sampler2D u_texture;
    uniform float u_global_alpha;
    uniform int u_alpha_test;
    uniform int u_luma_texture;
    
    uniform vec4 u_rect_size;
    uniform float u_radius;
    uniform int u_edges;

    float cornerCoverage(float r, vec2 d) {
        if (r <= 0.0)
            return 1.0;
        float dist = length(d) - r;
        return clamp(0.5 - dist, 0.0, 1.0);
    }

    float roundedCoverage(vec2 local) {
        float w = u_rect_size.z;
        float h = u_rect_size.w;
        float r = min(u_radius, min(w, h) * 0.5);
        float c = 1.0;
        if ((u_edges & 1) != 0 && local.x < r && local.y < r)
            c = cornerCoverage(r, vec2(r - local.x, r - local.y));
        else if ((u_edges & 2) != 0 && local.x > w - r && local.y < r)
            c = cornerCoverage(r, vec2(local.x - (w - r), r - local.y));
        else if ((u_edges & 4) != 0 && local.x < r && local.y > h - r)
            c = cornerCoverage(r, vec2(r - local.x, local.y - (h - r)));
        else if ((u_edges & 8) != 0 && local.x > w - r && local.y > h - r)
            c = cornerCoverage(r, vec2(local.x - (w - r), local.y - (h - r)));
        return c;
    }

    void main() {
        float coverage = 1.0;
        if (u_radius > 0.0) {
            coverage = roundedCoverage(v_pos - u_rect_size.xy);
            if (coverage <= 0.0)
                discard;
        }

        vec4 tex_color = texture(u_texture, v_uv);
        if (u_luma_texture == 1)
            tex_color = vec4(tex_color.r, tex_color.r, tex_color.r, tex_color.a);
        if (u_alpha_test == 1 && tex_color.a < 0.5) discard;
        frag_color = vec4(tex_color.rgb, tex_color.a * u_global_alpha * coverage);
    }
)";
#endif

// ---------------------------------------------------------------------------
// GLES 2.0 shader sources
// ---------------------------------------------------------------------------
static const char *vertex_shader_es2 = R"(#version 100
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

static const char *fragment_shader_es2 = R"(#version 100
    precision mediump float;
    
    varying vec2 v_uv;
    varying vec2 v_pos;
    
    uniform sampler2D u_texture;
    uniform float u_global_alpha;
    uniform int u_alpha_test;
    uniform int u_luma_texture;
    
    uniform vec4 u_rect_size;
    uniform float u_radius;
    // Per-corner radii (GLSL ES 1.00 has no bitwise ops on integers)
    uniform float u_r_tl;
    uniform float u_r_tr;
    uniform float u_r_bl;
    uniform float u_r_br;

    float cornerCoverage(float r, vec2 d) {
        if (r <= 0.0)
            return 1.0;
        float dist = length(d) - r;
        return clamp(0.5 - dist, 0.0, 1.0);
    }

    float roundedCoverage(vec2 local) {
        float w = u_rect_size.z;
        float h = u_rect_size.w;
        float max_r = min(w, h) * 0.5;
        float r_tl = min(u_r_tl, max_r);
        float r_tr = min(u_r_tr, max_r);
        float r_bl = min(u_r_bl, max_r);
        float r_br = min(u_r_br, max_r);
        float c = 1.0;
        if (local.x < r_tl && local.y < r_tl)
            c = cornerCoverage(r_tl, vec2(r_tl - local.x, r_tl - local.y));
        else if (local.x > w - r_tr && local.y < r_tr)
            c = cornerCoverage(r_tr, vec2(local.x - (w - r_tr), r_tr - local.y));
        else if (local.x < r_bl && local.y > h - r_bl)
            c = cornerCoverage(r_bl, vec2(r_bl - local.x, local.y - (h - r_bl)));
        else if (local.x > w - r_br && local.y > h - r_br)
            c = cornerCoverage(r_br, vec2(local.x - (w - r_br), local.y - (h - r_br)));
        return c;
    }

    void main() {
        float coverage = 1.0;
        if (u_radius > 0.0) {
            coverage = roundedCoverage(v_pos - u_rect_size.xy);
            if (coverage <= 0.0)
                discard;
        }

        vec4 tex_color = texture2D(u_texture, v_uv);
        if (u_luma_texture == 1)
            tex_color = vec4(tex_color.r, tex_color.r, tex_color.r, tex_color.a);
        if (u_alpha_test == 1 && tex_color.a < 0.5) discard;
        gl_FragColor = vec4(tex_color.rgb, tex_color.a * u_global_alpha * coverage);
    }
)";

// ---------------------------------------------------------------------------

gTextureShader::gTextureShader() : m_program_id(0), m_vbo(0)
{
}

gTextureShader::~gTextureShader()
{
    release();
}

void gTextureShader::release()
{
    if (eglGetCurrentContext() == EGL_NO_CONTEXT) {
        m_vbo = 0;
        m_program_id = 0;
        return;
    }
    if (m_vbo) {
        glDeleteBuffers(1, &m_vbo);
        m_vbo = 0;
    }
    if (m_program_id) {
        glDeleteProgram(m_program_id);
        m_program_id = 0;
    }
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
    m_alpha_test_location  = glGetUniformLocation(m_program_id, "u_alpha_test");
    m_luma_texture_location = glGetUniformLocation(m_program_id, "u_luma_texture");
    m_rect_size_location   = glGetUniformLocation(m_program_id, "u_rect_size");
    m_radius_location      = glGetUniformLocation(m_program_id, "u_radius");
    m_edges_location       = glGetUniformLocation(m_program_id, "u_edges");

    if (!gles::isGLES3()) {
        m_edges_tl_location = glGetUniformLocation(m_program_id, "u_r_tl");
        m_edges_tr_location = glGetUniformLocation(m_program_id, "u_r_tr");
        m_edges_bl_location = glGetUniformLocation(m_program_id, "u_r_bl");
        m_edges_br_location = glGetUniformLocation(m_program_id, "u_r_br");
    }

    glGenBuffers(1, &m_vbo);
    glBindBuffer(GL_ARRAY_BUFFER, m_vbo);
    // 6 vertices × 4 floats (x, y, u, v)
    glBufferData(GL_ARRAY_BUFFER, sizeof(float) * 6 * 4, nullptr, GL_DYNAMIC_DRAW);
    
    glVertexAttribPointer(0, 4, GL_FLOAT, GL_FALSE, 4 * sizeof(float), (void*)0);
    glEnableVertexAttribArray(0);
    
    glBindBuffer(GL_ARRAY_BUFFER, 0);

    return true;
}

void gTextureShader::bind()
{
    glUseProgram(m_program_id);
}

void gTextureShader::bindVAO()
{
    glBindBuffer(GL_ARRAY_BUFFER, m_vbo);
    glVertexAttribPointer(0, 4, GL_FLOAT, GL_FALSE, 4 * sizeof(float), (void*)0);
    glEnableVertexAttribArray(0);
}

void gTextureShader::unbindVAO()
{
    glDisableVertexAttribArray(0);
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

void gTextureShader::setFramebufferResolution(float width, float height)
{
    bind();
    float ortho[16] = {
        2.0f / width, 0.0f, 0.0f, 0.0f,
        0.0f, 2.0f / height, 0.0f, 0.0f,
        0.0f, 0.0f, -1.0f, 0.0f,
        -1.0f, -1.0f, 0.0f, 1.0f
    };
    glUniformMatrix4fv(m_projection_location, 1, GL_FALSE, ortho);
}

void gTextureShader::drawTexture(float x, float y, float width, float height, GLuint texture_id, float global_alpha, float radius, uint8_t edges, float u0, float v0, float u1, float v1, bool alpha_test,
								 bool luma_texture, float mask_x, float mask_y, float mask_width, float mask_height)
{
    bind();
    
    glActiveTexture(GL_TEXTURE0);
    glBindTexture(GL_TEXTURE_2D, texture_id);
    glUniform1i(m_texture_location, 0);
    glUniform1f(m_alpha_location, global_alpha);
    glUniform1i(m_alpha_test_location, alpha_test ? 1 : 0);
    glUniform1i(m_luma_texture_location, luma_texture ? 1 : 0);
    
	if (mask_width <= 0.0f || mask_height <= 0.0f) {
		mask_x = x;
		mask_y = y;
		mask_width = width;
		mask_height = height;
	}

    glUniform4f(m_rect_size_location, mask_x, mask_y, mask_width, mask_height);
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
        x,         y,          u0, v0,
        x,         y + height, u0, v1,
        x + width, y,          u1, v0,
        x + width, y,          u1, v0,
        x,         y + height, u0, v1,
        x + width, y + height, u1, v1
    };

    bindVAO();
    glBindBuffer(GL_ARRAY_BUFFER, m_vbo);
    glBufferSubData(GL_ARRAY_BUFFER, 0, sizeof(vertices), vertices);
    glDrawArrays(GL_TRIANGLES, 0, 6);
    unbindVAO();
}
