#include <lib/gdi/gfont_atlas.h>
#include <lib/base/eerror.h>
#include <cstring>
#include <algorithm>
#include <cstdlib>
#include <cassert>

extern "C" {
#define STB_RECT_PACK_IMPLEMENTATION
#include <include/stb_rect_pack.h>
}

gFontAtlas::gFontAtlas()
    : m_atlas_width(0)
    , m_atlas_height(0)
    , m_is_dirty(false)
{
}

gFontAtlas::~gFontAtlas()
{
}

bool gFontAtlas::init(int width, int height)
{
    release();
    m_atlas_width = width;
    m_atlas_height = height;

    m_pixmap = new gPixmap(eSize(width, height), 8, gPixmap::accelNever);
    memset(m_pixmap->surface->data, 0, width * height);

    m_is_dirty = false;
    m_dirty_rect = eRect();
    m_dirty_rects.clear();

    // stb_rect_pack requires an array of nodes equal to the width of the atlas
    m_pack_nodes.resize(width);
    stbrp_init_target(&m_pack_context, width, height, m_pack_nodes.data(), m_pack_nodes.size());

    eDebug("[gFontAtlas] initialized %dx%d glyph atlas via stb_rect_pack", width, height);
    return true;
}

void gFontAtlas::release()
{
    m_pixmap = nullptr;
    m_atlas_width = 0;
    m_atlas_height = 0;
    m_is_dirty = false;
    m_dirty_rect = eRect();
    std::vector<eRect>().swap(m_dirty_rects);
    std::vector<stbrp_node>().swap(m_pack_nodes);
    std::unordered_map<glyph_key_t, glyph_uv>().swap(m_glyphs);
}

static long long atlasRectArea(const eRect &rect)
{
    return rect.empty() ? 0 : (long long)rect.width() * (long long)rect.height();
}

static eRect atlasUnionRect(const eRect &a, const eRect &b)
{
    if (a.empty())
        return b;
    if (b.empty())
        return a;

    const int left = std::min(a.left(), b.left());
    const int top = std::min(a.top(), b.top());
    const int right = std::max(a.right(), b.right());
    const int bottom = std::max(a.bottom(), b.bottom());
    return eRect(left, top, right - left, bottom - top);
}

void gFontAtlas::markDirty(const eRect &rect)
{
    eRect clipped = rect & eRect(0, 0, m_atlas_width, m_atlas_height);
    if (clipped.empty())
        return;

    m_dirty_rect = m_is_dirty ? atlasUnionRect(m_dirty_rect, clipped) : clipped;
    m_is_dirty = true;

    for (auto &existing : m_dirty_rects) {
        eRect expanded(existing.left() - 4, existing.top() - 4, existing.width() + 8, existing.height() + 8);
        eRect joined = atlasUnionRect(existing, clipped);
        const long long separate_area = atlasRectArea(existing) + atlasRectArea(clipped);
        const bool close_enough = !(expanded & clipped).empty();
        if (close_enough || atlasRectArea(joined) <= separate_area + 2048) {
            existing = joined;
            return;
        }
    }

    m_dirty_rects.push_back(clipped);
    if (m_dirty_rects.size() > 64) {
        m_dirty_rects.clear();
        m_dirty_rects.push_back(m_dirty_rect);
    }
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

bool gFontAtlas::addGlyph(glyph_key_t key, int width, int height, int pitch, const uint8_t *data, glyph_uv &uv, bool allow_reset)
{
    if (!m_pixmap) return false;
    
    if (width == 0 || height == 0) {
        // Empty space glyph
        uv.u0 = uv.v0 = uv.u1 = uv.v1 = 0.0f;
        uv.width = 0;
        uv.height = 0;
        m_glyphs[key] = uv;
        return true;
    }

    stbrp_rect rect;
    rect.id = 0;
    rect.w = width + 1;
    rect.h = height + 1;

    stbrp_pack_rects(&m_pack_context, &rect, 1);

    // If completely full, rebuild atlas buffer.
    if (!rect.was_packed) {
        if (!allow_reset)
            return false;

        eDebug("[gFontAtlas] ATLAS FULL! Resetting atlas...");
        m_glyphs.clear();
        memset(m_pixmap->surface->data, 0, m_atlas_width * m_atlas_height);

        stbrp_init_target(&m_pack_context, m_atlas_width, m_atlas_height, m_pack_nodes.data(), m_pack_nodes.size());
        stbrp_pack_rects(&m_pack_context, &rect, 1);

        if (!rect.was_packed) {
            eDebug("[gFontAtlas] ERROR: Glyph too large to fit in a completely empty atlas!");
            return false;
        }

        clearDirty();
        markDirty(eRect(0, 0, m_atlas_width, m_atlas_height));
    }

    int px = rect.x;
    int py = rect.y;

    if (!pitch)
        pitch = width;

    uint8_t *dst = (uint8_t *)m_pixmap->surface->data;
    for (int row = 0; row < height; ++row) {
        const uint8_t *src_row = pitch > 0 ? data + (row * pitch) : data + ((height - 1 - row) * -pitch);
        memcpy(dst + ((py + row) * m_atlas_width) + px, src_row, width);
    }

    markDirty(eRect(px, py, width, height));

    // Generate UVs. We use width/height (not the +1 padded sizes) so the quad wraps the glyph perfectly.
    uv.width = width;
    uv.height = height;
    uv.u0 = (float)px / (float)m_atlas_width;
    uv.v0 = (float)py / (float)m_atlas_height;
    uv.u1 = (float)(px + width) / (float)m_atlas_width;
    uv.v1 = (float)(py + height) / (float)m_atlas_height;

    m_glyphs[key] = uv;
    return true;
}
