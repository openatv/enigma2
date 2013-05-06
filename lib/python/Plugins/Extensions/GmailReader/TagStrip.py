# -*- coding: utf-8 -*-
from re import sub

# Entities to be converted
entities = (
	# ISO-8895-1 (most common)
	("&#228;", u"ä"),
	("&auml;", u"ä"),
	("&#252;", u"ü"),
	("&uuml;", u"ü"),
	("&#246;", u"ö"),
	("&ouml;", u"ö"),
	("&#196;", u"Ä"),
	("&Auml;", u"Ä"),
	("&#220;", u"Ü"),
	("&Uuml;", u"Ü"),
	("&#214;", u"Ö"),
	("&Ouml;", u"Ö"),
	("&#223;", u"ß"),
	("&szlig;", u"ß"),

	# Rarely used entities
	("&#8230;", u"..."),
	("&#8211;", u"-"),
	("&#160;", u" "),
	("&#34;", u"\""),
	("&#38;", u"&"),
	("&#39;", u"'"),
	("&#60;", u"<"),
	("&#62;", u">"),

	# Common entities
	("&lt;", u"<"),
	("&gt;", u">"),
	("&nbsp;", u" "),
	("&amp;", u"&"),
	("&quot;", u"\""),
	("&apos;", u"'"),
)

def strip_readable(html):
	# Newlines are rendered as whitespace in html
	html = html.replace('\n', ' ')

	# Multiple whitespaces are rendered as a single one
	html = sub('\s\s+', ' ', html)

	# Replace <br> by newlines
	html = sub('<br(\s+/)?>', '\n', html)

	# Replace <p>, <ul>, <ol> and end of these tags by newline
	html = sub('</?(p|ul|ol)(\s+.*?)?>', '\n', html)

	# Replace <li> by - and </li> by newline
	html = sub('<li(\s+.*?)?>', '-', html)
	html = html.replace('</li>', '\n')

	# And 'normal' stripping
	return strip(html)

def strip(html):
	# Strip enclosed tags
	html = sub('<(.*?)>', '', html)

	# Convert html entities
	for escaped, unescaped in entities:
		html = html.replace(escaped, unescaped)

	# Return result with leading/trailing whitespaces removed
	return html.strip()

