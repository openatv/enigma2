# -*- coding: UTF-8 -*-

from gettext import bindtextdomain, install, textdomain, translation
from locale import Error as LocaleError, LC_ALL, LC_COLLATE, LC_CTYPE, LC_MESSAGES, LC_MONETARY, LC_NUMERIC, LC_TIME, setlocale, getlocale
from os import environ, listdir
from os.path import isdir
from six import PY2
from subprocess import Popen, PIPE
from time import localtime, strftime, time

from Tools.CountryCodes import setISO3166
from Tools.Directories import SCOPE_LANGUAGE, resolveFilename

PACKAGER = "/usr/bin/opkg"
PACKAGE_TEMPLATE = "enigma2-locale-%s"

languagePath = resolveFilename(SCOPE_LANGUAGE)
try:
	if PY2:
		install("enigma2", languagePath, unicode=False, codeset="UTF-8", names=("ngettext", "pgettext"))
	else:
		install("enigma2", languagePath, names=("ngettext", "pgettext"))
except UnicodeDecodeError:
	print("[International] Error: The language translation data in '%s' has failed to initialise!  Translations are not possible." % languagePath)
	install("enigma2", "/", names=("ngettext", "pgettext"))
bindtextdomain("enigma2", languagePath)
textdomain("enigma2")

LANG_NAME = 0
LANG_TRANSLATED = 1
LANG_NATIVE = 2
LANG_ENCODING = 3
LANG_COUNTRYCODES = 4
LANG_MAX = 4

# In this code the following meanings are used:
# 	Country: An official country as recognised by ISO, eg "AU" for Australia.
# 	Language: An official language as recognised by ISO, eg "en" for English.
# 	Locale: An official language as spoken in a country, eg "en_AU" for English (Australian).

