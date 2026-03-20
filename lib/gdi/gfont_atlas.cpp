#include <lib/gdi/gfont_atlas.h>
#include <lib/base/eerror.h>
#include <cstring>

gFontAtlas::gFontAtlas()
    : m_atlas_width(0), m_atlas_height(0), m_is_dirty(false),
      m_current_x(0), m_current_y(0), m_current_row_height(0)
{
}

gFontAtlas::~gFontAtlas()
{
    // m_pixmap is managed by ePtr
}

bool gFontAtlas::init(int width, int height)
{
    // Normally 2D blitters support at least 2048x2048, but the user can clamp this down 
    // elsewhere if they know their hardware's max 2D texture limit.
    m_atlas_width = width;
    m_atlas_height = height;

    // Create an 8-bit pixmap for the atlas as a simple byte buffer.
    m_pixmap = new gPixmap(eSize(width, height), 8);
    // Initialize to zero (transparent)
    memset(m_pixmap->surface->data, 0, width * height);

    m_is_dirty = false;
    m_dirty_rect = eRect();

    eDebug("[gFontAtlas] initialized %dx%d glyph atlas", width, height);
    return true;
}



bool gFontAtlas::getGlyph(glyph_key_t key, glyph_uv &uv)
{
    auto it = m_glyphs.find(key);
    if (it != m_glyphs.end()) {
        uv = it->second;
        return true;
    }
    return false;
}

void gFontAtlas::addGlyph(glyph_key_t key, int width, int height, const uint8_t *data, glyph_uv &uv)
{
    if (!m_pixmap) return;
    
    if (width == 0 || height == 0) {
        // Empty space glyph
        uv.u0 = uv.v0 = uv.u1 = uv.v1 = 0.0f;
        uv.width = 0;
        uv.height = 0;
        m_glyphs[key] = uv;
        return;
    }

    // Check if we need to advance to the next row
    if (m_current_x + width > m_atlas_width) {
        m_current_x = 0;
        m_current_y += m_current_row_height + 1; // 1px padding
        m_current_row_height = 0;
    }

    // Check if we ran out of space entirely
    if (m_current_y + height > m_atlas_height) {
        eDebug("[gFontAtlas] ATLAS FULL! Resetting atlas...");
        m_current_x = 0;
        m_current_y = 0;
        m_current_row_height = 0;
        m_glyphs.clear();
        memset(m_pixmap->surface->data, 0, m_atlas_width * m_atlas_height);
        m_is_dirty = true;
        m_dirty_rect = eRect(0, 0, m_atlas_width, m_atlas_height);
    }

    // Manually copy the glyph into our 8-bit pixmap buffer on the CPU
    uint8_t *dst = (uint8_t *)m_pixmap->surface->data;
    for (int row = 0; row < height; ++row) {
        memcpy(dst + ((m_current_y + row) * m_atlas_width) + m_current_x, 
               data + (row * width), 
               width);
    }

    if (!m_is_dirty) {
        m_dirty_rect = eRect(m_current_x, m_current_y, width, height);
        m_is_dirty = true;
    } else {
        // Expand dirty rect
        int min_x = std::min(m_dirty_rect.left(), m_current_x);
        int min_y = std::min(m_dirty_rect.top(), m_current_y);
        int max_x = std::max(m_dirty_rect.right(), m_current_x + width);
        int max_y = std::max(m_dirty_rect.bottom(), m_current_y + height);
        m_dirty_rect = eRect(min_x, min_y, max_x - min_x, max_y - min_y);
    }

    uv.width = width;
    uv.height = height;
    uv.u0 = (float)m_current_x / (float)m_atlas_width;
    uv.v0 = (float)m_current_y / (float)m_atlas_height;
    uv.u1 = (float)(m_current_x + width) / (float)m_atlas_width;
    uv.v1 = (float)(m_current_y + height) / (float)m_atlas_height;

    m_glyphs[key] = uv;

    m_current_x += width + 1; // 1 pixel padding
    if (height > m_current_row_height) {
        m_current_row_height = height;
    }
}
