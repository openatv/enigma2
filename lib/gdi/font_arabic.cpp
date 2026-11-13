#include <lib/gdi/font_arabic.h>
#include <fribidi/fribidi.h>
#include <hb.h>
#include <algorithm>
#include <memory>
#include <numeric>

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

bool shapeRun(const Run &run, const uint32_t *text, int length, hb_font_t *font, HbBuffer &buffer, int64_t &pen,
	std::vector<unsigned long> &visual, std::vector<PositionedGlyph> &positioned,
	const int64_t *colors, std::vector<int64_t> &visualColors, std::vector<TextCluster> &clusters)
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
	for (unsigned int g = 0; g < count;)
	{
		size_t first = positioned.size();
		int clusterStart = pixels(pen);
		unsigned int cluster = info[g].cluster;
		unsigned int next = g + 1;
		while (next < count && info[next].cluster == cluster)
			++next;
		int end = run.level & 1 ? (g ? info[g - 1].cluster : run.end) : (next < count ? info[next].cluster : run.end);
		do
		{
			int x = pixels(pen);
			positioned.push_back({visual.size(), unsigned(run.font), info[g].codepoint,
				pixels(pen + pos[g].x_advance) - x, pixels(pen + pos[g].x_offset) - x,
				-pixels(pos[g].y_offset), -1});
			visual.push_back(text[cluster]);
			clusters.push_back({int(cluster), end, bool(run.level & 1)});
			if (colors)
				visualColors.push_back(colors[cluster]);
			pen += pos[g++].x_advance;
		} while (g < count && info[g].cluster == cluster);
		positioned[first].clusterWidth = pixels(pen) - clusterStart;
	}
	return true;
}

struct Line
{
	std::vector<unsigned long> visual;
	std::vector<PositionedGlyph> positioned;
	std::vector<TextCluster> clusters;
	std::vector<int64_t> colors;
};

bool layoutLine(const uint32_t *text, int length, const FriBidiCharType *types, const FriBidiLevel *paragraphLevels,
	FriBidiParType direction, const std::array<LayoutFont, 3> &fonts, const std::set<int> &forcedReplacement,
	const int64_t *colors, HbBuffer &buffer, Line &line)
{
	line.visual.clear();
	line.positioned.clear();
	line.clusters.clear();
	line.colors.clear();
	std::vector<FriBidiLevel> levels;
	if (length)
		levels.assign(paragraphLevels, paragraphLevels + length);
	std::vector<FriBidiStrIndex> visualToLogical(length);
	std::iota(visualToLogical.begin(), visualToLogical.end(), 0);
	// Bidi levels belong to the paragraph; reorder only after choosing a line.
	if (length && !fribidi_reorder_line(FRIBIDI_FLAG_REORDER_NSM, types, length, 0, direction,
			levels.data(), nullptr, visualToLogical.data()))
		return false;
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

	// Keep fractional advances across colour and font boundaries.
	int64_t pen = 0;
	for (int v = 0; v < length; ++v)
	{
		int logicalIndex = visualToLogical[v];
		int id = runAt[logicalIndex];
		if (id < 0)
		{
			pen = 0;
			FriBidiChar ch = text[logicalIndex];
			if (levels[logicalIndex] & 1)
				fribidi_get_mirror_char(ch, &ch);
			line.visual.push_back(ch);
			line.clusters.push_back({logicalIndex, logicalIndex + 1, bool(levels[logicalIndex] & 1)});
			if (colors)
				line.colors.push_back(colors[logicalIndex]);
			continue;
		}
		auto &run = runs[id];
		if (run.emitted)
			continue;
		run.emitted = true;
		const auto &source = fonts[run.font];
		if (!shapeRun(run, text, length, source.font->getShapingFont(source.face), buffer, pen,
				line.visual, line.positioned, colors, line.colors, line.clusters))
			return false;
	}
	return true;
}

// Measure once in visual order, but accumulate widths at logical cluster starts.
// The ordinary LTR renderer does not enter this path.
int measureLine(const Line &line, const std::array<LayoutFont, 3> &fonts, const std::set<int> &forced,
	std::vector<int> &widths, std::vector<int> &ends, int length)
{
	widths.assign(length, 0);
	ends.resize(length);
	std::iota(ends.begin(), ends.end(), 1);
	size_t positioned = 0;
	int total = 0;
	FT_UInt previous = 0;
	Font *previousFont = nullptr;
	for (size_t i = 0; i < line.visual.size(); ++i)
	{
		int advance = 0;
		if (positioned < line.positioned.size() && line.positioned[positioned].visualIndex == i)
		{
			const auto &glyph = line.positioned[positioned++];
			advance = glyph.advance;
			previous = glyph.glyph;
			previousFont = fonts[glyph.fontIndex].font;
		}
		else
		{
			auto ch = line.visual[i];
			if (ch == '\t')
				advance = fonts[0].font->tabwidth - total % fonts[0].font->tabwidth;
			else if (ch != 0xAD && ch != 0x86 && ch != 0x87 && ch != 0xE086 && ch != 0xE087)
			{
				if (ch == 0x2010)
					ch = '-';
				for (size_t slot = 0; slot < fonts.size(); ++slot)
				{
					const auto &source = fonts[slot];
					if (!source.font || (!slot && forced.count(ch)))
						continue;
					auto glyph = source.font->getCharIndex(ch);
					if (!glyph)
						continue;
					advance = source.font->getGlyphAdvance(source.face, glyph);
					if (previous && previousFont == source.font && FT_HAS_KERNING(source.face))
					{
						FT_Vector delta{};
						FT_Get_Kerning(source.face, previous, glyph, FT_KERNING_DEFAULT, &delta);
						advance += delta.x >> 6;
					}
					previous = glyph;
					previousFont = source.font;
					break;
				}
			}
		}
		const auto &cluster = line.clusters[i];
		widths[cluster.start] += advance;
		ends[cluster.start] = cluster.end;
		total += advance;
	}
	return total;
}

