/*
 * This was taken from pango. 
 * Modified for enigma by Felix Domke <tmbinc@gmx.net>.
 * I removed support for vowels and ligatures. Sorry.
 *
 * Original header:
 *
 * This is part of Pango - Arabic shaping module 
 *
 * (C) 2000 Karl Koehler <koehler@or.uni-bonn.de>
 * (C) 2001 Roozbeh Pournader <roozbeh@sharif.edu>
 *
 */

#include <vector>
#include <lib/base/eerror.h>

typedef struct
{
	unsigned long basechar;
	int count;
	unsigned long charshape[4];
} shapestruct;

typedef struct
{
	unsigned long basechar;
	char numshapes;
} charstruct;

static void
charstruct_init (charstruct * s)
{
  s->basechar = 0;
  s->numshapes = 1;
}

#define connects_to_left(a)	 ((a).numshapes > 2)

/* The Unicode order is always 'isolated, final, initial, medial'. */

/* *INDENT-OFF* */
static shapestruct chartable[] = {
	{0x0621, 1, {0xFE80}}, /* HAMZA */
	{0x0622, 2, {0xFE81, 0xFE82}}, /* ALEF WITH MADDA ABOVE */
	{0x0623, 2, {0xFE83, 0xFE84}}, /* ALEF WITH HAMZA ABOVE */
	{0x0624, 2, {0xFE85, 0xFE86}}, /* WAW WITH HAMZA ABOVE */
	{0x0625, 2, {0xFE87, 0xFE88}}, /* ALEF WITH HAMZA BELOW */
	{0x0626, 4, {0xFE89, 0xFE8A, 0xFE8B, 0xFE8C}}, /* YEH WITH HAMZA ABOVE */
	{0x0627, 2, {0xFE8D, 0xFE8E}}, /* ALEF */
	{0x0628, 4, {0xFE8F, 0xFE90, 0xFE91, 0xFE92}}, /* BEH */
	{0x0629, 2, {0xFE93, 0xFE94}}, /* TEH MARBUTA */
	{0x062A, 4, {0xFE95, 0xFE96, 0xFE97, 0xFE98}}, /* TEH */
	{0x062B, 4, {0xFE99, 0xFE9A, 0xFE9B, 0xFE9C}}, /* THEH */
	{0x062C, 4, {0xFE9D, 0xFE9E, 0xFE9F, 0xFEA0}}, /* JEEM */
	{0x062D, 4, {0xFEA1, 0xFEA2, 0xFEA3, 0xFEA4}}, /* HAH */
	{0x062E, 4, {0xFEA5, 0xFEA6, 0xFEA7, 0xFEA8}}, /* KHAH */
	{0x062F, 2, {0xFEA9, 0xFEAA}}, /* DAL */
	{0x0630, 2, {0xFEAB, 0xFEAC}}, /* THAL */
	{0x0631, 2, {0xFEAD, 0xFEAE}}, /* REH */
	{0x0632, 2, {0xFEAF, 0xFEB0}}, /* ZAIN */
	{0x0633, 4, {0xFEB1, 0xFEB2, 0xFEB3, 0xFEB4}}, /* SEEN */
	{0x0634, 4, {0xFEB5, 0xFEB6, 0xFEB7, 0xFEB8}}, /* SHEEN */
	{0x0635, 4, {0xFEB9, 0xFEBA, 0xFEBB, 0xFEBC}}, /* SAD */
	{0x0636, 4, {0xFEBD, 0xFEBE, 0xFEBF, 0xFEC0}}, /* DAD */
	{0x0637, 4, {0xFEC1, 0xFEC2, 0xFEC3, 0xFEC4}}, /* TAH */
	{0x0638, 4, {0xFEC5, 0xFEC6, 0xFEC7, 0xFEC8}}, /* ZAH */
	{0x0639, 4, {0xFEC9, 0xFECA, 0xFECB, 0xFECC}}, /* AIN */
	{0x063A, 4, {0xFECD, 0xFECE, 0xFECF, 0xFED0}}, /* GHAIN */
	{0x0640, 4, {0x0640, 0x0640, 0x0640, 0x0640}}, /* TATWEEL */
	{0x0641, 4, {0xFED1, 0xFED2, 0xFED3, 0xFED4}}, /* FEH */
	{0x0642, 4, {0xFED5, 0xFED6, 0xFED7, 0xFED8}}, /* QAF */
	{0x0643, 4, {0xFED9, 0xFEDA, 0xFEDB, 0xFEDC}}, /* KAF */
	{0x0644, 4, {0xFEDD, 0xFEDE, 0xFEDF, 0xFEE0}}, /* LAM */
	{0x0645, 4, {0xFEE1, 0xFEE2, 0xFEE3, 0xFEE4}}, /* MEEM */
	{0x0646, 4, {0xFEE5, 0xFEE6, 0xFEE7, 0xFEE8}}, /* NOON */
	{0x0647, 4, {0xFEE9, 0xFEEA, 0xFEEB, 0xFEEC}}, /* HEH */
	{0x0648, 2, {0xFEED, 0xFEEE}}, /* WAW */
	{0x0649, 4, {0xFEEF, 0xFEF0, 0xFBE8, 0xFBE9}}, /* ALEF MAKSURA */
	{0x064A, 4, {0xFEF1, 0xFEF2, 0xFEF3, 0xFEF4}}, /* YEH */
	{0x0671, 2, {0xFB50, 0xFB51}}, /* ALEF WASLA */
	{0x0679, 4, {0xFB66, 0xFB67, 0xFB68, 0xFB69}}, /* TTEH */
	{0x067A, 4, {0xFB5E, 0xFB5F, 0xFB60, 0xFB61}}, /* TTEHEH */
	{0x067B, 4, {0xFB52, 0xFB53, 0xFB54, 0xFB55}}, /* BEEH */
	{0x067E, 4, {0xFB56, 0xFB57, 0xFB58, 0xFB59}}, /* PEH */
	{0x067F, 4, {0xFB62, 0xFB63, 0xFB64, 0xFB65}}, /* TEHEH */
	{0x0680, 4, {0xFB5A, 0xFB5B, 0xFB5C, 0xFB5D}}, /* BEHEH */
	{0x0683, 4, {0xFB76, 0xFB77, 0xFB78, 0xFB79}}, /* NYEH */
	{0x0684, 4, {0xFB72, 0xFB73, 0xFB74, 0xFB75}}, /* DYEH */
	{0x0686, 4, {0xFB7A, 0xFB7B, 0xFB7C, 0xFB7D}}, /* TCHEH */
	{0x0687, 4, {0xFB7E, 0xFB7F, 0xFB80, 0xFB81}}, /* TCHEHEH */
	{0x0688, 2, {0xFB88, 0xFB89}}, /* DDAL */
	{0x068C, 2, {0xFB84, 0xFB85}}, /* DAHAL */
	{0x068D, 2, {0xFB82, 0xFB83}}, /* DDAHAL */
	{0x068E, 2, {0xFB86, 0xFB87}}, /* DUL */
	{0x0691, 2, {0xFB8C, 0xFB8D}}, /* RREH */
	{0x0698, 2, {0xFB8A, 0xFB8B}}, /* JEH */
	{0x06A4, 4, {0xFB6A, 0xFB6B, 0xFB6C, 0xFB6D}}, /* VEH */
	{0x06A6, 4, {0xFB6E, 0xFB6F, 0xFB70, 0xFB71}}, /* PEHEH */
	{0x06A9, 4, {0xFB8E, 0xFB8F, 0xFB90, 0xFB91}}, /* KEHEH */
	{0x06AD, 4, {0xFBD3, 0xFBD4, 0xFBD5, 0xFBD6}}, /* NG */
	{0x06AF, 4, {0xFB92, 0xFB93, 0xFB94, 0xFB95}}, /* GAF */
	{0x06B1, 4, {0xFB9A, 0xFB9B, 0xFB9C, 0xFB9D}}, /* NGOEH */
	{0x06B3, 4, {0xFB96, 0xFB97, 0xFB98, 0xFB99}}, /* GUEH */
	{0x06BB, 4, {0xFBA0, 0xFBA1, 0xFBA2, 0xFBA3}}, /* RNOON */
	{0x06BE, 4, {0xFBAA, 0xFBAB, 0xFBAC, 0xFBAD}}, /* HEH DOACHASHMEE */
	{0x06C0, 2, {0xFBA4, 0xFBA5}}, /* HEH WITH YEH ABOVE */
	{0x06C1, 4, {0xFBA6, 0xFBA7, 0xFBA8, 0xFBA9}}, /* HEH GOAL */
	{0x06C5, 2, {0xFBE0, 0xFBE1}}, /* KIRGHIZ OE */
	{0x06C6, 2, {0xFBD9, 0xFBDA}}, /* OE */
	{0x06C7, 2, {0xFBD7, 0xFBD8}}, /* U */
	{0x06C8, 2, {0xFBDB, 0xFBDC}}, /* YU */
	{0x06C9, 2, {0xFBE2, 0xFBE3}}, /* KIRGHIZ YU */
	{0x06CB, 2, {0xFBDE, 0xFBDF}}, /* VE */
	{0x06CC, 4, {0xFBFC, 0xFBFD, 0xFBFE, 0xFBFF}}, /* FARSI YEH */
	{0x06D0, 4, {0xFBE4, 0xFBE5, 0xFBE6, 0xFBE7}}, /* E */
	{0x06D2, 2, {0xFBAE, 0xFBAF}}, /* YEH BARREE */
	{0x06D3, 2, {0xFBB0, 0xFBB1}}, /* YEH BARREE WITH HAMZA ABOVE */
};