LANGUAGE_DATA = {
	# DEVELOPER NOTE:
	#
	# Should this language table include the ISO three letter code for use in the subtitle code?
	# Perhaps also have a flag to indicate that the language should be listed in the subtitle list?
	#
	# Fields: English Name, Translated Name, Localised Name, Encoding
	# 	Character Set, (Tuple of ISO-3166 Alpha2 Country Codes).
	#		NOTE: The first item of the tuple should be the
	# 		default or commonly known country for the language.
	# To make managing this list easier please keep languages in ISO
	# 639-2 Code order.  Language codes should be in lower case and
	# country codes should be in upper case.  Be careful not to 
	# confuse / mix the language and country!
	#
	# The Character Set entry is only used to set a shell variable used
	# by Gstreamer.
	#
	# As noted above, if a language is used in more than one country then
	# the default locale contry should be listed first.
	#
	# https://www.loc.gov/standards/iso639-2/php/code_list.php
	# https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes
	# https://lh.2xlibre.net/locales/
	"aa": ("Afar", _("Afar"), "Afaraf", "UTF-8", ("DJ", "ER", "ET")),
	"ab": ("Abkhazian", _("Abkhazian"), "Аҧсуа Бызшәа / Аҧсшәа", "UTF-8", ()),
	"ae": ("Avestan", _("Avestan"), "Avesta", "UTF-8", ()),
	"af": ("Afrikaans", _("Afrikaans"), "Afrikaans", "UTF-8", ("ZA",)),
	"ak": ("Akan", _("Akan"), "Akan", "UTF-8", ("GH",)),
	"am": ("Amharic", _("Amharic"), "አማርኛ", "UTF-8", ("ET",)),
	"an": ("Aragonese", _("Aragonese"), "Aragonés", "UTF-8", ("ES",)),
	"ar": ("Arabic", _("Arabic"), "العربية", "ISO-8859-15", ("AE", "BH", "DZ", "EG", "IN", "IQ", "JO", "KW", "LB", "LY", "MA", "OM", "QA", "SA", "SD", "SS", "SY", "TN", "YE")),
	"as": ("Assamese", _("Assamese"), "অসমীয়া", "UTF-8", ("IN",)),
	"av": ("Avaric", _("Avaric"), "Авар мацӀ / МагӀарул мацӀ", "UTF-8", ()),
	"ay": ("Aymara", _("Aymara"), "Aymar Aru", "UTF-8", ("PE",)),
	"az": ("Azerbaijani", _("Azerbaijani"), "Azərbaycan Dili", "UTF-8", ("AZ", "IR")),
	"ba": ("Bashkir", _("Bashkir"), "башҡорт теле", "UTF-8", ()),
	"be": ("Belarusian", _("Belarusian"), "беларуская мова", "UTF-8", ("BY",)),
	"bg": ("Bulgarian", _("Bulgarian"), "български език", "ISO-8859-15", ("BG",)),
	"bh": ("Bihari languages", _("Bihari languages"), "भोजपुरी", "UTF-8", ()),
	"bi": ("Bislama", _("Bislama"), "Bislama", "UTF-8", ("TV", "VU")),
	"bm": ("Bambara", _("Bambara"), "Bamanankan", "UTF-8", ("ML",)),
	"bn": ("Bengali", _("Bengali"), "বাংলা", "UTF-8", ("BD", "IN")),
	"bo": ("Tibetan", _("Tibetan"), "བོད་ཡིག", "UTF-8", ("CN", "IN")),
	"br": ("Breton", _("Breton"), "Brezhoneg", "UTF-8", ("FR",)),
	"bs": ("Bosnian", _("Bosnian"), "Bosanski Jezik", "UTF-8", ("BA",)),
	"ca": ("Catalan / Valencian", _("Catalan / Valencian"), "Català / Valencià", "ISO-8859-15", ("AD", "ES", "FR", "IT")),
	"ce": ("Chechen", _("Chechen"), "Нохчийн Мотт", "UTF-8", ("RU",)),
	"ch": ("Chamorro", _("Chamorro"), "Chamoru", "UTF-8", ()),
	"co": ("Corsican", _("Corsican"), "Corsu, Lingua Corsa", "UTF-8", ()),
	"cr": ("Cree", _("Cree"), "ᓀᐦᐃᔭᐍᐏᐣ", "UTF-8", ()),
	"cs": ("Czech", _("Czech"), "Čeština / Český Jazyk", "ISO-8859-15", ("CZ",)),
	"cu": ("Church Slavic", _("Church Slavic"), "Ѩзыкъ Словѣньскъ", "UTF-8", ()),
	"cv": ("Chuvash", _("Chuvash"), "Чӑваш Чӗлхи", "UTF-8", ("RU",)),
	"cy": ("Welsh", _("Welsh"), "Cymraeg", "UTF-8", ("GB",)),
	"da": ("Danish", _("Danish"), "Dansk", "ISO-8859-15", ("DK",)),
	"de": ("German", _("German"), "Deutsch", "ISO-8859-15", ("DE", "AT", "BE", "CH", "IT", "LI", "LU")),
	"dv": ("Divehi / Dhivehi / Maldivian", _("Divehi / Dhivehi / Maldivian"), "ދިވެހި", "UTF-8", ("MV",)),
	"dz": ("Dzongkha", _("Dzongkha"), "རྫོང་ཁ", "UTF-8", ("BT",)),
	"ee": ("Ewe", _("Ewe"), "Eʋegbe", "UTF-8", ()),
	"el": ("Greek", _("Greek"), "Ελληνικά", "ISO-8859-7", ("GR", "CY")),
	"en": ("English", _("English"), "English", "ISO-8859-15", ("US", "AG", "AU", "BW", "BZ", "CA", "DK", "GB", "HK", "IE", "IL", "IN", "JM", "KH", "NG", "NZ", "PH", "SC", "SG", "TT", "ZA", "ZM", "ZW")),
	"eo": ("Esperanto", _("Esperanto"), "Esperanto", "UTF-8", ()),
	"es": ("Spanish / Castilian", _("Spanish / Castilian"), "Español", "ISO-8859-15", ("ES", "AR", "BO", "CL", "CO", "CR", "CU", "DO", "EC", "GT", "HN", "MX", "NI", "PA", "PE", "PR", "PY", "SV", "US", "UY", "VE")),
	"et": ("Estonian", _("Estonian"), "Eesti / Eesti keel", "ISO-8859-15", ("EE",)),
	"eu": ("Basque", _("Basque"), "Euskara / Euskera", "UTF-8", ("ES",)),
	"fa": ("Farsi / Persian", _("Farsi / Persian"), "فارسی", "ISO-8859-15", ("IR",)),
	"ff": ("Fulah", _("Fulah"), "Fulfulde / Pulaar / Pular", "UTF-8", ("SN",)),
	"fi": ("Finnish", _("Finnish"), "Suomi / Suomen kieli", "ISO-8859-15", ("FI",)),
	"fj": ("Fijian", _("Fijian"), "Vosa Vakaviti", "UTF-8", ()),
	"fo": ("Faroese", _("Faroese"), "Føroyskt", "UTF-8", ("FO",)),
	"fr": ("French", _("French"), "Français", "ISO-8859-15", ("FR", "AG", "AI", "BE", "BB", "BS", "CA", "CG", "CH", "CI", "CM", "CU", "DO", "DM", "GD", "GY", "HT", "JM", "KN", "LC", "LU", "MA", "MC", "ML", "MQ", "PR", "SN", "SR", "SX", "TT", "VC", "VI")),
	"fy": ("Western Frisian", _("Western Frisian"), "Frysk", "ISO-8859-15", ("NL", "DE")),
	"ga": ("Irish", _("Irish"), "Gaeilge", "UTF-8", ("IE",)),
	"gd": ("Gaelic", _("Gaelic"), "Gàidhlig", "UTF-8", ("GB",)),
	"gl": ("Galician", _("Galician"), "Galego", "UTF-8", ("ES",)),
	"gn": ("Guarani", _("Guarani"), "Avañe'ẽ", "UTF-8", ("PY",)),
	"gu": ("Gujarati", _("Gujarati"), "ગુજરાતી", "UTF-8", ("IN",)),
	"gv": ("Manx", _("Manx"), "Gaelg / Gailck", "UTF-8", ("GB",)),
	"ha": ("Hausa", _("Hausa"), "هَوُسَ", "UTF-8", ("NG",)),
	"he": ("Hebrew", _("Hebrew"), "עברית‎", "ISO-8859-15", ("IL",)),
	"hi": ("Hindi", _("Hindi"), "हिन्दी / हिंदी", "UTF-8", ("IN",)),
	"ho": ("Hiri Motu", _("Hiri Motu"), "Hiri Motu", "UTF-8", ()),
	"hr": ("Croatian", _("Croatian"), "Hrvatski Jezik", "ISO-8859-15", ("HR",)),
	"ht": ("Haitian / Haitian Creole", _("Haitian / Haitian Creole"), "Kreyòl ayisyen", "UTF-8", ("HT",)),
	"hu": ("Hungarian", _("Hungarian"), "Magyar", "ISO-8859-15", ("HU",)),
	"hy": ("Armenian", _("Armenian"), "Հայերեն", "UTF-8", ("AM",)),
	"hz": ("Herero", _("Herero"), "Otjiherero", "UTF-8", ()),
	"ia": ("Interlingua", _("Interlingua"), "Interlingua", "UTF-8", ("FR",)),
	"id": ("Indonesian", _("Indonesian"), "Bahasa Indonesia", "ISO-8859-15", ("ID",)),
	"ie": ("Interlingue / Occidental", _("Interlingue / Occidental"), "Interlingue", "UTF-8", ()),
	"ig": ("Igbo", _("Igbo"), "Asụsụ Igbo", "UTF-8", ("NG",)),
	"ii": ("Sichuan Yi / Nuosu", _("Sichuan Yi / Nuosu"), "ꆈꌠ꒿ Nuosuhxop", "UTF-8", ()),
	"ik": ("Inupiaq", _("Inupiaq"), "Iñupiaq / Iñupiatun", "UTF-8", ("CA",)),
	"io": ("Ido", _("Ido"), "Ido", "UTF-8", ()),
	"is": ("Icelandic", _("Icelandic"), "Íslenska", "ISO-8859-15", ("IS",)),
	"it": ("Italian", _("Italian"), "Italiano", "ISO-8859-15", ("IT", "CH")),
	"iu": ("Inuktitut", _("Inuktitut"), "ᐃᓄᒃᑎᑐᑦ", "UTF-8", ("CA",)),
	"ja": ("Japanese", _("Japanese"), "日本語 (にほんご)", "UTF-8", ("JP",)),
	"jv": ("Javanese", _("Javanese"), "ꦧꦱꦗꦮ / Basa Jawa", "UTF-8", ()),
	"ka": ("Georgian", _("Georgian"), "ქართული", "UTF-8", ("GE",)),
	"kg": ("Kongo", _("Kongo"), "Kikongo", "UTF-8", ()),
	"ki": ("Kikuyu / Gikuyu", _("Kikuyu / Gikuyu"), "Gĩkũyũ", "UTF-8", ()),
	"kj": ("Kuanyama / Kwanyama", _("Kuanyama / Kwanyama"), "Kuanyama", "UTF-8", ()),
	"kk": ("Kazakh", _("Kazakh"), "Қазақ тілі", "UTF-8", ("KZ",)),
	"kl": ("Kalaallisut / Greenlandic", _("Kalaallisut / Greenlandic"), "Kalaallisut / Kalaallit oqaasii", "UTF-8", ("GL",)),
	"km": ("Central Khmer", _("Central Khmer"), "ខ្មែរ, ខេមរភាសា, ភាសាខ្មែរ", "UTF-8", ("KH",)),
	"kn": ("Kannada", _("Kannada"), "ಕನ್ನಡ", "UTF-8", ("IN",)),
	"ko": ("Korean", _("Korean"), "한국어", "UTF-8", ("KR",)),
	"kr": ("Kanuri", _("Kanuri"), "Kanuri", "UTF-8", ()),
	"ks": ("Kashmiri", _("Kashmiri"), "कश्मीरी / كشميري", "UTF-8", ("IN",)),
	"ku": ("Kurdish", _("Kurdish"), "Kurdî / کوردی", "ISO-8859-15", ("TR",)),
	"kv": ("Komi", _("Komi"), "Коми кыв", "UTF-8", ()),
	"kw": ("Cornish", _("Cornish"), "Kernewek", "UTF-8", ("GB",)),
	"ky": ("Kirghiz / Kyrgyz", _("Kirghiz / Kyrgyz"), "Кыргызча, Кыргыз тили", "UTF-8", ("KG",)),
	"la": ("Latin", _("Latin"), "Latine / Lingua Latina", "UTF-8", ()),
	"lb": ("Luxembourgish / Letzeburgesch", _("Luxembourgish / Letzeburgesch"), "Lëtzebuergesch", "UTF-8", ("LU",)),
	"lg": ("Ganda", _("Ganda"), "Luganda", "UTF-8", ("UG",)),
	"li": ("Limburgan / Limburger / Limburgish", _("Limburgan / Limburger / Limburgish"), "Limburgs", "UTF-8", ("BE", "NL")),
	"ln": ("Lingala", _("Lingala"), "Lingála", "UTF-8", ("CD",)),
	"lo": ("Lao", _("Lao"), "ພາສາລາວ", "UTF-8", ("LA",)),
	"lt": ("Lithuanian", _("Lithuanian"), "Lietuvių Kalba", "ISO-8859-15", ("LT",)),
	"lu": ("Luba-Katanga", _("Luba-Katanga"), "Kiluba", "UTF-8", ()),
	"lv": ("Latvian", _("Latvian"), "Latviešu Valoda", "ISO-8859-15", ("LV",)),
	"mg": ("Malagasy", _("Malagasy"), "Fiteny Malagasy", "UTF-8", ("MG",)),
	"mh": ("Marshallese", _("Marshallese"), "Kajin M̧ajeļ", "UTF-8", ("MH",)),
	"mi": ("Maori", _("Maori"), "te reo Māori", "UTF-8", ("NZ",)),
	"mk": ("Macedonian", _("Macedonian"), "Македонски Јазик", "UTF-8", ("MK",)),
	"ml": ("Malayalam", _("Malayalam"), "മലയാളം", "UTF-8", ("IN",)),
	"mn": ("Mongolian", _("Mongolian"), "Монгол хэл", "UTF-8", ("MN",)),
	"mr": ("Marathi", _("Marathi"), "मराठी", "UTF-8", ("IN",)),
	"ms": ("Malay", _("Malay"), "Bahasa Melayu, بهاس ملايو", "UTF-8", ("MY",)),
	"mt": ("Maltese", _("Maltese"), "Malti", "UTF-8", ("MT",)),
	"my": ("Burmese", _("Burmese"), "ဗမာစာ", "UTF-8", ("MM",)),
	"na": ("Nauru", _("Nauru"), "Dorerin Naoero", "UTF-8", ()),
	"nb": ("Norwegian Bokml", _("Norwegian Bokml"), "Norsk Bokmål", "ISO-8859-15", ("NO",)),
	"nd": ("North Ndebele", _("North Ndebele"), "isiNdebele", "UTF-8", ()),
	"ne": ("Nepali", _("Nepali"), "नेपाली", "UTF-8", ("NP",)),
	"ng": ("Ndonga", _("Ndonga"), "Owambo", "UTF-8", ()),
	"nl": ("Dutch / Flemish", _("Dutch / Flemish"), "Nederlands / Vlaams", "ISO-8859-15", ("NL", "AW", "BE")),
	"nn": ("Norwegian Nynorsk", _("Norwegian Nynorsk"), "Norsk Nynorsk", "UTF-8", ("NO",)),
	"no": ("Norwegian", _("Norwegian"), "Norsk", "ISO-8859-15", ("NO",)),
	"nr": ("South Ndebele", _("South Ndebele"), "isiNdebele", "UTF-8", ("ZA",)),
	"nv": ("Navajo / Navaho", _("Navajo / Navaho"), "Diné bizaad", "UTF-8", ()),
	"ny": ("Chichewa / Chewa / Nyanja", _("Chichewa / Chewa / Nyanja"), "ChiCheŵa / Chinyanja", "UTF-8", ()),
	"oc": ("Occitan", _("Occitan"), "Occitan / Lenga D'òc", "UTF-8", ("FR",)),
	"oj": ("Ojibwa", _("Ojibwa"), "ᐊᓂᔑᓈᐯᒧᐎᓐ", "UTF-8", ()),
	"om": ("Oromo", _("Oromo"), "Afaan Oromoo", "UTF-8", ("ET", "KE")),
	"or": ("Oriya", _("Oriya"), "ଓଡ଼ିଆ", "UTF-8", ("IN",)),
	"os": ("Ossetian / Ossetic", _("Ossetian / Ossetic"), "Ирон Æвзаг", "UTF-8", ("RU",)),
	"pa": ("Panjabi / Punjabi", _("Panjabi / Punjabi"), "ਪੰਜਾਬੀ, پنجابی", "UTF-8", ("IN", "PK")),
	"pi": ("Pali", _("Pali"), "पालि, पाळि", "UTF-8", ()),
	"pl": ("Polish", _("Polish"), "Język Polski, Polszczyzna", "ISO-8859-15", ("PL",)),
	"ps": ("Pushto / Pashto", _("Pushto / Pashto"), "پښتو", "UTF-8", ("AF",)),
	"pt": ("Portuguese", _("Portuguese"), "Português", "ISO-8859-15", ("PT", "BR")),
	"qu": ("Quechua", _("Quechua"), "Runa Simi, Kichwa", "UTF-8", ()),
	"rm": ("Romansh", _("Romansh"), "Rumantsch Grischun", "UTF-8", ()),
	"rn": ("Rundi", _("Rundi"), "Ikirundi", "UTF-8", ()),
	"ro": ("Romanian", _("Romanian"), "Română", "ISO-8859-15", ("RO",)),
	"ru": ("Russian", _("Russian"), "Русский", "ISO-8859-15", ("RU", "UA")),
	"rw": ("Kinyarwanda", _("Kinyarwanda"), "Ikinyarwanda", "UTF-8", ("RW",)),
	"sa": ("Sanskrit", _("Sanskrit"), "संस्कृतम्", "UTF-8", ("IN",)),
	"sb": ("Sorbian", _("Sorbian"), "Sorbian", "UTF-8", ()),  # Not in Wikipedia.
	"sc": ("Sardinian", _("Sardinian"), "Sardu", "UTF-8", ("IT",)),
	"sd": ("Sindhi", _("Sindhi"), "सिन्धी, سنڌي، سندھی", "UTF-8", ("IN",)),
	"se": ("Northern Sami", _("Northern Sami"), "Davvisámegiella", "UTF-8", ("NO",)),
	"sg": ("Sango", _("Sango"), "Yângâ tî sängö", "UTF-8", ()),
	"si": ("Sinhala / Sinhalese", _("Sinhala / Sinhalese"), "සිංහල", "UTF-8", ("LK",)),
	"sk": ("Slovak", _("Slovak"), "Slovenčina / Slovenský Jazyk", "ISO-8859-15", ("SK",)),
	"sl": ("Slovenian", _("Slovenian"), "Slovenski Jezik / Slovenščina", "ISO-8859-15", ("SI",)),
	"sm": ("Samoan", _("Samoan"), "Gagana Fa'a Samoa", "UTF-8", ("WS",)),
	"sn": ("Shona", _("Shona"), "chiShona", "UTF-8", ()),
	"so": ("Somali", _("Somali"), "Soomaaliga, af Soomaali", "UTF-8", ("DJ", "ET", "KE", "SO")),
	"sq": ("Albanian", _("Albanian"), "Shqip", "UTF-8", ("AL", "KV", "MK")),
	"sr": ("Serbian", _("Serbian"), "Српски Језик", "ISO-8859-15", ("RS", "ME")),
	"ss": ("Swati", _("Swati"), "SiSwati", "UTF-8", ("ZA",)),
	"st": ("Sotho, Southern", _("Sotho, Southern"), "Sesotho", "UTF-8", ("ZA",)),
	"su": ("Sundanese", _("Sundanese"), "Basa Sunda", "UTF-8", ("SD",)),
	"sv": ("Swedish", _("Swedish"), "Svenska", "ISO-8859-15", ("SE", "FI")),
	"sw": ("Swahili", _("Swahili"), "Kiswahili", "UTF-8", ("KE", "TZ")),
	"ta": ("Tamil", _("Tamil"), "தமிழ்", "UTF-8", ("IN", "LK")),
	"te": ("Telugu", _("Telugu"), "తెలుగు", "UTF-8", ("IN",)),
	"tg": ("Tajik", _("Tajik"), "тоҷикӣ, toçikī, تاجیکی", "UTF-8", ("TJ",)),
	"th": ("Thai", _("Thai"), "ไทย", "ISO-8859-15", ("TH",)),
	"ti": ("Tigrinya", _("Tigrinya"), "ትግርኛ", "UTF-8", ("ER", "ET")),
	"tk": ("Turkmen", _("Turkmen"), "Türkmen, Түркмен", "UTF-8", ("TM",)),
	"tl": ("Tagalog", _("Tagalog"), "Wikang Tagalog", "UTF-8", ("PH",)),
	"tn": ("Tswana", _("Tswana"), "Setswana", "UTF-8", ("ZA",)),
	"to": ("Tonga", _("Tonga"), "Faka Tonga", "UTF-8", ("TO",)),
	"tr": ("Turkish", _("Turkish"), "Türkçe", "ISO-8859-15", ("TR", "CY")),
	"ts": ("Tsonga", _("Tsonga"), "Xitsonga", "UTF-8", ("ZA",)),
	"tt": ("Tatar", _("Tatar"), "Татар теле, Tatar tele", "UTF-8", ("RU",)),
	"tw": ("Twi", _("Twi"), "Twi", "UTF-8", ()),
	"ty": ("Tahitian", _("Tahitian"), "Reo Tahiti", "UTF-8", ()),
	"ug": ("Uighur / Uyghur", _("Uighur / Uyghur"), "ئۇيغۇرچە‎ / Uyghurche", "UTF-8", ("CN",)),
	"uk": ("Ukrainian", _("Ukrainian"), "Українська", "ISO-8859-15", ("UA",)),
	"ur": ("Urdu", _("Urdu"), "اردو", "UTF-8", ("IN", "PK")),
	"uz": ("Uzbek", _("Uzbek"), "Oʻzbek, Ўзбек, أۇزبېك", "UTF-8", ("UZ",)),
	"ve": ("Venda", _("Venda"), "Tshivenḓa", "UTF-8", ("ZA",)),
	"vi": ("Vietnamese", _("Vietnamese"), "Tiếng Việt", "UTF-8", ("VN",)),
	"vo": ("Volapük", _("Volapük"), "Volapük", "UTF-8", ()),
	"wa": ("Walloon", _("Walloon"), "Walon", "UTF-8", ("BE",)),
	"wo": ("Wolof", _("Wolof"), "Wollof", "UTF-8", ("SN",)),
	"xh": ("Xhosa", _("Xhosa"), "isiXhosa", "UTF-8", ("ZA",)),
	"yi": ("Yiddish", _("Yiddish"), "ייִדיש", "UTF-8", ("US",)),
	"yo": ("Yoruba", _("Yoruba"), "Yorùbá", "UTF-8", ("NG",)),
	"za": ("Zhuang / Chuang", _("Zhuang / Chuang"), "Saɯ cueŋƅ / Saw cuengh", "UTF-8", ()),
	"zh": ("Chinese", _("Chinese"), "中文", "UTF-8", ("CN", "HK", "SG", "TW")),
	"zu": ("Zulu", _("Zulu"), "isiZulu", "UTF-8", ("ZA",))
}

