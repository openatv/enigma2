#include <lib/base/eerror.h>
#include <lib/gdi/egl/gles_version.h>
#include <lib/gdi/egl/shader/gadvanced_shader.h>

// ---------------------------------------------------------------------------
// GLES 3.0 shader sources
// ---------------------------------------------------------------------------
#if defined(HAVE_GLES3)
static const char* vertex_shader_es3 = R"(
    #version 300 es
    layout(location = 0) in vec2 position;
    uniform mat4 u_projection;
    out vec2 v_pos;
    void main() {
        gl_Position = u_projection * vec4(position, 0.0, 1.0);
        v_pos = position;
    }
)";

static const char* fragment_shader_es3 = R"(
    #version 300 es
    precision mediump float;
    
    in vec2 v_pos;
    out vec4 frag_color;
    
    uniform vec4 u_rect_size;
    uniform float u_radius;
    uniform int u_edges;
    uniform vec4 u_solid_color;
    
    uniform int u_num_stops;
    uniform vec4 u_gradient_colors[16];
    uniform float u_gradient_stops[16];
    uniform int u_gradient_orientation;
    uniform int u_alphablend;

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
        
        vec4 final_color = u_solid_color;
        
        if (u_num_stops > 0) {
            float t = 0.0;
            if (u_gradient_orientation == 1) {
                t = (v_pos.x - u_rect_size.x) / u_rect_size.z;
            } else {
                t = (v_pos.y - u_rect_size.y) / u_rect_size.w;
            }
            
            vec4 grad_color = u_gradient_colors[0];
            for (int i = 0; i < 15; i++) {
                if (i >= u_num_stops - 1) break;
                if (t >= u_gradient_stops[i] && t <= u_gradient_stops[i+1]) {
                    float range = u_gradient_stops[i+1] - u_gradient_stops[i];
                    float f = (t - u_gradient_stops[i]) / range;
                    grad_color = mix(u_gradient_colors[i], u_gradient_colors[i+1], f);
                    break;
                }
            }
            
            if (t > u_gradient_stops[u_num_stops - 1]) {
                grad_color = u_gradient_colors[u_num_stops - 1];
            }
            
            if (u_alphablend == 1) {
                final_color.rgb = mix(final_color.rgb, grad_color.rgb, grad_color.a);
            } else {
                final_color = grad_color;
            }
        }
        
        frag_color = final_color;
    }
)";
#endif

// ---------------------------------------------------------------------------
// GLES 2.0 shader sources
// Note: bitwise operators on int uniforms are NOT supported in GLSL ES 1.00.
// We replace the bitmask corner test with float comparisons using float uniforms.
// ---------------------------------------------------------------------------
static const char* vertex_shader_es2 = R"(
    #version 100
    attribute vec2 position;
    uniform mat4 u_projection;
    varying vec2 v_pos;
    void main() {
        gl_Position = u_projection * vec4(position, 0.0, 1.0);
        v_pos = position;
    }
)";

static const char* fragment_shader_es2 = R"(
    #version 100
    precision mediump float;
    
    varying vec2 v_pos;
    
    uniform vec4 u_rect_size;
    uniform float u_radius;
    // Per-corner radii replaces bitmask (GLSL ES 1.00 has no bitwise ops on int uniforms)
    uniform float u_r_tl; // top-left
    uniform float u_r_tr; // top-right
    uniform float u_r_bl; // bottom-left
    uniform float u_r_br; // bottom-right
    uniform vec4 u_solid_color;
    
    uniform int u_num_stops;
    uniform vec4 u_gradient_colors[16];
    uniform float u_gradient_stops[16];
    uniform int u_gradient_orientation;
    uniform int u_alphablend;

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
        
        vec4 final_color = u_solid_color;
        
        if (u_num_stops > 0) {
            float t = 0.0;
            if (u_gradient_orientation == 1) {
                t = (v_pos.x - u_rect_size.x) / u_rect_size.z;
            } else {
                t = (v_pos.y - u_rect_size.y) / u_rect_size.w;
            }
            
            vec4 grad_color = u_gradient_colors[0];
            for (int i = 0; i < 15; i++) {
                if (i >= u_num_stops - 1) break;
                if (t >= u_gradient_stops[i] && t <= u_gradient_stops[i+1]) {
                    float range = u_gradient_stops[i+1] - u_gradient_stops[i];
                    float f = (t - u_gradient_stops[i]) / range;
                    grad_color = mix(u_gradient_colors[i], u_gradient_colors[i+1], f);
                    break;
                }
            }
            
            if (t > u_gradient_stops[u_num_stops - 1]) {
                grad_color = u_gradient_colors[u_num_stops - 1];
            }
            
            if (u_alphablend == 1) {
                final_color.rgb = mix(final_color.rgb, grad_color.rgb, grad_color.a);
            } else {
                final_color = grad_color;
            }
        }
        
        gl_FragColor = final_color;
    }
)";

// ---------------------------------------------------------------------------

#if defined(HAVE_GLES3)
gAdvancedShader::gAdvancedShader() : m_program_id(0), m_vao(0), m_vbo(0) {}
#else
gAdvancedShader::gAdvancedShader() : m_program_id(0), m_vbo(0) {}
#endif

gAdvancedShader::~gAdvancedShader() {
#if defined(HAVE_GLES3)
	if (gles::isGLES3() && m_vao)
		glDeleteVertexArrays(1, &m_vao);
#endif
	if (m_vbo)
		glDeleteBuffers(1, &m_vbo);
	if (m_program_id)
		glDeleteProgram(m_program_id);
}