#define ALEF					 0x0627
#define ALEFHAMZA			0x0623
#define ALEFHAMZABELOW 0x0625
#define ALEFMADDA			0x0622
#define LAM						0x0644
#define HAMZA					0x0621
#define TATWEEL				0x0640
#define ZWJ						0x200D

#define HAMZAABOVE	0x0654
#define HAMZABELOW	0x0655

#define WAWHAMZA		0x0624
#define YEHHAMZA		0x0626
#define WAW				 0x0648
#define ALEFMAKSURA 0x0649
#define YEH				 0x064A
#define FARSIYEH		0x06CC

#define SHADDA			0x0651
#define KASRA			 0x0650
#define FATHA			 0x064E
#define DAMMA			 0x064F
#define MADDA			 0x0653

#define LAM_ALEF					 0xFEFB
#define LAM_ALEFHAMZA			0xFEF7
#define LAM_ALEFHAMZABELOW 0xFEF9
#define LAM_ALEFMADDA			0xFEF5

static short
shapecount (unsigned long s)
{
  int l, r, m;
  if ((s >= 0x0621) && (s <= 0x06D3))
    {
      l = 0;
      r = sizeof (chartable) / sizeof (shapestruct);
      while (l <= r)
        {
          m = (l + r) / 2;
          if (s == chartable[m].basechar)
            {
              return chartable[m].count;
            }
          else if (s < chartable[m].basechar)
            {
              r = m - 1;
            }
          else
            {
              l = m + 1;
            }
        }
    }
  else if (s == ZWJ)
    {
      return 4;
    }
  return 1;
}