COUNTRY_ALPHA3 = 0
COUNTRY_NUMERIC = 1
COUNTRY_NAME = 2
COUNTRY_TRANSLATED = 3
COUNTRY_NATIVE = 4
COUNTRY_MAX = 4

COUNTRY_DATA = {
	# https://www.iso.org/obp/ui/#search/code/
	# https://www.worldatlas.com/aatlas/ctycodes.htm
	"AD": ("AND", "020", "Andorra", _("Andorra"), "d'Andorra"),
	"AE": ("ARE", "784", "United Arab Emirates", _("United Arab Emirates"), "الإمارات العربية المتحدة‎ al-ʾImārāt al-ʿArabīyyah al-Muttaḥidah"),
	"AF": ("AFG", "004", "Afghanistan", _("Afghanistan"), "افغانستان"),
	"AG": ("ATG", "028", "Antigua and Barbuda", _("Antigua and Barbuda"), "Antigua and Barbuda"),
	"AI": ("AIA", "660", "Anguilla", _("Anguilla"), "Anguilla"),
	"AL": ("ALB", "008", "Albania", _("Albania"), "Shqipëri"),
	"AM": ("ARM", "051", "Armenia", _("Armenia"), "Հայաստան"),
	"AO": ("AGO", "024", "Angola", _("Angola"), "Angola"),
	"AQ": ("ATA", "010", "Antarctica", _("Antarctica"), "Antarctica"),
	"AR": ("ARG", "032", "Argentina", _("Argentina"), "Argentina"),
	"AS": ("ASM", "016", "American Samoa", _("American Samoa"), "Amerika Sāmoa"),
	"AT": ("AUT", "040", "Austria", _("Austria"), "Österreich"),
	"AU": ("AUS", "036", "Australia", _("Australia"), "Australia"),
	"AW": ("ABW", "533", "Aruba", _("Aruba"), "Aruba"),
	"AX": ("ALA", "248", "Aland Islands", _("Aland Islands"), "Åland Islands"),
	"AZ": ("AZE", "031", "Azerbaijan", _("Azerbaijan"), "Azərbaycan"),
	"BA": ("BIH", "070", "Bosnia and Herzegovina", _("Bosnia and Herzegovina"), "Bosna i Hercegovina"),
	"BB": ("BRB", "052", "Barbados", _("Barbados"), "Barbados"),
	"BD": ("BGD", "050", "Bangladesh", _("Bangladesh"), "বাংলাদেশ"),
	"BE": ("BEL", "056", "Belgium", _("Belgium"), "België"),
	"BF": ("BFA", "854", "Burkina Faso", _("Burkina Faso"), "Buʁkina Faso"),
	"BG": ("BGR", "100", "Bulgaria", _("Bulgaria"), "България"),
	"BH": ("BHR", "048", "Bahrain", _("Bahrain"), "البحرين‎"),
	"BI": ("BDI", "108", "Burundi", _("Burundi"), "y'Uburundi"),
	"BJ": ("BEN", "204", "Benin", _("Benin"), "Bénin"),
	"BL": ("BLM", "652", "Saint Barthelemy", _("Saint Barthelemy"), "Saint-Barthélemy"),
	"BM": ("BMU", "060", "Bermuda", _("Bermuda"), "Bermuda"),
	"BN": ("BRN", "096", "Brunei Darussalam", _("Brunei Darussalam"), "Negara Brunei Darussalam"),
	"BO": ("BOL", "068", "Bolivia", _("Bolivia"), "Mborivia"),
	"BQ": ("BES", "535", "Bonaire", _("Bonaire"), "Bonaire"),
	"BR": ("BRA", "076", "Brazil", _("Brazil"), "Brasil"),
	"BS": ("BHS", "044", "Bahamas", _("Bahamas"), "Bahamas"),
	"BT": ("BTN", "064", "Bhutan", _("Bhutan"), "འབྲུག་རྒྱལ་ཁབ་"),
	"BV": ("BVT", "074", "Bouvet Island", _("Bouvet Island"), "Bouvetøya"),
	"BW": ("BWA", "072", "Botswana", _("Botswana"), "Botswana"),
	"BY": ("BLR", "112", "Belarus", _("Belarus"), "Беларусь"),
	"BZ": ("BLZ", "084", "Belize", _("Belize"), "Belize"),
	"CA": ("CAN", "124", "Canada", _("Canada"), "Canada"),
	"CC": ("CCK", "166", "Cocos (Keeling) Islands", _("Cocos (Keeling) Islands"), "Cocos (Keeling) Islands"),
	"CD": ("COD", "180", "Congo, Democratic Republic of the", _("Democratic Republic of the Congo"), "République démocratique du Congo"),
	"CF": ("CAF", "140", "Central African Republic", _("Central African Republic"), "Ködörösêse tî Bêafrîka"),
	"CG": ("COG", "178", "Congo", _("Congo"), "Congo"),
	"CH": ("CHE", "756", "Switzerland", _("Switzerland"), "Suisse"),
	"CI": ("CIV", "384", "Cote d'Ivoire / Ivory Coast", _("Cote d'Ivoire / Ivory Coast"), "Côte d'Ivoire"),
	"CK": ("COK", "184", "Cook Islands", _("Cook Islands"), "Kūki 'Āirani"),
	"CL": ("CHL", "152", "Chile", _("Chile"), "Chile"),
	"CM": ("CMR", "120", "Cameroon", _("Cameroon"), "Cameroun"),
	"CN": ("CHN", "156", "China", _("China"), "中国"),
	"CO": ("COL", "170", "Colombia", _("Colombia"), "Colombia"),
	"CR": ("CRI", "188", "Costa Rica", _("Costa Rica"), "Costa Rica"),
	"CU": ("CUB", "192", "Cuba", _("Cuba"), "Cuba"),
	"CV": ("CPV", "132", "Cape Verde", _("Cape Verde"), "Cabo Verde"),
	"CW": ("CUW", "531", "Curacao", _("Curacao"), "Kòrsou"),
	"CX": ("CXR", "162", "Christmas Island", _("Christmas Island"), "聖誕島 / Wilayah Pulau Krismas"),
	"CY": ("CYP", "196", "Cyprus", _("Cyprus"), "Κύπρος"),
	"CZ": ("CZE", "203", "Czech Republic", _("Czech Republic"), "Česká Republika"),
	"DE": ("DEU", "276", "Germany", _("Germany"), "Deutschland"),
	"DJ": ("DJI", "262", "Djibouti", _("Djibouti"), "جيبوتي‎"),
	"DK": ("DNK", "208", "Denmark", _("Denmark"), "Danmark"),
	"DM": ("DMA", "212", "Dominica", _("Dominica"), "Dominique"),
	"DO": ("DOM", "214", "Dominican Republic", _("Dominican Republic"), "República Dominicana"),
	"DZ": ("DZA", "012", "Algeria", _("Algeria"), "الجزائر‎"),
	"EC": ("ECU", "218", "Ecuador", _("Ecuador"), "Ikwayur"),
	"EE": ("EST", "233", "Estonia", _("Estonia"), "Eesti"),
	"EG": ("EGY", "818", "Egypt", _("Egypt"), "ِصر‎"),
	"EH": ("ESH", "732", "Western Sahara", _("Western Sahara"), "الصحراء الغربية"),
	"ER": ("ERI", "232", "Eritrea", _("Eritrea"), "ኤርትራ"),
	"ES": ("ESP", "724", "Spain", _("Spain"), "España"),
	"ET": ("ETH", "231", "Ethiopia", _("Ethiopia"), "ኢትዮጵያ"),
	"FI": ("FIN", "246", "Finland", _("Finland"), "Suomi"),
	"FJ": ("FJI", "242", "Fiji", _("Fiji"), "Viti"),
	"FK": ("FLK", "238", "Falkland Islands (Malvinas)", _("Falkland Islands (Malvinas)"), "Islas Malvinas"),
	"FM": ("FSM", "583", "Micronesia, Federated States of", _("Micronesia, Federated States of"), "Micronesia, Federated States of"),
	"FO": ("FRO", "234", "Faroe Islands", _("Faroe Islands"), "Føroyar"),
	"FR": ("FRA", "250", "France", _("France"), "Française"),
	"GA": ("GAB", "266", "Gabon", _("Gabon"), "Gabonaise"),
	"GB": ("GBR", "826", "United Kingdom", _("United Kingdom"), "United Kingdom"),
	"GD": ("GRD", "308", "Grenada", _("Grenada"), "Grenada"),
	"GE": ("GEO", "268", "Georgia", _("Georgia"), "საქართველო"),
	"GF": ("GUF", "254", "French Guiana", _("French Guiana"), "Guyane"),
	"GG": ("GGY", "831", "Guernsey", _("Guernsey"), "Guernési"),
	"GH": ("GHA", "288", "Ghana", _("Ghana"), "Ghana"),
	"GI": ("GIB", "292", "Gibraltar", _("Gibraltar"), "جبل طارق"),
	"GL": ("GRL", "304", "Greenland", _("Greenland"), "Grønland"),
	"GM": ("GMB", "270", "Gambia", _("Gambia"), "Gambia"),
	"GN": ("GIN", "324", "Guinea", _("Guinea"), "Guinée"),
	"GP": ("GLP", "312", "Guadeloupe", _("Guadeloupe"), "Gwadloup"),
	"GQ": ("GNQ", "226", "Equatorial Guinea", _("Equatorial Guinea"), "Guinea Ecuatorial"),
	"GR": ("GRC", "300", "Greece", _("Greece"), "Ελληνική Δημοκρατία"),
	"GS": ("SGS", "239", "South Georgia and the South Sandwich Islands", _("South Georgia and the South Sandwich Islands"), "South Georgia and the South Sandwich Islands"),
	"GT": ("GTM", "320", "Guatemala", _("Guatemala"), "Guatemala"),
	"GU": ("GUM", "316", "Guam", _("Guam"), "Guåhån"),
	"GW": ("GNB", "624", "Guinea-Bissau", _("Guinea-Bissau"), "Guiné-Bissau"),
	"GY": ("GUY", "328", "Guyana", _("Guyana"), "Guyana"),
	"HK": ("HKG", "344", "Hong Kong", _("Hong Kong"), "香港"),
	"HM": ("HMD", "334", "Heard Island and McDonald Islands", _("Heard Island and McDonald Islands"), "Heard Island and McDonald Islands"),
	"HN": ("HND", "340", "Honduras", _("Honduras"), "Honduras"),
	"HR": ("HRV", "191", "Croatia", _("Croatia"), "Hrvatska"),
	"HT": ("hti", "332", "Haiti", _("Haiti"), "Haïti"),
	"HU": ("HUN", "348", "Hungary", _("Hungary"), "Magyarország"),
	"ID": ("IDN", "360", "Indonesia", _("Indonesia"), "Indonesia"),
	"IE": ("IRL", "372", "Ireland", _("Ireland"), "Éire"),
	"IL": ("ISR", "376", "Israel", _("Israel"), "ישראל"),
	"IM": ("IMN", "833", "Isle of Man", _("Isle of Man"), "Mannin"),
	"IN": ("IND", "356", "India", _("India"), "Bhārat"),
	"IO": ("IOT", "086", "British Indian Ocean Territory", _("British Indian Ocean Territory"), "British Indian Ocean Territory"),
	"IQ": ("IRQ", "368", "Iraq", _("Iraq"), "ٱلْعِرَاق‎"),
	"IR": ("IRN", "364", "Iran, Islamic Republic of", _("Iran, Islamic Republic of"), "جمهوری اسلامی ایران"),
	"IS": ("ISL", "352", "Iceland", _("Iceland"), "Ísland"),
	"IT": ("ITA", "380", "Italy", _("Italy"), "Italia"),
	"JE": ("JEY", "832", "Jersey", _("Jersey"), "Jèrri"),
	"JM": ("JAM", "388", "Jamaica", _("Jamaica"), "Jumieka"),
	"JO": ("JOR", "400", "Jordan", _("Jordan"), "الْأُرْدُنّ‎"),
	"JP": ("JPN", "392", "Japan", _("Japan"), "日本"),
	"KE": ("KEN", "404", "Kenya", _("Kenya"), "Kenya"),
	"KG": ("KGZ", "417", "Kyrgyzstan", _("Kyrgyzstan"), "Kırğızstan"),
	"KH": ("KHM", "116", "Cambodia", _("Cambodia"), "កម្ពុជា"),
	"KI": ("KIR", "296", "Kiribati", _("Kiribati"), "Kiribati"),
	"KM": ("COM", "174", "Comoros", _("Comoros"), "جزر القمر‎"),
	"KN": ("KNA", "659", "Saint Kitts and Nevis", _("Saint Kitts and Nevis"), "Saint Kitts and Nevis"),
	"KP": ("PRK", "408", "Korea, Democratic People's Republic of", _("Korea, Democratic People's Republic of"), "조선"),
	"KR": ("KOR", "410", "Korea, Republic of", _("Korea, Republic of"), "한국"),
	"KW": ("KWT", "414", "Kuwait", _("Kuwait"), "الكويت‎"),
	"KY": ("CYM", "136", "Cayman Islands", _("Cayman Islands"), "Cayman Islands"),
	"KZ": ("KAZ", "398", "Kazakhstan", _("Kazakhstan"), "Қазақстан"),
	"LA": ("LAO", "418", "Lao People's Democratic Republic", _("Lao People's Democratic Republic"), "ລາວ"),
	"LB": ("LBM", "422", "Lebanon", _("Lebanon"), "لبنان‎"),
	"LC": ("LCA", "662", "Saint Lucia", _("Saint Lucia"), "Sainte-Lucie"),
	"LI": ("LIE", "438", "Liechtenstein", _("Liechtenstein"), "Liechtenstein"),
	"LK": ("LKA", "144", "Sri Lanka", _("Sri Lanka"), "ශ්‍රී ලංකා Śrī Laṃkā"),
	"LR": ("LBR", "430", "Liberia", _("Liberia"), "Liberia"),
	"LS": ("LSO", "426", "Lesotho", _("Lesotho"), "Lesotho"),
	"LT": ("LTU", "440", "Lithuania", _("Lithuania"), "Lietuva"),
	"LU": ("LUX", "442", "Luxembourg", _("Luxembourg"), "Lëtzebuerg"),
	"LV": ("LVA", "428", "Latvia", _("Latvia"), "Latvija"),
	"LY": ("LBY", "434", "Libya", _("Libya"), "ليبيا‎"),
	"MA": ("MAR", "504", "Morocco", _("Morocco"), "المغرب‎"),
	"MC": ("MCO", "492", "Monaco", _("Monaco"), "Monaco"),
	"MD": ("MDA", "498", "Moldova, Republic of", _("Moldova, Republic of"), "Republica Moldova"),
	"ME": ("MNE", "499", "Montenegro", _("Montenegro"), "Црна Гора"),
	"MF": ("MAF", "663", "Saint Martin (French part)", _("Saint Martin (French part)"), "Saint-Martin"),
	"MG": ("MDG", "450", "Madagascar", _("Madagascar"), "Madagasikara"),
	"MH": ("MHL", "584", "Marshall Islands", _("Marshall Islands"), "Aolepān Aorōkin M̧ajeļ"),
	"MK": ("MKD", "807", "North Macedonia, Republic of", _("North Macedonia, Republic of"), "Република Северна Македонија"),
	"ML": ("MLI", "466", "Mali", _("Mali"), "Mali"),
	"MM": ("MMR", "104", "Myanmar", _("Myanmar"), "မြန်မာ"),
	"MN": ("MNG", "496", "Mongolia", _("Mongolia"), "Монгол Улс"),
	"MO": ("MAC", "446", "Macao", _("Macao"), "澳門"),
	"MP": ("MNP", "580", "Northern Mariana Islands", _("Northern Mariana Islands"), "Northern Mariana Islands"),
	"MQ": ("MTQ", "474", "Martinique", _("Martinique"), "Matnik / Matinik"),
	"MR": ("MRT", "478", "Mauritania", _("Mauritania"), "موريتانيا‎"),
	"MS": ("MSR", "500", "Montserrat", _("Montserrat"), "Montserrat"),
	"MT": ("MLT", "470", "Malta", _("Malta"), "Malta"),
	"MU": ("MUS", "480", "Mauritius", _("Mauritius"), "Maurice"),
	"MV": ("MDV", "462", "Maldives", _("Maldives"), "ދިވެހިރާއްޖެ"),
	"MW": ("MWI", "454", "Malawi", _("Malawi"), "Malaŵi"),
	"MX": ("MEX", "484", "Mexico", _("Mexico"), "Mēxihco"),
	"MY": ("MYS", "458", "Malaysia", _("Malaysia"), "Məlejsiə"),
	"MZ": ("MOZ", "508", "Mozambique", _("Mozambique"), "Moçambique"),
	"NA": ("NAM", "516", "Namibia", _("Namibia"), "Namibia"),
	"NC": ("NCL", "540", "New Caledonia", _("New Caledonia"), "Nouvelle-Calédonie"),
	"NE": ("NER", "562", "Niger", _("Niger"), "Niger"),
	"NF": ("NFK", "574", "Norfolk Island", _("Norfolk Island"), "Norf'k Ailen"),
	"NG": ("NGA", "566", "Nigeria", _("Nigeria"), "Nijeriya"),
	"NI": ("NIC", "558", "Nicaragua", _("Nicaragua"), "Nicaragua"),
	"NL": ("NLD", "528", "Netherlands", _("Netherlands"), "Nederland"),
	"NO": ("NOR", "578", "Norway", _("Norway"), "Norge / Noreg"),
	"NP": ("NPL", "524", "Nepal", _("Nepal"), "नेपाल"),
	"NR": ("NRU", "520", "Nauru", _("Nauru"), "Naoero"),
	"NU": ("NIU", "570", "Niue", _("Niue"), "Niuē"),
	"NZ": ("NZL", "554", "New Zealand", _("New Zealand"), "New Zealand"),
	"OM": ("OMN", "512", "Oman", _("Oman"), "عمان‎"),
	"PA": ("PAN", "591", "Panama", _("Panama"), "Panamá"),
	"PE": ("PER", "604", "Peru", _("Peru"), "Perú"),
	"PF": ("PYF", "258", "French Polynesia", _("French Polynesia"), "Polynésie française"),
	"PG": ("PNG", "598", "Papua New Guinea", _("Papua New Guinea"), "Papua Niugini"),
	"PH": ("PHL", "608", "Philippines", _("Philippines"), "Pilipinas"),
	"PK": ("PAK", "586", "Pakistan", _("Pakistan"), "اِسلامی جمہوریہ پاكِستان"),
	"PL": ("POL", "616", "Poland", _("Poland"), "Polska"),
	"PM": ("SPM", "666", "Saint Pierre and Miquelon", _("Saint Pierre and Miquelon"), "Saint-Pierre-et-Miquelon"),
	"PN": ("PCN", "612", "Pitcairn", _("Pitcairn"), "Pitkern Ailen"),
	"PR": ("PRI", "630", "Puerto Rico", _("Puerto Rico"), "Puerto Rico"),
	"PS": ("PSE", "275", "Palestine, State of", _("Palestine, State of"), "فلسطين‎"),
	"PT": ("PRT", "620", "Portugal", _("Portugal"), "Portuguesa"),
	"PW": ("PLW", "585", "Palau", _("Palau"), "Belau"),
	"PY": ("PRY", "600", "Paraguay", _("Paraguay"), "Paraguái"),
	"QA": ("QAT", "634", "Qatar", _("Qatar"), "قطر‎"),
	"RE": ("REU", "638", "Réunion", _("Réunion"), "La Réunion"),
	"RO": ("ROU", "642", "Romania", _("Romania"), "România"),
	"RS": ("SRB", "688", "Serbia", _("Serbia"), "Србија"),
	"RU": ("RUS", "643", "Russian Federation", _("Russian Federation"), "Росси́йская Федера́ция"),
	"RW": ("RWA", "646", "Rwanda", _("Rwanda"), "Rwanda"),
	"SA": ("SAU", "682", "Saudi Arabia", _("Saudi Arabia"), "المملكة العربية السعودية"),
	"SB": ("SLB", "090", "Solomon Islands", _("Solomon Islands"), "Solomon Aelan"),
	"SC": ("SYC", "690", "Seychelles", _("Seychelles"), "Seychelles"),
	"SD": ("SDN", "729", "Sudan", _("Sudan"), "السودان‎ as-Sūdān"),
	"SE": ("SWE", "752", "Sweden", _("Sweden"), "Sverige"),
	"SG": ("SGP", "702", "Singapore", _("Singapore"), "Singapore"),
	"SH": ("SHN", "654", "Saint Helena, Ascension and Tristan da Cunha", _("Saint Helena, Ascension and Tristan da Cunha"), "Saint Helena, Ascension and Tristan da Cunha"),
	"SI": ("SVN", "705", "Slovenia", _("Slovenia"), "Slovenija"),
	"SJ": ("SJM", "744", "Svalbard and Jan Mayen", _("Svalbard and Jan Mayen"), "Svalbard og Jan Mayen"),
	"SK": ("SVK", "703", "Slovakia", _("Slovakia"), "Slovensko"),
	"SL": ("SLE", "694", "Sierra Leone", _("Sierra Leone"), "Sierra Leone"),
	"SM": ("SMR", "674", "San Marino", _("San Marino"), "San Marino"),
	"SN": ("SEN", "686", "Senegal", _("Senegal"), "Sénégal"),
	"SO": ("SOM", "706", "Somalia", _("Somalia"), "Soomaaliya"),
	"SR": ("SUR", "740", "Suriname", _("Suriname"), "Suriname"),
	"SS": ("SSD", "728", "South Sudan", _("South Sudan"), "South Sudan"),
	"ST": ("STP", "678", "Sao Tome and Principe", _("Sao Tome and Principe"), "São Tomé e Principe"),
	"SV": ("SLV", "222", "El Salvador", _("El Salvador"), "el salβaˈðoɾ"),
	"SX": ("SXM", "534", "Sint Maarten", _("Sint Maarten"), "Sint Maarten"),
	"SY": ("SYR", "760", "Syrian Arab Republic", _("Syrian Arab Republic"), "سوريا‎"),
	"SZ": ("SWZ", "748", "Swaziland / Eswatini", _("Swaziland / Eswatini"), "eSwatini"),
	"TC": ("TCA", "796", "Turks and Caicos Islands", _("Turks and Caicos Islands"), "Turks and Caicos Islands"),
	"TD": ("TCD", "148", "Chad", _("Chad"), "تشاد‎"),
	"TF": ("ATF", "260", "French Southern Territories", _("French Southern Territories"), "Terres australes et antarctiques françaises"),
	"TG": ("TGO", "768", "Togo", _("Togo"), "Togolaise"),
	"TH": ("THA", "764", "Thailand", _("Thailand"), "ราชอาณาจักรไทย"),
	"TJ": ("TJK", "762", "Tajikistan", _("Tajikistan"), "Тоҷикистон"),
	"TK": ("TKL", "772", "Tokelau", _("Tokelau"), "Tokelau"),
	"TL": ("TLS", "626", "Timor-Leste / East Timor", _("Timor-Leste / East Timor"), "Timór Lorosa'e"),
	"TM": ("TKM", "795", "Turkmenistan", _("Turkmenistan"), "Türkmenistan"),
	"TN": ("TUN", "788", "Tunisia", _("Tunisia"), "الجمهورية التونسية"),
	"TO": ("TON", "776", "Tonga", _("Tonga"), "Tonga"),
	"TR": ("TUR", "792", "Turkey", _("Turkey"), "Türkiye"),
	"TT": ("TTO", "780", "Trinidad and Tobago", _("Trinidad and Tobago"), "Trinidad and Tobago"),
	"TV": ("TUV", "798", "Tuvalu", _("Tuvalu"), "Tuvalu"),
	"TW": ("TWN", "158", "Taiwan", _("Taiwan"), "中華民國"),
	"TZ": ("TZA", "834", "Tanzania, United Republic of", _("Tanzania, United Republic of"), "جمهورية تنزانيا المتحدة‎"),
	"UA": ("UKR", "804", "Ukraine", _("Ukraine"), "Україна"),
	"UG": ("UGA", "800", "Uganda", _("Uganda"), "Jamhuri ya Uganda"),
	"UM": ("UMI", "581", "United States Minor Outlying Islands", _("United States Minor Outlying Islands"), "United States Minor Outlying Islands"),
	"US": ("USA", "840", "United States of America", _("United States of America"), "United States of America"),
	"UY": ("URY", "858", "Uruguay", _("Uruguay"), "Uruguay"),
	"UZ": ("UZB", "860", "Uzbekistan", _("Uzbekistan"), "Oʻzbekiston"),
	"VA": ("VAT", "336", "Holy See (Vatican City State)", _("Holy See (Vatican City State)"), "Santa Sede (Stato della Città del Vaticano)"),
	"VC": ("VCT", "670", "Saint Vincent and the Grenadines", _("Saint Vincent and the Grenadines"), "Saint Vincent and the Grenadines"),
	"VE": ("VEN", "862", "Venezuela, Bolivarian Republic of", _("Venezuela, Bolivarian Republic of"), "República Bolivariana de Venezuela"),
	"VG": ("VGB", "092", "Virgin Islands (British)", _("Virgin Islands (British)"), "Virgin Islands (British)"),
	"VI": ("VIR", "850", "Virgin Islands (US)", _("Virgin Islands (US)"), "Virgin Islands (US)"),
	"VN": ("VNM", "704", "Viet Nam", _("Viet Nam"), "Việt Nam"),
	"VU": ("VUT", "548", "Vanuatu", _("Vanuatu"), "Vanuatu"),
	"WF": ("WLF", "876", "Wallis and Futuna", _("Wallis and Futuna"), "Wallis-et-Futuna"),
	"WS": ("WSM", "882", "Samoa", _("Samoa"), "Sāmoa"),
	"YE": ("YEM", "887", "Yemen", _("Yemen"), "ٱلْيَمَن‎"),
	"YT": ("MYT", "175", "Mayotte", _("Mayotte"), "Mayotte"),
	"ZA": ("ZAF", "710", "South Africa", _("South Africa"), "South Africa"),
	"ZM": ("ZMB", "894", "Zambia", _("Zambia"), "Zambia"),
	"ZW": ("ZWE", "716", "Zimbabwe", _("Zimbabwe"), "Zimbabwe")
}

