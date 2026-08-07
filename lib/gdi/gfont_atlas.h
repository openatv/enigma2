#pragma once

#include <include/stb_rect_pack.h>
#include <lib/gdi/gpixmap.h>
#include <lib/gdi/erect.h>
#include <unordered_map>
#include <vector>
#include <stdint.h>
#include <cstdint>

typedef uint64_t glyph_key_t;

struct glyph_uv {
    float u0, v0;
    float u1, v1;
    int width, height;
};

class gFontAtlas
{
private:
    ePtr<gPixmap> m_pixmap;
    int m_atlas_width;
    int m_atlas_height;
    
    bool m_is_dirty;
    eRect m_dirty_rect;
    std::vector<eRect> m_dirty_rects;

    stbrp_context m_pack_context;
    std::vector<stbrp_node> m_pack_nodes;

    std::unordered_map<glyph_key_t, glyph_uv> m_glyphs;

    void markDirty(const eRect &rect);

public:
    gFontAtlas();
    ~gFontAtlas();

    bool init(int width = 2048, int height = 2048);
    void release();
    
    bool getGlyph(glyph_key_t key, glyph_uv &uv);
    bool addGlyph(glyph_key_t key, int width, int height, int pitch, const uint8_t *data, glyph_uv &uv, bool allow_reset = true);

    gPixmap* getPixmap() const { return m_pixmap; }
    bool isDirty() const { return m_is_dirty; }
    eRect getDirtyRect() const { return m_dirty_rect; }
    const std::vector<eRect>& getDirtyRects() const { return m_dirty_rects; }
    void clearDirty() { m_is_dirty = false; m_dirty_rect = eRect(); m_dirty_rects.clear(); }
};
