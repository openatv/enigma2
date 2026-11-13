#include <lib/gdi/font_arabic.h>
#include <fribidi/fribidi.h>
#include <hb-ft.h>
#include <hb-ot.h>
#include <algorithm>
#include <memory>

// renderString holds ftlock while shaping. Keep one font per registered face,
// sharing its OpenType tables across labels without retaining rendered text.
hb_font_t *Font::getShapingFont(FT_Face face) const
{
	auto *entry = static_cast<fontRenderClass::fontListEntry *>(scaler.face_id);
	if (!entry->shapingFont)
	{
		hb_face_t *hbFace = hb_ft_face_create_referenced(face);
		entry->shapingFont = hb_font_create(hbFace);
		hb_face_destroy(hbFace);
		hb_ot_font_set_funcs(entry->shapingFont);
	}
	unsigned int width, height;
	hb_font_get_ppem(entry->shapingFont, &width, &height);
	if (width != scaler.width || height != scaler.height)
	{
		hb_font_set_scale(entry->shapingFont, scaler.width * 64, scaler.height * 64);
		hb_font_set_ppem(entry->shapingFont, scaler.width, scaler.height);
	}
	return entry->shapingFont;
}

namespace
{
using HbBuffer = std::unique_ptr<hb_buffer_t, decltype(&hb_buffer_destroy)>;

bool arabic(uint32_t c)
{
	if (c < 0x0600)
		return false;
	return hb_unicode_script(hb_unicode_funcs_get_default(), c) == HB_SCRIPT_ARABIC ||
		c == 0x0640 || (c >= 0x064B && c <= 0x065F) || c == 0x0670;
}

bool mark(uint32_t c)
{
	auto category = hb_unicode_general_category(hb_unicode_funcs_get_default(), c);
	return category == HB_UNICODE_GENERAL_CATEGORY_NON_SPACING_MARK ||
		category == HB_UNICODE_GENERAL_CATEGORY_SPACING_MARK ||
		category == HB_UNICODE_GENERAL_CATEGORY_ENCLOSING_MARK;
}

bool joinControl(uint32_t c)
{
	return c == 0x200C || c == 0x200D;
}

// Prefer a face covering both the base and its marks. If none does, keep
// the base and the visible missing-glyph indication together.
int clusterFont(const uint32_t *text, int length, const std::array<LayoutFont, 3> &fonts,
	const std::set<int> &forced)
{
	bool replace = std::any_of(text, text + length, [&](uint32_t c) { return forced.count(c); });
	int first = replace && (fonts[1].face || fonts[2].face) ? 1 : 0;
	int base = -1;
	for (int i = first; i < int(fonts.size()); ++i)
	{
		auto *font = fonts[i].font;
		if (!font || (!joinControl(text[0]) && !font->getCharIndex(text[0])))
			continue;
		if (base < 0)
			base = i;
		if (std::all_of(text + 1, text + length, [font](uint32_t c) {
			return joinControl(c) || font->getCharIndex(c);
		}))
			return i;
	}
	if (base >= 0)
		return base;
	return fonts[first].face ? first : 2;
}

struct Run
{
	int start, end, font;
	FriBidiLevel level;
	bool emitted = false;
};

int pixels(int64_t value)
{
	return (value + 32) >> 6;
}

bool shapeRun(const Run &run, const uint32_t *text, int length, hb_font_t *font, HbBuffer &buffer,
	std::vector<unsigned long> &visual, std::vector<PositionedGlyph> &positioned,
	const int64_t *colors, std::vector<int64_t> &visualColors)
{
	if (!buffer)
		buffer.reset(hb_buffer_create());
	hb_buffer_reset(buffer.get());
	hb_buffer_set_direction(buffer.get(), (run.level & 1) ? HB_DIRECTION_RTL : HB_DIRECTION_LTR);
	hb_buffer_set_script(buffer.get(), HB_SCRIPT_ARABIC);
	hb_buffer_add_codepoints(buffer.get(), text, length, run.start, run.end - run.start);
	hb_shape(font, buffer.get(), nullptr, 0);
	if (!hb_buffer_allocation_successful(buffer.get()))
		return false;
	unsigned int count;
	auto info = hb_buffer_get_glyph_infos(buffer.get(), &count);
	auto pos = hb_buffer_get_glyph_positions(buffer.get(), nullptr);
	int64_t pen = 0;
	for (unsigned int g = 0; g < count;)
	{
		size_t first = positioned.size();
		int clusterStart = pixels(pen);
		unsigned int cluster = info[g].cluster;
		do
		{
			int x = pixels(pen);
			positioned.push_back({visual.size(), unsigned(run.font), info[g].codepoint,
				pixels(pen + pos[g].x_advance) - x, pixels(pen + pos[g].x_offset) - x,
				-pixels(pos[g].y_offset), -1});
			visual.push_back(text[cluster]);
			if (colors)
				visualColors.push_back(colors[cluster]);
			pen += pos[g++].x_advance;
		} while (g < count && info[g].cluster == cluster);
		positioned[first].clusterWidth = pixels(pen) - clusterStart;
	}
	return true;
}
}