GLuint gAdvancedShader::compileShader(GLenum type, const char* source) {
	GLuint shader = glCreateShader(type);
	glShaderSource(shader, 1, &source, nullptr);
	glCompileShader(shader);

	GLint success;
	glGetShaderiv(shader, GL_COMPILE_STATUS, &success);
	if (!success) {
		GLchar info_log[512];
		glGetShaderInfoLog(shader, 512, nullptr, info_log);
		eDebug("[gAdvancedShader] compilation failed: %s", info_log);
		return 0;
	}
	return shader;
}

bool gAdvancedShader::init() {
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

	if (!gles::isGLES3()) {
		glBindAttribLocation(m_program_id, 0, "position");
	}

	glAttachShader(m_program_id, vertex_shader);
	glAttachShader(m_program_id, fragment_shader);
	glLinkProgram(m_program_id);

	glDeleteShader(vertex_shader);
	glDeleteShader(fragment_shader);

	m_projection_location = glGetUniformLocation(m_program_id, "u_projection");
	m_rect_size_location = glGetUniformLocation(m_program_id, "u_rect_size");
	m_radius_location = glGetUniformLocation(m_program_id, "u_radius");
	m_edges_location = glGetUniformLocation(m_program_id, "u_edges");
	m_solid_color_location = glGetUniformLocation(m_program_id, "u_solid_color");
	m_alphablend_location = glGetUniformLocation(m_program_id, "u_alphablend");
	m_gradient_colors_location = glGetUniformLocation(m_program_id, "u_gradient_colors");
	m_gradient_stops_location = glGetUniformLocation(m_program_id, "u_gradient_stops");
	m_num_stops_location = glGetUniformLocation(m_program_id, "u_num_stops");
	m_gradient_orientation_location = glGetUniformLocation(m_program_id, "u_gradient_orientation");

	// ES2-only per-corner radius locations
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

void gAdvancedShader::bind() {
	glUseProgram(m_program_id);
}

void gAdvancedShader::bindVAO() {
#if defined(HAVE_GLES3)
	if (gles::isGLES3()) {
		glBindVertexArray(m_vao);
	} else
#endif
	{
		glBindBuffer(GL_ARRAY_BUFFER, m_vbo);
		glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, 2 * sizeof(float), (void*)0);
		glEnableVertexAttribArray(0);
	}
}

void gAdvancedShader::unbindVAO() {
#if defined(HAVE_GLES3)
	if (gles::isGLES3()) {
		glBindVertexArray(0);
	} else
#endif
	{
		glDisableVertexAttribArray(0);
	}
}

void gAdvancedShader::setResolution(float width, float height) {
	bind();
	float ortho[16] = {2.0f / width, 0.0f, 0.0f, 0.0f, 0.0f, -2.0f / height, 0.0f, 0.0f, 0.0f, 0.0f, -1.0f, 0.0f, -1.0f, 1.0f, 0.0f, 1.0f};
	glUniformMatrix4fv(m_projection_location, 1, GL_FALSE, ortho);
}

void gAdvancedShader::drawAdvancedRect(float x, float y, float width, float height, int radius, uint8_t edges, const std::vector<gRGB>& gradient_colors, uint8_t orientation, bool alphablend,
									   float alpha, const gRGB& solid_color) {
	bind();

	glUniform4f(m_rect_size_location, x, y, width, height);
	glUniform1f(m_radius_location, (float)radius);
	glUniform4f(m_solid_color_location, solid_color.r / 255.0f, solid_color.g / 255.0f, solid_color.b / 255.0f, 1.0f - (solid_color.a / 255.0f));

	if (gles::isGLES3()) {
		// ES3: pass as integer bitmask
		glUniform1i(m_edges_location, (int)edges);
	} else {
		// ES2: expand bitmask to four per-corner float uniforms (0.0 = sharp, radius = rounded)
		float r = (float)radius;
		glUniform1f(m_edges_tl_location, (edges & 1) ? r : 0.0f);
		glUniform1f(m_edges_tr_location, (edges & 2) ? r : 0.0f);
		glUniform1f(m_edges_bl_location, (edges & 4) ? r : 0.0f);
		glUniform1f(m_edges_br_location, (edges & 8) ? r : 0.0f);
	}

	if (gradient_colors.size() > 0) {
		glUniform1i(m_num_stops_location, gradient_colors.size());
		glUniform1i(m_gradient_orientation_location, orientation);
		glUniform1i(m_alphablend_location, alphablend ? 1 : 0);

		float colors[16 * 4];
		float stops[16];
		int stops_count = gradient_colors.size() > 16 ? 16 : gradient_colors.size();

		for (int i = 0; i < stops_count; i++) {
			colors[i * 4 + 0] = gradient_colors[i].r / 255.0f;
			colors[i * 4 + 1] = gradient_colors[i].g / 255.0f;
			colors[i * 4 + 2] = gradient_colors[i].b / 255.0f;
			colors[i * 4 + 3] = alphablend ? alpha : (1.0f - (gradient_colors[i].a / 255.0f));
			stops[i] = (float)i / (float)(stops_count - 1);
		}

		glUniform4fv(m_gradient_colors_location, stops_count, colors);
		glUniform1fv(m_gradient_stops_location, stops_count, stops);
	} else {
		glUniform1i(m_num_stops_location, 0);
	}

	float vertices[6][2] = {{x, y}, {x, y + height}, {x + width, y}, {x + width, y}, {x, y + height}, {x + width, y + height}};

	bindVAO();
	glBindBuffer(GL_ARRAY_BUFFER, m_vbo);
	glBufferSubData(GL_ARRAY_BUFFER, 0, sizeof(vertices), vertices);
	glDrawArrays(GL_TRIANGLES, 0, 6);
	unbindVAO();
}
