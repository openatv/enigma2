#include <lib/base/eerror.h>
#include <lib/gdi/egl/gles_version.h>
#include <lib/gdi/egl/shader/gadvanced_shader.h>
#include <EGL/egl.h>
#include <algorithm>

// ---------------------------------------------------------------------------
// GLES 3.0 shader sources
// ---------------------------------------------------------------------------
#if defined(HAVE_GLES3)
static const char* vertex_shader_es3 = R"(#version 300 es
    layout(location = 0) in vec2 position;
    uniform mat4 u_projection;
    out vec2 v_pos;
    void main() {
        gl_Position = u_projection * vec4(position, 0.0, 1.0);
        v_pos = position;
    }
)";

static const char* fragment_shader_es3 = R"(#version 300 es
    #ifdef GL_FRAGMENT_PRECISION_HIGH
    precision highp float;
    #else
    precision mediump float;
    #endif
    
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
    uniform float u_gradient_extent;
    uniform int u_alphablend;

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
        
        vec4 final_color = u_solid_color;
        
        if (u_num_stops > 0) {
            float t = 0.0;
            float extent = u_gradient_extent > 0.0 ? u_gradient_extent : ((u_gradient_orientation == 1) ? u_rect_size.w : u_rect_size.z);
            if (u_gradient_orientation == 1) {
                t = (v_pos.y - u_rect_size.y) / extent;
            } else {
                t = (v_pos.x - u_rect_size.x) / extent;
            }
            t = clamp(t, 0.0, 1.0);
            
            vec4 grad_color = u_gradient_colors[0];
            for (int i = 0; i < 15; i++) {
                if (i >= u_num_stops - 1) break;
                if (t >= u_gradient_stops[i] && t <= u_gradient_stops[i+1]) {
                    float range = u_gradient_stops[i+1] - u_gradient_stops[i];
                    float f = (t - u_gradient_stops[i]) / range;
                    f = smoothstep(0.0, 1.0, f);
                    grad_color = mix(u_gradient_colors[i], u_gradient_colors[i+1], f);
                    break;
                }
            }
            
            if (t > u_gradient_stops[u_num_stops - 1]) {
                grad_color = u_gradient_colors[u_num_stops - 1];
            }
            
            final_color = grad_color;
        }
        
        frag_color = vec4(final_color.rgb, final_color.a * coverage);
    }
)";
#endif

// ---------------------------------------------------------------------------
// GLES 2.0 shader sources
// Note: bitwise operators on int uniforms are NOT supported in GLSL ES 1.00.
// We replace the bitmask corner test with float comparisons using float uniforms.
// ---------------------------------------------------------------------------
static const char* vertex_shader_es2 = R"(#version 100
    attribute vec2 position;
    uniform mat4 u_projection;
    varying vec2 v_pos;
    void main() {
        gl_Position = u_projection * vec4(position, 0.0, 1.0);
        v_pos = position;
    }
)";