int findLineEnd(const uint32_t *text, int length, const std::vector<int> &widths, const std::vector<int> &ends,
	int start, int available)
{
	int width = 0, breakAt = start;
	for (int i = start; i < length;)
	{
		if (i > start && width + widths[i] > available && text[i] != ' ')
			return breakAt > start ? breakAt : i;
		width += widths[i];
		int next = ends[i];
		if (text[i] == ' ' || text[i] == '-' || text[i] == 0x2010 || text[i] == 0xAD || text[i] == '/')
			breakAt = next;
		i = next;
	}
	return length;
}
}

bool layoutParagraphs(const std::vector<unsigned long> &logical,
	const std::array<LayoutFont, 3> &fonts, const std::set<int> &forcedReplacement,
	std::vector<unsigned long> &visual, std::vector<bool> &paragraphRtl,
	std::vector<PositionedGlyph> &positioned, const std::vector<int64_t> &logicalColors,
	std::vector<int64_t> &visualColors, std::vector<TextCluster> *clusters, int lineWidth, int firstLineWidth)
{
	std::vector<FriBidiChar> input(logical.begin(), logical.end());
	visual.reserve(logical.size());
	HbBuffer buffer(nullptr, hb_buffer_destroy);
	std::vector<FriBidiCharType> types;
	std::vector<FriBidiBracketType> brackets;
	std::vector<FriBidiLevel> levels;
	std::vector<int> widths, ends, checkWidths, checkEnds;
	Line whole, line;
	int available = firstLineWidth > 0 ? firstLineWidth : lineWidth;
	auto appendLine = [&](const Line &value, int offset, bool rtl) {
		for (auto glyph : value.positioned)
		{
			glyph.visualIndex += visual.size();
			positioned.push_back(glyph);
		}
		visual.insert(visual.end(), value.visual.begin(), value.visual.end());
		visualColors.insert(visualColors.end(), value.colors.begin(), value.colors.end());
		if (clusters)
			for (auto cluster : value.clusters)
				clusters->push_back({cluster.start + offset, cluster.end + offset, cluster.rtl});
		paragraphRtl.push_back(rtl);
	};
	auto appendBreak = [&](int position) {
		visual.push_back('\n');
		if (!logicalColors.empty())
			visualColors.push_back(position >= 0 ? logicalColors[position] : -2);
		if (clusters)
			clusters->push_back({position, position >= 0 ? position + 1 : -1, false});
		available = lineWidth;
	};
	for (size_t start = 0; start <= input.size();)
	{
		auto begin = input.begin() + start;
		int length = std::find(begin, input.end(), '\n') - begin;
		FriBidiParType direction = FRIBIDI_PAR_ON;
		const int64_t *colors = logicalColors.empty() ? nullptr : logicalColors.data() + start;
		const auto *text = length ? &*begin : nullptr;
		types.resize(length);
		brackets.resize(length);
		levels.resize(length);
		if (length)
		{
			fribidi_get_bidi_types(text, length, types.data());
			fribidi_get_bracket_types(text, length, types.data(), brackets.data());
			if (!fribidi_get_par_embedding_levels_ex(types.data(), brackets.data(), length, &direction, levels.data()))
				return false;
		}
		if (!layoutLine(text, length, types.data(), levels.data(), direction, fonts, forcedReplacement, colors, buffer, whole))
			return false;
		if (!lineWidth || measureLine(whole, fonts, forcedReplacement, widths, ends, length) <= available)
			appendLine(whole, start, FRIBIDI_IS_RTL(direction));
		else
		{
			for (int first = 0; first < length;)
			{
				int end = findLineEnd(text, length, widths, ends, first, available);
				for (;;)
				{
					// Shape with line-local context so a split word gets correct joining forms.
					if (!layoutLine(text + first, end - first, types.data() + first, levels.data() + first,
							direction, fonts, forcedReplacement, colors ? colors + first : nullptr, buffer, line))
						return false;
					if (end < length && text[end - 1] == 0xAD)
						for (size_t i = 0; i < line.visual.size(); ++i)
							if (line.clusters[i].start == end - first - 1)
								line.visual[i] = 0x2010;
					if (measureLine(line, fonts, forcedReplacement, checkWidths, checkEnds, end - first) <= available)
						break;
					int shorter = first + findLineEnd(text + first, end - first, checkWidths, checkEnds, 0, available);
					if (shorter == end) // A single cluster wider than the line must still be emitted.
						break;
					end = shorter;
				}
				appendLine(line, start + first, FRIBIDI_IS_RTL(direction));
				first = end;
				if (first < length)
					appendBreak(-1);
			}
		}
		start += length;
		if (start == input.size())
			break;
		appendBreak(start);
		++start;
	}
	return true;
}
