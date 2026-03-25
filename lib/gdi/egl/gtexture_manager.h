#pragma once

#include <GLES2/gl2.h>
#include <GLES2/gl2ext.h>
#include <lib/gdi/gpixmap.h>
#include <mutex>
#include <unordered_map>
#include <vector>

class gTextureManager {
private:
	// thread safe garbage collection for destroyed pixmaps
	std::vector<GLuint> m_pending_deletions;
	std::mutex m_deletion_mutex;

	// unified method to generate and upload the texture based on bpp
	GLuint createTextureFromPixmap(gPixmap* pixmap);

public:
	gTextureManager();
	~gTextureManager();

	// returns the gl texture id, creating it on the fly if not cached
	GLuint getTexture(gPixmap* pixmap);

	// called by enigma2 main thread when a pixmap dies
	void queueForDeletion(GLuint texture_id);

	// called by our egl context thread at the start of exec() to free vram
	void processDeletions();
};