static unsigned long
charshape (unsigned long s, int which)
/* which 0=isolated 1=final 2=initial 3=medial */
{
	int l, r, m;
	if ((s >= 0x0621) && (s <= 0x06D3))
		{
			l = 0;
			r = sizeof (chartable) / sizeof (shapestruct);
			while (l <= r)
				{
					m = (l + r) / 2;
					if (s == chartable[m].basechar)
						{
							return chartable[m].charshape[which];
						}
					else if (s < chartable[m].basechar)
						{
							r = m - 1;
						}
					else
						{
							l = m + 1;
						}
				}
		}
	else if ((s >= 0xFEF5) && (s <= 0xFEFB))
		{													 /* Lam+Alef */
			return s + which;
		}

	return s;
}

void
shape (std::vector<unsigned long> &string, const std::vector<unsigned long> &text)
{
	string.reserve(text.size());

	charstruct oldchar, curchar;
	int which;
	unsigned long nextletter;

	charstruct_init (&oldchar);
	charstruct_init (&curchar);
	
	for (std::vector<unsigned long>::const_iterator i(text.begin());
			i != text.end(); ++i)
	{
		nextletter = *i;
		int nc = shapecount (nextletter);
		
		if (nc == 1)
			which = 0;				/* final or isolated */
		else
			which = 2;				/* medial or initial */
		if (connects_to_left (oldchar))
			which++;
		which = which % (curchar.numshapes);
		curchar.basechar = charshape (curchar.basechar, which);
			/* get rid of oldchar */
		if (oldchar.basechar)
			string.push_back(oldchar.basechar);
		oldchar = curchar;		/* new values in oldchar */

			/* init new curchar */
		charstruct_init (&curchar);
		curchar.basechar = nextletter;
		curchar.numshapes = nc;
	}

	/* Handle last char */
	if (connects_to_left (oldchar))
		which = 1;
	else
		which = 0;
	which = which % (curchar.numshapes);
	curchar.basechar = charshape (curchar.basechar, which);

	if (oldchar.basechar != 0)
		string.push_back(oldchar.basechar);
	if (curchar.basechar != 0)
		string.push_back(curchar.basechar);
}
