#include <lib/base/eerror.h>
#include <lib/gdi/egl/gtexture_manager.h>

static gTextureManager* s_active_manager = nullptr;

gTextureManager::gTextureManager() {
	s_active_manager = this;
}

gTextureManager::~gTextureManager() {
	if (s_active_manager == this)
		s_active_manager = nullptr;
}

GLuint gTextureManager::createTextureFromPixmap(gPixmap* pixmap) {
	if (!pixmap || !pixmap->surface)
		return 0;

	gSurface* surface = pixmap->surface;
	int width = surface->x;
	int height = surface->y;

	GLuint texture_id;
	glGenTextures(1, &texture_id);
	glBindTexture(GL_TEXTURE_2D, texture_id);

	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE);
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE);

	if (surface->bpp == 32) {
		// 32-bit images can be uploaded directly.
		// note: e2 often uses bgra layout in memory. if colors look swapped (blue faces),
		// change GL_RGBA to GL_BGRA_EXT in the format parameter below.
#ifndef GL_BGRA_EXT
#define GL_BGRA_EXT 0x80E1
#endif
		glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0, GL_BGRA_EXT, GL_UNSIGNED_BYTE, surface->data);
	} else if (surface->bpp == 8 && surface->clut.data) {
		// 8-bit paletted image (often used for picons/skins).
		// gles 3.0 does not support indexed color textures natively anymore,
		// so we expand it to 32-bit rgba on the cpu before uploading.
		std::vector<uint32_t> rgba_buffer(width * height);
		uint8_t* src_pixels = (uint8_t*)surface->data;
		gRGB* palette = surface->clut.data;

		for (int i = 0; i < width * height; ++i) {
			gRGB color = palette[src_pixels[i]];
			// pack e2 gRGB into a 32-bit integer (rgba layout)
			rgba_buffer[i] = (color.a << 24) | (color.b << 16) | (color.g << 8) | color.r;
		}

		glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0, GL_RGBA, GL_UNSIGNED_BYTE, rgba_buffer.data());
	} else {
		eDebug("[gTextureManager] unsupported surface format (bpp: %d)", surface->bpp);
		glDeleteTextures(1, &texture_id);
		return 0;
	}

	glBindTexture(GL_TEXTURE_2D, 0);
	return texture_id;
}

GLuint gTextureManager::getTexture(gPixmap* pixmap) {
	if (!pixmap || !pixmap->surface)
		return 0;

	if (pixmap->surface->gl_texture_id != 0) {
		return pixmap->surface->gl_texture_id;
	}

	GLuint new_texture = createTextureFromPixmap(pixmap);
	if (new_texture) {
		pixmap->surface->gl_texture_id = new_texture;
	}
	return new_texture;
}

void gTextureManager::queueForDeletion(GLuint texture_id) {
	if (texture_id == 0)
		return;

	std::lock_guard<std::mutex> lock(m_deletion_mutex);
	m_pending_deletions.push_back(texture_id);
}

void gTextureManager::processDeletions() {
	std::lock_guard<std::mutex> lock(m_deletion_mutex);
	if (!m_pending_deletions.empty()) {
		glDeleteTextures(m_pending_deletions.size(), m_pending_deletions.data());

		m_pending_deletions.clear();
	}
}

extern "C" void egl_queue_texture_deletion(unsigned int gl_texture_id);
void egl_queue_texture_deletion(unsigned int gl_texture_id) {
	if (s_active_manager) {
		s_active_manager->queueForDeletion(gl_texture_id);
	}
}