static const char* fragment_shader_es2 = R"(#version 100
    #ifdef GL_FRAGMENT_PRECISION_HIGH
    precision highp float;
    #else
    precision mediump float;
    #endif
    
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
    uniform float u_gradient_extent;
    uniform int u_alphablend;

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

    vec4 mixGradientSegment(float t, float lo, float hi, vec4 a, vec4 b) {
        float f = clamp((t - lo) / (hi - lo), 0.0, 1.0);
        return mix(a, b, smoothstep(0.0, 1.0, f));
    }

    vec4 gradientColor(float t) {
        vec4 grad_color = u_gradient_colors[0];
        float denom = max(float(u_num_stops) - 1.0, 1.0);

        if (u_num_stops > 1) {
            float lo = 0.0 / denom;
            float hi = 1.0 / denom;
            if (t >= lo && t <= hi) grad_color = mixGradientSegment(t, lo, hi, u_gradient_colors[0], u_gradient_colors[1]);
        }
        if (u_num_stops > 2) {
            float lo = 1.0 / denom;
            float hi = 2.0 / denom;
            if (t >= lo && t <= hi) grad_color = mixGradientSegment(t, lo, hi, u_gradient_colors[1], u_gradient_colors[2]);
        }
        if (u_num_stops > 3) {
            float lo = 2.0 / denom;
            float hi = 3.0 / denom;
            if (t >= lo && t <= hi) grad_color = mixGradientSegment(t, lo, hi, u_gradient_colors[2], u_gradient_colors[3]);
        }
        if (u_num_stops > 4) {
            float lo = 3.0 / denom;
            float hi = 4.0 / denom;
            if (t >= lo && t <= hi) grad_color = mixGradientSegment(t, lo, hi, u_gradient_colors[3], u_gradient_colors[4]);
        }
        if (u_num_stops > 5) {
            float lo = 4.0 / denom;
            float hi = 5.0 / denom;
            if (t >= lo && t <= hi) grad_color = mixGradientSegment(t, lo, hi, u_gradient_colors[4], u_gradient_colors[5]);
        }
        if (u_num_stops > 6) {
            float lo = 5.0 / denom;
            float hi = 6.0 / denom;
            if (t >= lo && t <= hi) grad_color = mixGradientSegment(t, lo, hi, u_gradient_colors[5], u_gradient_colors[6]);
        }
        if (u_num_stops > 7) {
            float lo = 6.0 / denom;
            float hi = 7.0 / denom;
            if (t >= lo && t <= hi) grad_color = mixGradientSegment(t, lo, hi, u_gradient_colors[6], u_gradient_colors[7]);
        }
        if (u_num_stops > 8) {
            float lo = 7.0 / denom;
            float hi = 8.0 / denom;
            if (t >= lo && t <= hi) grad_color = mixGradientSegment(t, lo, hi, u_gradient_colors[7], u_gradient_colors[8]);
        }
        if (u_num_stops > 9) {
            float lo = 8.0 / denom;
            float hi = 9.0 / denom;
            if (t >= lo && t <= hi) grad_color = mixGradientSegment(t, lo, hi, u_gradient_colors[8], u_gradient_colors[9]);
        }
        if (u_num_stops > 10) {
            float lo = 9.0 / denom;
            float hi = 10.0 / denom;
            if (t >= lo && t <= hi) grad_color = mixGradientSegment(t, lo, hi, u_gradient_colors[9], u_gradient_colors[10]);
        }
        if (u_num_stops > 11) {
            float lo = 10.0 / denom;
            float hi = 11.0 / denom;
            if (t >= lo && t <= hi) grad_color = mixGradientSegment(t, lo, hi, u_gradient_colors[10], u_gradient_colors[11]);
        }
        if (u_num_stops > 12) {
            float lo = 11.0 / denom;
            float hi = 12.0 / denom;
            if (t >= lo && t <= hi) grad_color = mixGradientSegment(t, lo, hi, u_gradient_colors[11], u_gradient_colors[12]);
        }
        if (u_num_stops > 13) {
            float lo = 12.0 / denom;
            float hi = 13.0 / denom;
            if (t >= lo && t <= hi) grad_color = mixGradientSegment(t, lo, hi, u_gradient_colors[12], u_gradient_colors[13]);
        }
        if (u_num_stops > 14) {
            float lo = 13.0 / denom;
            float hi = 14.0 / denom;
            if (t >= lo && t <= hi) grad_color = mixGradientSegment(t, lo, hi, u_gradient_colors[13], u_gradient_colors[14]);
        }
        if (u_num_stops > 15) {
            float lo = 14.0 / denom;
            float hi = 15.0 / denom;
            if (t >= lo && t <= hi) grad_color = mixGradientSegment(t, lo, hi, u_gradient_colors[14], u_gradient_colors[15]);
        }

        return grad_color;
    }

    void main() {
        float coverage = 1.0;
        if (u_radius > 0.0) {
            coverage = roundedCoverage(v_pos - u_rect_size.xy);
            if (coverage <= 0.0)
                discard;
        }
        
        vec4 final_color = u_solid_color;
        
        if (u_num_stops > 0) {
            float t = 0.0;
            float extent = u_gradient_extent > 0.0 ? u_gradient_extent : ((u_gradient_orientation == 1) ? u_rect_size.w : u_rect_size.z);
            if (u_gradient_orientation == 1) {
                t = (v_pos.y - u_rect_size.y) / extent;
            } else {
                t = (v_pos.x - u_rect_size.x) / extent;
            }
            t = clamp(t, 0.0, 1.0);
            
            final_color = gradientColor(t);
        }
        
        gl_FragColor = vec4(final_color.rgb, final_color.a * coverage);
    }
)";

// ---------------------------------------------------------------------------

gAdvancedShader::gAdvancedShader() : m_program_id(0), m_vbo(0) {}

gAdvancedShader::~gAdvancedShader() {
	release();
}

