#include <lib/base/eerror.h>
#include <lib/gdi/egl/gtexture_manager.h>

static gTextureManager* s_active_manager = nullptr;

gTextureManager::gTextureManager() : m_egl_display(EGL_NO_DISPLAY) {
	s_active_manager = this;
}

gTextureManager::~gTextureManager() {
	if (s_active_manager == this)
		s_active_manager = nullptr;
}

#ifndef EGL_LINUX_DMA_BUF_EXT
#define EGL_LINUX_DMA_BUF_EXT 0x3270
#endif
#ifndef EGL_LINUX_DRM_FOURCC_EXT
#define EGL_LINUX_DRM_FOURCC_EXT 0x3271
#endif
#ifndef EGL_DMA_BUF_PLANE0_FD_EXT
#define EGL_DMA_BUF_PLANE0_FD_EXT 0x3272
#endif
#ifndef EGL_DMA_BUF_PLANE0_OFFSET_EXT
#define EGL_DMA_BUF_PLANE0_OFFSET_EXT 0x3273
#endif
#ifndef EGL_DMA_BUF_PLANE0_PITCH_EXT
#define EGL_DMA_BUF_PLANE0_PITCH_EXT 0x3274
#endif

// DRM FourCC formats
#define DRM_FORMAT_ARGB8888 0x34325241

#include <lib/gdi/fb.h>

GLuint gTextureManager::createTextureFromDmabuf(gPixmap* pixmap) {
#ifdef CONFIG_ION
	fbClass* fb = fbClass::getInstance();
	if (!fb || fb->m_accel_fd < 0 || m_egl_display == EGL_NO_DISPLAY)
		return 0;

	gUnmanagedSurface* surface = pixmap->surface;
	if (surface->bpp != 32 || surface->data_phys == 0)
		return 0;

	unsigned long offset = surface->data_phys - fb->getAccelPhysAddr();
	int width = surface->x;
	int height = surface->y;
	int stride = surface->stride;

	EGLint attribs[] = {
		EGL_WIDTH, width,
		EGL_HEIGHT, height,
		EGL_LINUX_DRM_FOURCC_EXT, DRM_FORMAT_ARGB8888,
		EGL_DMA_BUF_PLANE0_FD_EXT, fb->m_accel_fd,
		EGL_DMA_BUF_PLANE0_OFFSET_EXT, (EGLint)offset,
		EGL_DMA_BUF_PLANE0_PITCH_EXT, stride,
		EGL_NONE
	};

	PFNEGLCREATEIMAGEKHRPROC eglCreateImageKHR = (PFNEGLCREATEIMAGEKHRPROC)eglGetProcAddress("eglCreateImageKHR");
	PFNGLEGLIMAGETARGETTEXTURE2DOESPROC glEGLImageTargetTexture2DOES = (PFNGLEGLIMAGETARGETTEXTURE2DOESPROC)glGetProcAddress("glEGLImageTargetTexture2DOES");

	if (!eglCreateImageKHR || !glEGLImageTargetTexture2DOES) {
		eDebug("[gTextureManager] EGL dmabuf extensions not available");
		return 0;
	}

	EGLImageKHR image = eglCreateImageKHR(m_egl_display, EGL_NO_CONTEXT, EGL_LINUX_DMA_BUF_EXT, (EGLClientBuffer)NULL, attribs);
	if (image == EGL_NO_IMAGE_KHR) {
		eDebug("[gTextureManager] eglCreateImageKHR failed: 0x%x", eglGetError());
		return 0;
	}

	GLuint texture_id;
	glGenTextures(1, &texture_id);
	glBindTexture(GL_TEXTURE_2D, texture_id);
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE);
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE);

	glEGLImageTargetTexture2DOES(GL_TEXTURE_2D, image);
	glBindTexture(GL_TEXTURE_2D, 0);

	m_texture_to_image_map[texture_id] = image;
	return texture_id;
#else
	return 0;
#endif
}

GLuint gTextureManager::createTextureFromPixmap(gPixmap* pixmap) {
	if (!pixmap || !pixmap->surface)
		return 0;

	GLuint texture_id = createTextureFromDmabuf(pixmap);
	if (texture_id != 0)
		return texture_id;

	gUnmanagedSurface* surface = pixmap->surface;
	int width = surface->x;
	int height = surface->y;

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

		PFNEGLDESTROYIMAGEKHRPROC eglDestroyImageKHR = (PFNEGLDESTROYIMAGEKHRPROC)eglGetProcAddress("eglDestroyImageKHR");
		for (GLuint texture_id : m_pending_deletions) {
			auto it = m_texture_to_image_map.find(texture_id);
			if (it != m_texture_to_image_map.end()) {
				if (eglDestroyImageKHR && m_egl_display != EGL_NO_DISPLAY) {
					eglDestroyImageKHR(m_egl_display, it->second);
				}
				m_texture_to_image_map.erase(it);
			}
		}

		m_pending_deletions.clear();
	}
}

extern "C" void egl_queue_texture_deletion(unsigned int gl_texture_id);
void egl_queue_texture_deletion(unsigned int gl_texture_id) {
	if (s_active_manager) {
		s_active_manager->queueForDeletion(gl_texture_id);
	}
}