bool layoutParagraphs(const std::vector<unsigned long> &logical,
	const std::array<LayoutFont, 3> &fonts, const std::set<int> &forcedReplacement,
	std::vector<unsigned long> &visual, std::vector<bool> &paragraphRtl,
	std::vector<PositionedGlyph> &positioned, const std::vector<int64_t> &logicalColors,
	std::vector<int64_t> &visualColors)
{
	std::vector<FriBidiChar> input(logical.begin(), logical.end());
	visual.reserve(logical.size());
	HbBuffer buffer(nullptr, hb_buffer_destroy);
	for (size_t start = 0; start <= input.size();)
	{
		auto begin = input.begin() + start;
		int length = std::find(begin, input.end(), '\n') - begin;
		FriBidiParType direction = FRIBIDI_PAR_ON;
		std::vector<FriBidiChar> reordered(length);
		std::vector<FriBidiStrIndex> visualToLogical(length);
		std::vector<FriBidiLevel> levels(length);
		const int64_t *colors = logicalColors.empty() ? nullptr : logicalColors.data() + start;
		const auto *text = length ? &*begin : nullptr;
		if (length && !fribidi_log2vis(text, length, &direction, reordered.data(),
				nullptr, visualToLogical.data(), levels.data()))
			return false;
		paragraphRtl.push_back(FRIBIDI_IS_RTL(direction));

		std::vector<Run> runs;
		std::vector<int> runAt(length, -1);
		for (int i = 0; i < length;)
		{
			int base = i++;
			if (!arabic(text[base]) && !(joinControl(text[base]) && i < length && arabic(text[i])))
				continue;
			while (i < length && levels[i] == levels[base] && (mark(text[i]) || joinControl(text[i])))
				++i;
			int slot = clusterFont(text + base, i - base, fonts, forcedReplacement);
			if (!runs.empty() && runs.back().end == base && runs.back().font == slot &&
					runs.back().level == levels[base] && (!colors || colors[runs.back().start] == colors[base]))
				runs.back().end = i;
			else
				runs.push_back({base, i, slot, levels[base]});
			std::fill(runAt.begin() + base, runAt.begin() + i, int(runs.size()) - 1);
		}

		for (int v = 0; v < length; ++v)
		{
			int id = runAt[visualToLogical[v]];
			if (id < 0)
			{
				visual.push_back(reordered[v]);
				if (colors)
					visualColors.push_back(colors[visualToLogical[v]]);
				continue;
			}
			auto &run = runs[id];
			if (run.emitted)
				continue;
			run.emitted = true;
			const auto &source = fonts[run.font];
			if (!shapeRun(run, text, length, source.font->getShapingFont(source.face), buffer, visual, positioned, colors, visualColors))
				return false;
		}
		start += length;
		if (start == input.size())
			break;
		visual.push_back('\n');
		if (!logicalColors.empty())
			visualColors.push_back(logicalColors[start]);
		++start;
	}
	return true;
}