CAT_ENVIRONMENT = 0
CAT_PYTHON = 1

CATEGORIES = [
	("LC_ALL", None),
	("LC_ADDRESS", None),
	("LC_COLLATE", None),
	("LC_CTYPE", None),
	("LC_DATE", None),
	("LC_IDENTIFICATION", None),
	("LC_MEASUREMENT", None),
	("LC_MESSAGES", LC_MESSAGES),
	("LC_MONETARY", LC_MONETARY),
	("LC_NAME", None),
	("LC_NUMERIC", LC_NUMERIC),
	("LC_PAPER", None),
	("LC_TELEPHONE", None),
	("LC_TIME", LC_TIME)
]


class International:
	def __init__(self):
		self.availablePackages = []
		self.installedPackages = []
		self.packageDirectories = []
		self.localeList = ["en_US"]
		self.languageList = ["en"]
		self.activeLocale = "en_US"
		self.catalog = None
		self.callbacks = []
		# environ["LANG"] = "en_US.UTF-8"  # Force the environment to US English so all shell command run from Enigma2 can be parsed in English (as coded).
		# environ["LANGUAGE"] = "en_US.UTF-8"
		self.buildISO3166()  # This should not be required when all Enigma2 code comes here for country and language data.
		self.initInternational()

	def buildISO3166(self):  # This code builds the CountryCodes.py ISO3166 country list.
		data = []
		for country in COUNTRY_DATA.keys():
			data.append((
				COUNTRY_DATA[country][COUNTRY_TRANSLATED],
				country,  # This is the ISO3166 ALPHA2 Code.
				COUNTRY_DATA[country][COUNTRY_ALPHA3],
				COUNTRY_DATA[country][COUNTRY_NUMERIC],
				COUNTRY_DATA[country][COUNTRY_NAME]
			))
		data.sort(key=lambda x: x[4])
		setISO3166(data)

	def initInternational(self):
		self.availablePackages = self.getAvailablePackages()
		self.installedPackages = self.getInstalledPackages()
		self.packageDirectories = self.getPackageDirectories()
		if len(self.packageDirectories) != len(self.installedPackages):
			print("[International] Warning: Count of installed language packages and language directory entries do not match!")
		for package in self.installedPackages:
			locales = self.packageToLocales(package)
			packageLocales = []
			for locale in locales:
				if locale not in packageLocales:
					packageLocales.append(locale)
				if locale not in self.localeList:
					self.localeList.append(locale)
			language = self.splitPackage(package)[0]
			if language not in self.languageList:
				self.languageList.append(language)
			count = len(packageLocales)
			print("[International] Package '%s' supports %d locale%s '%s'." % (package, count, "" if count == 1 else "s", "', '".join(packageLocales)))
		self.localeList.sort()
		self.languageList.sort()

	def activateLanguage(self, language, runCallbacks=True):
		locale = "%s_%s" % (language, LANGUAGE_DATA[language][LANG_COUNTRYCODES][0]) if language in LANGUAGE_DATA else "en_US"
		print("[International] Language '%s' is being activated as locale '%s'." % (language, locale))
		return self.activateLocale(locale, runCallbacks=runCallbacks)

	def activateLocale(self, locale, runCallbacks=True):
		if locale not in self.localeList:
			print("[International] Selected locale '%s' is not installed or does not exist!" % locale)
		elif locale == self.activeLocale:
			print("[International] Language '%s', locale '%s' is already active." % (self.getLanguage(locale), locale))
		else:
			print("[International] Activating language '%s', locale '%s'." % (self.getLanguage(locale), locale))
			global languagePath
			try:
				self.catalog = translation("enigma2", languagePath, languages=[locale], fallback=True)
			except UnicodeDecodeError:
				print("[International] Error: The language translation data in '%s' for '%s' ('%s') has failed to initialise!" % (languagePath, self.getLanguage(locale), locale))
				self.catalog = translation("enigma2", "/", fallback=True)
			self.catalog.install(names=("ngettext", "pgettext"))

			# These should always be C.UTF-8 (or POSIX if C.UTF-8 is unavaible) or program code might behave
			# differently depending on language setting
			try:
				setlocale(LC_CTYPE, ('C', 'UTF-8'))
			except:
				pass
			try:
				setlocale(LC_COLLATE, ('C', 'UTF-8'))
			except:
				try:
					setlocale(LC_COLLATE, ('POSIX', ''))
				except:
					pass

			for category in CATEGORIES:
				environ[category[CAT_ENVIRONMENT]] = "%s.UTF-8" % locale
				localeError = None
				if category[CAT_PYTHON] is not None:
					try:  # Try and set the Python locale to the current locale.
						setlocale(category[CAT_PYTHON], locale=(locale, "UTF-8"))
					except LocaleError as err:
						try:  # If unavailable, try for the Python locale to the language base locale.
							locales = self.packageToLocales(self.getLanguage(locale))
							setlocale(category[CAT_PYTHON], locale=(locales[0], "UTF-8"))
							replacement = locales[0]
						except LocaleError as err:  # If unavailable fall back to the US English locale.
							setlocale(category[CAT_PYTHON], locale=("en_US", "UTF-8"))
							replacement = "en_US"
						if localeError is None:
							localeError = replacement
							print("[International] Warning: Locale '%s' is not available in Python %s, using locale '%s' instead." % (locale, category[CAT_ENVIRONMENT], replacement))
			environ["LC_TIME"] = "%s.UTF-8" % locale  # Python 2.7 sometimes reverts the LC_TIME environment value, so make sure it has the correct value!
			environ["LANG"] = "%s.UTF-8" % locale
			environ["LANGUAGE"] = "%s.UTF-8" % locale
			environ["GST_SUBTITLE_ENCODING"] = self.getGStreamerSubtitleEncoding()
			self.activeLocale = locale
		if runCallbacks:
			for method in self.callbacks:
				method()

	def addCallback(self, callback):
		if callable(callback):
			self.callbacks.append(callback)
		else:
			print("[International] Error: The callback '%s' is invalid!" % callback)

	def getActiveCatalog(self):
		return self.catalog

	def getAvailablePackages(self):
		command = (PACKAGER, "find", PACKAGE_TEMPLATE % "*")
		availablePackages = []
		try:
			# print("[International] Processing command '%s' with arguments '%s'." % (command[0], "', '".join(command[1:])))
			process = Popen(command, stdout=PIPE, stderr=PIPE, universal_newlines=True)
			packageText, errorText = process.communicate()
			if errorText:
				print("[International] getLanguagePackages Error: %s" % errorText)
			else:
				for language in packageText.split("\n"):
					if language and "meta" not in language:
						lang = language[15:].split(" ")[0]
						if lang not in availablePackages:
							availablePackages.append(lang)
				availablePackages = sorted(availablePackages)
		except (IOError, OSError) as err:
			print("[International] getLanguagePackages Error %d: %s ('%s')" % (err.errno, err.strerror, command[0]))
			availablePackages = []
		print("[International] There are %d available language packages in the repository '%s'." % (len(availablePackages), "', '".join(availablePackages)))
		return availablePackages

	def getInstalledPackages(self):
		command = (PACKAGER, "status", PACKAGE_TEMPLATE % "*")
		installedPackages = []
		try:
			# print("[International] Processing command '%s' with arguments '%s'." % (command[0], "', '".join(command[1:])))
			process = Popen(command, stdout=PIPE, stderr=PIPE, universal_newlines=True)
			packageText, errorText = process.communicate()
			if errorText:
				print("[International] getInstalledPackages Error: %s" % errorText)
			else:
				for package in packageText.split("\n\n"):
					if package.startswith("Package: %s" % (PACKAGE_TEMPLATE % "")) and "meta" not in package:
						list = []
						for data in package.split("\n"):
							if data.startswith("Package: "):
								installedPackages.append(data[24:])
								break
				installedPackages = sorted(installedPackages)
		except (IOError, OSError) as err:
			print("[International] getInstalledPackages Error %d: %s ('%s')" % (err.errno, err.strerror, command[0]))
		print("[International] There are %d installed language packages '%s'." % (len(installedPackages), "', '".join(installedPackages)))
		return installedPackages

	def getPackageDirectories(self):  # Adapt language directory entries to match the package format.
		global languagePath
		packageDirectories = sorted(listdir(languagePath)) if isdir(languagePath) else []
		print("[International] There are %d installed language directories '%s'." % (len(packageDirectories), "', '".join(packageDirectories)))
		return packageDirectories

	def packageToLocales(self, package):
		locale = package.replace("-", "_")
		data = self.splitLocale(locale)
		locales = []
		if data[1]:
			locales.append("%s_%s" % (data[0], data[1].upper()))
		else:
			for country in LANGUAGE_DATA.get(data[0], tuple([None] * LANG_MAX))[LANG_COUNTRYCODES]:
				locales.append("%s_%s" % (data[0], country))
		return locales

	def splitPackage(self, package):
		data = package.split("-")
		if len(data) < 2:
			data.append(None)
		else:
			data[1] = data[1].upper()
		return data

	def getLocale(self):
		return "en_US" if self.activeLocale is None else self.activeLocale

	def splitLocale(self, locale):
		data = locale.split("_")
		if len(data) < 2:
			data.append(None)
		return data

	def getCountry(self, item=None):
		if item is None:
			item = self.getLocale()
		return self.splitLocale(item)[1] if len(item) > 3 else item  # and item in COUNTRY_DATA or None

	def getCountryAlpha3(self, item=None):
		return COUNTRY_DATA.get(self.getCountry(item), tuple([None] * COUNTRY_MAX))[COUNTRY_ALPHA3]

	def getCountryNumeric(self, item=None):
		return COUNTRY_DATA.get(self.getCountry(item), tuple([None] * COUNTRY_MAX))[COUNTRY_NUMERIC]

	def getCountryName(self, item=None):
		return COUNTRY_DATA.get(self.getCountry(item), tuple([None] * COUNTRY_MAX))[COUNTRY_NAME]

	def getCountryTranslated(self, item=None):
		return COUNTRY_DATA.get(self.getCountry(item), tuple([None] * COUNTRY_MAX))[COUNTRY_TRANSLATED]

	def getCountryNative(self, item=None):
		return COUNTRY_DATA.get(self.getCountry(item), tuple([None] * COUNTRY_MAX))[COUNTRY_NATIVE]

	def getLanguage(self, item=None):
		if item is None:
			item = self.getLocale()
		return self.splitLocale(item)[0] if len(item) > 3 else item  # and item in LANGUAGE_DATA or None

	def getLanguageName(self, item=None):
		return LANGUAGE_DATA.get(self.getLanguage(item), tuple([None] * LANG_MAX))[LANG_NAME]

	def getLanguageNative(self, item=None):
		return LANGUAGE_DATA.get(self.getLanguage(item), tuple([None] * LANG_MAX))[LANG_NATIVE]

	def getLanguageEncoding(self, item=None):
		return LANGUAGE_DATA.get(self.getLanguage(item), tuple([None] * LANG_MAX))[LANG_ENCODING]

	def getLanguageCountryCode(self, item=None):
		countries = LANGUAGE_DATA.get(self.getLanguage(item), tuple([None] * LANG_MAX))[LANG_COUNTRYCODES]
		return countries[0] if countries else None

	def getLocaleList(self):
		return self.localeList

	def getLanguageList(self):
		return self.languageList

	def getPackage(self, locale=None):
		if locale is None:
			locale = self.getLocale()
		language = self.getLanguage(locale)
		pack = locale.replace("_", "-").lower()
		if pack in self.availablePackages:
			package = pack
		elif language in self.availablePackages:
			package = language
		else:
			package = None
		return package

	def getGStreamerSubtitleEncoding(self, item=None):
		language = self.getLanguage(item)
		return LANGUAGE_DATA[language][LANG_ENCODING] if language in LANGUAGE_DATA else "ISO-8859-15"

	def deleteLanguagePackages(self, packageList):
		return self.runPackageManager(cmdList=[PACKAGER, "remove", "--autoremove", "--force-depends"], packageList=packageList, action=_("deleted"))

	def installLanguagePackages(self, packageList):
		return self.runPackageManager(cmdList=[PACKAGER, "install", "--volatile-cache"], packageList=packageList, action=_("installed"))

	def runPackageManager(self, cmdList=None, packageList=None, action=""):
		status = ""
		if cmdList is not None and packageList is not None:
			cmdList = tuple(cmdList + [PACKAGE_TEMPLATE % x for x in packageList])
			print("[International] Running package manager command line '%s'." % " ".join(cmdList))
			try:
				process = Popen(cmdList, stdout=PIPE, stderr=PIPE, universal_newlines=True)
				packageText, errorText = process.communicate()
				if process.returncode:
					print("[International] Warning: Package manager exit status is %d!" % process.returncode)
				locales = 0
				languages = 0
				for package in packageList:
					if len(package) > 3:
						locales += 1
					if len(package) < 4:
						languages += 1
				msg = []
				if locales:
					msg.append(ngettext(_("Locale"), _("Locales"), locales))
				if languages:
					msg.append(ngettext(_("Language"), _("Languages"), languages))
				msg = "/".join(msg)
				languages = [self.splitPackage(x)[0] for x in packageList]
				languages = ["%s (%s)" % (LANGUAGE_DATA[x][LANG_NAME], LANGUAGE_DATA[x][LANG_NATIVE]) for x in languages]
				if errorText:
					print("[International] Warning: Package manager error:\n%s" % errorText)
					status = _("Error: %s %s not %s!  Please try again later.") % (msg, ", ".join(languages), action)
				else:
					status = "%s %s %s." % (msg, ", ".join(languages), action)
			except (IOError, OSError) as err:
				print("[International] Error %d: %s for command '%s'!" % (err.errno, err.strerror, " ".join(cmdList)))
				status = _("Error: Unable to process the command!  Please try again later.")
			self.initInternational()
		return status

	def removeLangs(self, currentLang='', excludeLangs=[]):
		delLangs = []
		print("[International] Delete all language packages except current:'%s' and excludes:'%s'" % (currentLang , ''.join(excludeLangs)))
		installedlanguages = listdir(languagePath)
		for l in installedlanguages:
			if l != currentLang and l not in excludeLangs:
				if len(l) > 2:
					l = l.lower()
					l = l.replace('_', '-')
					delLangs.append(l)
				else:
					if l != currentLang[:2]:
						delLangs.append(l)
		if delLangs:
			return international.deleteLanguagePackages(delLangs)

international = International()