void gAdvancedShader::release() {
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

static int channelDistance(unsigned char a, unsigned char b) {
	return a > b ? a - b : b - a;
}

static bool nearlySameGradientStop(const gRGB& a, const gRGB& b) {
	return a.a == b.a && channelDistance(a.r, b.r) <= 1 && channelDistance(a.g, b.g) <= 1 && channelDistance(a.b, b.b) <= 1;
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
	m_gradient_extent_location = glGetUniformLocation(m_program_id, "u_gradient_extent");

	// ES2-only per-corner radius locations
	if (!gles::isGLES3()) {
		m_edges_tl_location = glGetUniformLocation(m_program_id, "u_r_tl");
		m_edges_tr_location = glGetUniformLocation(m_program_id, "u_r_tr");
		m_edges_bl_location = glGetUniformLocation(m_program_id, "u_r_bl");
		m_edges_br_location = glGetUniformLocation(m_program_id, "u_r_br");
	}

	glGenBuffers(1, &m_vbo);
	glBindBuffer(GL_ARRAY_BUFFER, m_vbo);
	glBufferData(GL_ARRAY_BUFFER, sizeof(float) * 6 * 2, nullptr, GL_DYNAMIC_DRAW);
	glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, 2 * sizeof(float), (void*)0);
	glEnableVertexAttribArray(0);

	glBindBuffer(GL_ARRAY_BUFFER, 0);

	return true;
}

void gAdvancedShader::bind() {
	glUseProgram(m_program_id);
}

void gAdvancedShader::bindVAO() {
	glBindBuffer(GL_ARRAY_BUFFER, m_vbo);
	glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, 2 * sizeof(float), (void*)0);
	glEnableVertexAttribArray(0);
}

void gAdvancedShader::unbindVAO() {
	glDisableVertexAttribArray(0);
}

void gAdvancedShader::setResolution(float width, float height) {
	bind();
	float ortho[16] = {2.0f / width, 0.0f, 0.0f, 0.0f, 0.0f, -2.0f / height, 0.0f, 0.0f, 0.0f, 0.0f, -1.0f, 0.0f, -1.0f, 1.0f, 0.0f, 1.0f};
	glUniformMatrix4fv(m_projection_location, 1, GL_FALSE, ortho);
}

void gAdvancedShader::setFramebufferResolution(float width, float height) {
	bind();
	float ortho[16] = {2.0f / width, 0.0f, 0.0f, 0.0f, 0.0f, 2.0f / height, 0.0f, 0.0f, 0.0f, 0.0f, -1.0f, 0.0f, -1.0f, -1.0f, 0.0f, 1.0f};
	glUniformMatrix4fv(m_projection_location, 1, GL_FALSE, ortho);
}

void gAdvancedShader::drawAdvancedRect(float x, float y, float width, float height, int radius, uint8_t edges, const std::vector<gRGB>& gradient_colors, uint8_t orientation, bool alphablend,
									   int gradient_full_size, float alpha, const gRGB& solid_color) {
	bind();
	(void)alpha;

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
		int stops_count = gradient_colors.size() > 16 ? 16 : gradient_colors.size();
		const bool collapse_tail_stop = stops_count > 2 && nearlySameGradientStop(gradient_colors[1], gradient_colors[2]);
		if (collapse_tail_stop)
			stops_count = 2;
		glUniform1i(m_num_stops_location, stops_count);
		glUniform1i(m_gradient_orientation_location, orientation);
		glUniform1i(m_alphablend_location, alphablend ? 1 : 0);
		const float default_extent = orientation == 1 ? height : width;
		const float gradient_extent = gradient_full_size > 0 ? std::max((float)gradient_full_size, default_extent) : default_extent;
		glUniform1f(m_gradient_extent_location, gradient_extent);

		float colors[16 * 4];
		float stops[16];

		for (int i = 0; i < stops_count; i++) {
			const gRGB& color = collapse_tail_stop && i == 1 ? gradient_colors[2] : gradient_colors[i];
			colors[i * 4 + 0] = color.r / 255.0f;
			colors[i * 4 + 1] = color.g / 255.0f;
			colors[i * 4 + 2] = color.b / 255.0f;
			colors[i * 4 + 3] = 1.0f - (color.a / 255.0f);
			stops[i] = stops_count > 1 ? (float)i / (float)(stops_count - 1) : 0.0f;
		}

		glUniform4fv(m_gradient_colors_location, stops_count, colors);
		glUniform1fv(m_gradient_stops_location, stops_count, stops);
	} else {
		glUniform1i(m_num_stops_location, 0);
		glUniform1f(m_gradient_extent_location, 0.0f);
	}

	float vertices[6][2] = {{x, y}, {x, y + height}, {x + width, y}, {x + width, y}, {x, y + height}, {x + width, y + height}};

	bindVAO();
	glBindBuffer(GL_ARRAY_BUFFER, m_vbo);
	glBufferSubData(GL_ARRAY_BUFFER, 0, sizeof(vertices), vertices);
	glDrawArrays(GL_TRIANGLES, 0, 6);
	unbindVAO();
}
