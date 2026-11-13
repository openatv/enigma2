#pragma once

#include <lib/gdi/font.h>
#include <array>
#include <cstdint>
#include <set>
#include <vector>

struct LayoutFont
{
	Font *font;
	FT_Face face;
};

struct PositionedGlyph
{
	size_t visualIndex;
	unsigned int fontIndex, glyph;
	int advance, xOffset, yOffset;
	// Only the first glyph of a cluster participates in line breaking.
	int clusterWidth;
};

bool layoutParagraphs(const std::vector<unsigned long> &logical,
	const std::array<LayoutFont, 3> &fonts, const std::set<int> &forcedReplacement,
	std::vector<unsigned long> &visual, std::vector<bool> &paragraphRtl,
	std::vector<PositionedGlyph> &positioned, const std::vector<int64_t> &logicalColors,
	std::vector<int64_t> &visualColors, std::vector<TextCluster> *clusters = nullptr,
	int lineWidth = 0, int firstLineWidth = 0);
