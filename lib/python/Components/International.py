# -*- coding: UTF-8 -*-

from gettext import bindtextdomain, install, textdomain, translation
from locale import Error as LocaleError, LC_ALL, LC_COLLATE, LC_CTYPE, LC_MESSAGES, LC_MONETARY, LC_NUMERIC, LC_TIME, setlocale
from os import environ, listdir
from os.path import isdir

from Tools.Directories import SCOPE_CONFIG, SCOPE_LANGUAGE, fileReadLines, resolveFilename

# In this code the following meanings are used:
# 	Language: An official language as recognized by ISO, eg "en" for English.
# 	Country: An official country as recognized by ISO, eg "AU" for Australia.
# 	Locale: An official language as spoken in a country, eg "en_AU" for English (Australian).

MODULE_NAME = __name__.split(".")[-1]

languagePath = resolveFilename(SCOPE_LANGUAGE)
try:
	install("enigma2", languagePath, names=("ngettext", "pgettext"))
except UnicodeDecodeError:
	print(f"[International] Error: The language translation data in '{languagePath}' has failed to initialize!  Translations are not possible.")
	install("enigma2", "/", names=("ngettext", "pgettext"))
bindtextdomain("enigma2", languagePath)
textdomain("enigma2")


class International:
	# This is the list of all locales built for OpenATV. If any locales are added or removed then this list should be updated!
	# The list of available locales rarely changes so this has been done to optimize the speed of starting Enigma2.
	DEFINED_LOCALES = ["ar", "bg", "ca", "cs", "da", "de", "el", "en", "en-au", "en-gb", "es", "et", "fa", "fi", "fr", "fy", "he", "hr", "hu", "id", "is", "it", "ku", "lt", "lv", "nb", "nl", "nn", "pl", "pt", "pt-br", "ro", "ru", "sk", "sl", "sq", "sr", "sv", "ta", "th", "tr", "uk", "vi", "zh-cn", "zh-hk"]
	LOCALE_TEMPLATE = "enigma2-locale-%s"
	PERMANENT_LOCALES = ["de_DE", "en_US", "fr_FR"]

	LANG_NAME = 0
	LANG_TRANSLATED = 1
	LANG_NATIVE = 2
	LANG_ENCODING = 3
	LANG_KEYBOARD = 4
	LANG_COUNTRYCODES = 5
	LANG_MAX = 5

	LANGUAGE_DATA = {
		# DEVELOPER NOTE:
		#
		# Should this language table include the ISO three letter code for use in the subtitle code?
		# Perhaps also have a flag to indicate that the language should be listed in the subtitle list?
		#
		# Fields: English Name, Translated Name, Localized Name, Encoding
		# 	Character Set, Keyboard, (Tuple of ISO-3166 Alpha2 Country Codes).
		#		NOTE: The first item of the tuple should be the
		# 		default or commonly known country for the language.
		# To make managing this list easier please keep languages in ISO
		# 639-2 Code order.  Language codes should be in lower case and
		# country codes should be in upper case.  Be careful not to
		# confuse / mix the language and country!
		# An Encoding Character Set of "" means UTF-8 and has been done to save
		# memory space. A Keyboard of "" means "qwerty" and has been done to save
		# memory space.
		#
		# The Character Set entry is only used to set a shell variable used
		# by Gstreamer.
		#
		# As noted above, if a language is used in more than one country then
		# the default locale country should be listed first.
		#
		# https://www.loc.gov/standards/iso639-2/php/code_list.php
		# https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes
		# https://lh.2xlibre.net/locales/
		"aa": ("Afar", _("Afar"), "Afaraf", "", "", ("DJ", "ER", "ET")),
		"ab": ("Abkhazian", _("Abkhazian"), "Аҧсуа Бызшәа / Аҧсшәа", "", "", ()),
		"ae": ("Avestan", _("Avestan"), "Avesta", "", "", ()),
		"af": ("Afrikaans", _("Afrikaans"), "Afrikaans", "", "", ("ZA",)),
		"ak": ("Akan", _("Akan"), "Akan", "", "", ("GH",)),
		"am": ("Amharic", _("Amharic"), "አማርኛ", "", "", ("ET",)),
		"an": ("Aragonese", _("Aragonese"), "Aragonés", "", "", ("ES",)),
		"ar": ("Arabic", _("Arabic"), "العربية", "ISO-8859-15", "", ("AE", "BH", "DZ", "EG", "IN", "IQ", "JO", "KW", "LB", "LY", "MA", "OM", "QA", "SA", "SD", "SS", "SY", "TN", "YE")),
		"as": ("Assamese", _("Assamese"), "অসমীয়া", "", "", ("IN",)),
		"av": ("Avaric", _("Avaric"), "Авар мацӀ / МагӀарул мацӀ", "", "", ()),
		"ay": ("Aymara", _("Aymara"), "Aymar Aru", "", "", ("PE",)),
		"az": ("Azerbaijani", _("Azerbaijani"), "Azərbaycan Dili", "", "", ("AZ", "IR")),
		"ba": ("Bashkir", _("Bashkir"), "башҡорт теле", "", "", ()),
		"be": ("Belarusian", _("Belarusian"), "беларуская мова", "", "", ("BY",)),
		"bg": ("Bulgarian", _("Bulgarian"), "български език", "ISO-8859-15", "", ("BG",)),
		"bh": ("Bihari languages", _("Bihari languages"), "भोजपुरी", "", "", ()),
		"bi": ("Bislama", _("Bislama"), "Bislama", "", "", ("TV", "VU")),
		"bm": ("Bambara", _("Bambara"), "Bamanankan", "", "", ("ML",)),
		"bn": ("Bengali", _("Bengali"), "বাংলা", "", "", ("BD", "IN")),
		"bo": ("Tibetan", _("Tibetan"), "བོད་ཡིག", "", "", ("CN", "IN")),
		"br": ("Breton", _("Breton"), "Brezhoneg", "", "", ("FR",)),
		"bs": ("Bosnian", _("Bosnian"), "Bosanski Jezik", "", "", ("BA",)),
		"ca": ("Catalan / Valencian", _("Catalan / Valencian"), "Català / Valencià", "ISO-8859-15", "", ("AD", "ES", "FR", "IT")),
		"ce": ("Chechen", _("Chechen"), "Нохчийн Мотт", "", "", ("RU",)),
		"ch": ("Chamorro", _("Chamorro"), "Chamoru", "", "", ()),
		"co": ("Corsican", _("Corsican"), "Corsu, Lingua Corsa", "", "", ()),
		"cr": ("Cree", _("Cree"), "ᓀᐦᐃᔭᐍᐏᐣ", "", "", ()),
		"cs": ("Czech", _("Czech"), "Čeština / Český Jazyk", "ISO-8859-15", "qwertz", ("CZ",)),
		"cu": ("Church Slavic", _("Church Slavic"), "Ѩзыкъ Словѣньскъ", "", "", ()),
		"cv": ("Chuvash", _("Chuvash"), "Чӑваш Чӗлхи", "", "", ("RU",)),
		"cy": ("Welsh", _("Welsh"), "Cymraeg", "", "", ("GB",)),
		"da": ("Danish", _("Danish"), "Dansk", "ISO-8859-15", "", ("DK",)),
		"de": ("German", _("German"), "Deutsch", "ISO-8859-15", "qwertz", ("DE", "AT", "BE", "CH", "IT", "LI", "LU")),
		"dv": ("Divehi / Dhivehi / Maldivian", _("Divehi / Dhivehi / Maldivian"), "ދިވެހި", "", "", ("MV",)),
		"dz": ("Dzongkha", _("Dzongkha"), "རྫོང་ཁ", "", "", ("BT",)),
		"ee": ("Ewe", _("Ewe"), "Eʋegbe", "", "", ()),
		"el": ("Greek", _("Greek"), "Ελληνικά", "ISO-8859-7", "", ("GR", "CY")),
		"en": ("English", _("English"), "English", "ISO-8859-15", "", ("US", "AG", "AU", "BW", "BZ", "CA", "DK", "GB", "HK", "IE", "IL", "IN", "JM", "KH", "NG", "NZ", "PH", "SC", "SG", "TT", "ZA", "ZM", "ZW")),
		"eo": ("Esperanto", _("Esperanto"), "Esperanto", "", "", ()),
		"es": ("Spanish / Castilian", _("Spanish / Castilian"), "Español", "ISO-8859-15", "", ("ES", "AR", "BO", "CL", "CO", "CR", "CU", "DO", "EC", "GT", "HN", "MX", "NI", "PA", "PE", "PR", "PY", "SV", "US", "UY", "VE")),
		"et": ("Estonian", _("Estonian"), "Eesti / Eesti keel", "ISO-8859-15", "", ("EE",)),
		"eu": ("Basque", _("Basque"), "Euskara / Euskera", "", "", ("ES",)),
		"fa": ("Farsi / Persian", _("Farsi / Persian"), "فارسی", "ISO-8859-15", "", ("IR",)),
		"ff": ("Fulah", _("Fulah"), "Fulfulde / Pulaar / Pular", "", "", ("SN",)),
		"fi": ("Finnish", _("Finnish"), "Suomi / Suomen kieli", "ISO-8859-15", "", ("FI",)),
		"fj": ("Fijian", _("Fijian"), "Vosa Vakaviti", "", "", ()),
		"fo": ("Faroese", _("Faroese"), "Føroyskt", "", "", ("FO",)),
		"fr": ("French", _("French"), "Français", "ISO-8859-15", "azerty", ("FR", "AG", "AI", "BE", "BB", "BS", "CA", "CG", "CH", "CI", "CM", "CU", "DO", "DM", "GD", "GY", "HT", "JM", "KN", "LC", "LU", "MA", "MC", "ML", "MQ", "PR", "SN", "SR", "SX", "TT", "VC", "VI")),
		"fy": ("Western Frisian", _("Western Frisian"), "Frysk", "ISO-8859-15", "", ("NL", "DE")),
		"ga": ("Irish", _("Irish"), "Gaeilge", "", "", ("IE",)),
		"gd": ("Gaelic", _("Gaelic"), "Gàidhlig", "", "", ("GB",)),
		"gl": ("Galician", _("Galician"), "Galego", "", "", ("ES-GA",)),
		"gn": ("Guarani", _("Guarani"), "Avañe'ẽ", "", "", ("PY",)),
		"gu": ("Gujarati", _("Gujarati"), "ગુજરાતી", "", "", ("IN",)),
		"gv": ("Manx", _("Manx"), "Gaelg / Gailck", "", "", ("GB",)),
		"ha": ("Hausa", _("Hausa"), "هَوُسَ", "", "", ("NG",)),
		"he": ("Hebrew", _("Hebrew"), "עברית‎", "ISO-8859-15", "", ("IL",)),
		"hi": ("Hindi", _("Hindi"), "हिन्दी / हिंदी", "", "", ("IN",)),
		"ho": ("Hiri Motu", _("Hiri Motu"), "Hiri Motu", "", "", ()),
		"hr": ("Croatian", _("Croatian"), "Hrvatski Jezik", "ISO-8859-15", "", ("HR",)),
		"ht": ("Haitian / Haitian Creole", _("Haitian / Haitian Creole"), "Kreyòl ayisyen", "", "", ("HT",)),
		"hu": ("Hungarian", _("Hungarian"), "Magyar", "ISO-8859-15", "qwertz", ("HU",)),
		"hy": ("Armenian", _("Armenian"), "Հայերեն", "", "", ("AM",)),
		"hz": ("Herero", _("Herero"), "Otjiherero", "", "", ()),
		"ia": ("Interlingua", _("Interlingua"), "Interlingua", "", "", ("FR",)),
		"id": ("Indonesian", _("Indonesian"), "Bahasa Indonesia", "ISO-8859-15", "", ("ID",)),
		"ie": ("Interlingue / Occidental", _("Interlingue / Occidental"), "Interlingue", "", "", ()),
		"ig": ("Igbo", _("Igbo"), "Asụsụ Igbo", "", "", ("NG",)),
		"ii": ("Sichuan Yi / Nuosu", _("Sichuan Yi / Nuosu"), "ꆈꌠ꒿ Nuosuhxop", "", "", ()),
		"ik": ("Inupiaq", _("Inupiaq"), "Iñupiaq / Iñupiatun", "", "", ("CA",)),
		"io": ("Ido", _("Ido"), "Ido", "", "", ()),
		"is": ("Icelandic", _("Icelandic"), "Íslenska", "ISO-8859-15", "", ("IS",)),
		"it": ("Italian", _("Italian"), "Italiano", "ISO-8859-15", "", ("IT", "CH")),
		"iu": ("Inuktitut", _("Inuktitut"), "ᐃᓄᒃᑎᑐᑦ", "", "", ("CA",)),
		"ja": ("Japanese", _("Japanese"), "日本語 (にほんご)", "", "", ("JP",)),
		"jv": ("Javanese", _("Javanese"), "ꦧꦱꦗꦮ / Basa Jawa", "", "", ()),
		"ka": ("Georgian", _("Georgian"), "ქართული", "", "", ("GE",)),
		"kg": ("Kongo", _("Kongo"), "Kikongo", "", "", ()),
		"ki": ("Kikuyu / Gikuyu", _("Kikuyu / Gikuyu"), "Gĩkũyũ", "", "", ()),
		"kj": ("Kuanyama / Kwanyama", _("Kuanyama / Kwanyama"), "Kuanyama", "", "", ()),
		"kk": ("Kazakh", _("Kazakh"), "Қазақ тілі", "", "", ("KZ",)),
		"kl": ("Kalaallisut / Greenlandic", _("Kalaallisut / Greenlandic"), "Kalaallisut / Kalaallit oqaasii", "", "", ("GL",)),
		"km": ("Central Khmer", _("Central Khmer"), "ខ្មែរ, ខេមរភាសា, ភាសាខ្មែរ", "", "", ("KH",)),
		"kn": ("Kannada", _("Kannada"), "ಕನ್ನಡ", "", "", ("IN",)),
		"ko": ("Korean", _("Korean"), "한국어", "", "", ("KR",)),
		"kr": ("Kanuri", _("Kanuri"), "Kanuri", "", "", ()),
		"ks": ("Kashmiri", _("Kashmiri"), "कश्मीरी / كشميري", "", "", ("IN",)),
		"ku": ("Kurdish", _("Kurdish"), "Kurdî / کوردی", "ISO-8859-15", "", ("KU",)),
		"kv": ("Komi", _("Komi"), "Коми кыв", "", "", ()),
		"kw": ("Cornish", _("Cornish"), "Kernewek", "", "", ("GB",)),
		"ky": ("Kirghiz / Kyrgyz", _("Kirghiz / Kyrgyz"), "Кыргызча, Кыргыз тили", "", "", ("KG",)),
		"la": ("Latin", _("Latin"), "Latine / Lingua Latina", "", "", ()),
		"lb": ("Luxembourgish / Letzeburgesch", _("Luxembourgish / Letzeburgesch"), "Lëtzebuergesch", "", "", ("LU",)),
		"lg": ("Ganda", _("Ganda"), "Luganda", "", "", ("UG",)),
		"li": ("Limburgan / Limburger / Limburgish", _("Limburgan / Limburger / Limburgish"), "Limburgs", "", "", ("BE", "NL")),
		"ln": ("Lingala", _("Lingala"), "Lingála", "", "", ("CD",)),
		"lo": ("Lao", _("Lao"), "ພາສາລາວ", "", "", ("LA",)),
		"lt": ("Lithuanian", _("Lithuanian"), "Lietuvių Kalba", "ISO-8859-15", "", ("LT",)),
		"lu": ("Luba-Katanga", _("Luba-Katanga"), "Kiluba", "", "", ()),
		"lv": ("Latvian", _("Latvian"), "Latviešu Valoda", "ISO-8859-15", "", ("LV",)),
		"mg": ("Malagasy", _("Malagasy"), "Fiteny Malagasy", "", "", ("MG",)),
		"mh": ("Marshallese", _("Marshallese"), "Kajin M̧ajeļ", "", "", ("MH",)),
		"mi": ("Maori", _("Maori"), "te reo Māori", "", "", ("NZ",)),
		"mk": ("Macedonian", _("Macedonian"), "Македонски Јазик", "", "", ("MK",)),
		"ml": ("Malayalam", _("Malayalam"), "മലയാളം", "", "", ("IN",)),
		"mn": ("Mongolian", _("Mongolian"), "Монгол хэл", "", "", ("MN",)),
		"mr": ("Marathi", _("Marathi"), "मराठी", "", "", ("IN",)),
		"ms": ("Malay", _("Malay"), "Bahasa Melayu, بهاس ملايو", "", "", ("MY",)),
		"mt": ("Maltese", _("Maltese"), "Malti", "", "", ("MT",)),
		"my": ("Burmese", _("Burmese"), "ဗမာစာ", "", "", ("MM",)),
		"na": ("Nauru", _("Nauru"), "Dorerin Naoero", "", "", ()),
		"nb": ("Norwegian Bokml", _("Norwegian Bokml"), "Norsk Bokmål", "ISO-8859-15", "", ("NO",)),
		"nd": ("North Ndebele", _("North Ndebele"), "isiNdebele", "", "", ()),
		"ne": ("Nepali", _("Nepali"), "नेपाली", "", "", ("NP",)),
		"ng": ("Ndonga", _("Ndonga"), "Owambo", "", "", ()),
		"nl": ("Dutch / Flemish", _("Dutch / Flemish"), "Nederlands / Vlaams", "ISO-8859-15", "", ("NL", "AW", "BE")),
		"nn": ("Norwegian Nynorsk", _("Norwegian Nynorsk"), "Norsk Nynorsk", "", "", ("NO",)),
		"no": ("Norwegian", _("Norwegian"), "Norsk", "ISO-8859-15", "", ("NO",)),
		"nr": ("South Ndebele", _("South Ndebele"), "isiNdebele", "", "", ("ZA",)),
		"nv": ("Navajo / Navaho", _("Navajo / Navaho"), "Diné bizaad", "", "", ()),
		"ny": ("Chichewa / Chewa / Nyanja", _("Chichewa / Chewa / Nyanja"), "ChiCheŵa / Chinyanja", "", "", ()),
		"oc": ("Occitan", _("Occitan"), "Occitan / Lenga D'òc", "", "", ("FR",)),
		"oj": ("Ojibwa", _("Ojibwa"), "ᐊᓂᔑᓈᐯᒧᐎᓐ", "", "", ()),
		"om": ("Oromo", _("Oromo"), "Afaan Oromoo", "", "", ("ET", "KE")),
		"or": ("Oriya", _("Oriya"), "ଓଡ଼ିଆ", "", "", ("IN",)),
		"os": ("Ossetian / Ossetic", _("Ossetian / Ossetic"), "Ирон Æвзаг", "", "", ("RU",)),
		"pa": ("Panjabi / Punjabi", _("Panjabi / Punjabi"), "ਪੰਜਾਬੀ, پنجابی", "", "", ("IN", "PK")),
		"pi": ("Pali", _("Pali"), "पालि, पाळि", "", "", ()),
		"pl": ("Polish", _("Polish"), "Język Polski, Polszczyzna", "ISO-8859-15", "qwertz", ("PL",)),
		"ps": ("Pushto / Pashto", _("Pushto / Pashto"), "پښتو", "", "", ("AF",)),
		"pt": ("Portuguese", _("Portuguese"), "Português", "ISO-8859-15", "", ("PT", "BR")),
		"qu": ("Quechua", _("Quechua"), "Runa Simi, Kichwa", "", "", ()),
		"rm": ("Romansh", _("Romansh"), "Rumantsch Grischun", "", "", ()),
		"rn": ("Rundi", _("Rundi"), "Ikirundi", "", "", ()),
		"ro": ("Romanian", _("Romanian"), "Română", "ISO-8859-15", "qwertz", ("RO",)),
		"ru": ("Russian", _("Russian"), "Русский", "ISO-8859-15", "", ("RU", "UA")),
		"rw": ("Kinyarwanda", _("Kinyarwanda"), "Ikinyarwanda", "", "", ("RW",)),
		"sa": ("Sanskrit", _("Sanskrit"), "संस्कृतम्", "", "", ("IN",)),
		"sb": ("Sorbian", _("Sorbian"), "Sorbian", "", "", ()),  # Not in Wikipedia.
		"sc": ("Sardinian", _("Sardinian"), "Sardu", "", "", ("IT",)),
		"sd": ("Sindhi", _("Sindhi"), "सिन्धी, سنڌي، سندھی", "", "", ("IN",)),
		"se": ("Northern Sami", _("Northern Sami"), "Davvisámegiella", "", "", ("NO",)),
		"sg": ("Sango", _("Sango"), "Yângâ tî sängö", "", "", ()),
		"si": ("Sinhala / Sinhalese", _("Sinhala / Sinhalese"), "සිංහල", "", "", ("LK",)),
		"sk": ("Slovak", _("Slovak"), "Slovenčina / Slovenský Jazyk", "ISO-8859-15", "qwertz", ("SK",)),
		"sl": ("Slovenian", _("Slovenian"), "Slovenski Jezik / Slovenščina", "ISO-8859-15", "qwertz", ("SI",)),
		"sm": ("Samoan", _("Samoan"), "Gagana Fa'a Samoa", "", "", ("WS",)),
		"sn": ("Shona", _("Shona"), "chiShona", "", "", ()),
		"so": ("Somali", _("Somali"), "Soomaaliga, af Soomaali", "", "", ("DJ", "ET", "KE", "SO")),
		"sq": ("Albanian", _("Albanian"), "Shqip", "", "", ("AL", "KV", "MK")),
		"sr": ("Serbian", _("Serbian"), "Српски Језик", "ISO-8859-15", "qwertz", ("RS", "ME")),
		"ss": ("Swati", _("Swati"), "SiSwati", "", "", ("ZA",)),
		"st": ("Sotho, Southern", _("Sotho, Southern"), "Sesotho", "", "", ("ZA",)),
		"su": ("Sundanese", _("Sundanese"), "Basa Sunda", "", "", ("SD",)),
		"sv": ("Swedish", _("Swedish"), "Svenska", "ISO-8859-15", "", ("SE", "FI")),
		"sw": ("Swahili", _("Swahili"), "Kiswahili", "", "", ("KE", "TZ")),
		"ta": ("Tamil", _("Tamil"), "தமிழ்", "", "", ("IN", "LK")),
		"te": ("Telugu", _("Telugu"), "తెలుగు", "", "", ("IN",)),
		"tg": ("Tajik", _("Tajik"), "тоҷикӣ, toçikī, تاجیکی", "", "", ("TJ",)),
		"th": ("Thai", _("Thai"), "ไทย", "ISO-8859-15", "", ("TH",)),
		"ti": ("Tigrinya", _("Tigrinya"), "ትግርኛ", "", "", ("ER", "ET")),
		"tk": ("Turkmen", _("Turkmen"), "Türkmen, Түркмен", "", "", ("TM",)),
		"tl": ("Tagalog", _("Tagalog"), "Wikang Tagalog", "", "", ("PH",)),
		"tn": ("Tswana", _("Tswana"), "Setswana", "", "", ("ZA",)),
		"to": ("Tonga", _("Tonga"), "Faka Tonga", "", "", ("TO",)),
		"tr": ("Turkish", _("Turkish"), "Türkçe", "ISO-8859-15", "", ("TR", "CY")),
		"ts": ("Tsonga", _("Tsonga"), "Xitsonga", "", "", ("ZA",)),
		"tt": ("Tatar", _("Tatar"), "Татар теле, Tatar tele", "", "", ("RU",)),
		"tw": ("Twi", _("Twi"), "Twi", "", "", ()),
		"ty": ("Tahitian", _("Tahitian"), "Reo Tahiti", "", "", ()),
		"ug": ("Uighur / Uyghur", _("Uighur / Uyghur"), "ئۇيغۇرچە‎ / Uyghurche", "", "", ("CN",)),
		"uk": ("Ukrainian", _("Ukrainian"), "Українська", "ISO-8859-15", "", ("UA",)),
		"ur": ("Urdu", _("Urdu"), "اردو", "", "", ("IN", "PK")),
		"uz": ("Uzbek", _("Uzbek"), "Oʻzbek, Ўзбек, أۇزبېك", "", "", ("UZ",)),
		"ve": ("Venda", _("Venda"), "Tshivenḓa", "", "", ("ZA",)),
		"vi": ("Vietnamese", _("Vietnamese"), "Tiếng Việt", "", "", ("VN",)),
		"vo": ("Volapük", _("Volapük"), "Volapük", "", "", ()),
		"wa": ("Walloon", _("Walloon"), "Walon", "", "", ("BE",)),
		"wo": ("Wolof", _("Wolof"), "Wollof", "", "", ("SN",)),
		"xh": ("Xhosa", _("Xhosa"), "isiXhosa", "", "", ("ZA",)),
		"yi": ("Yiddish", _("Yiddish"), "ייִדיש", "", "", ("US",)),
		"yo": ("Yoruba", _("Yoruba"), "Yorùbá", "", "", ("NG",)),
		"za": ("Zhuang / Chuang", _("Zhuang / Chuang"), "Saɯ cueŋƅ / Saw cuengh", "", "", ()),
		"zh": ("Chinese", _("Chinese"), "中文", "", "", ("CN", "HK", "SG", "TW")),
		"zu": ("Zulu", _("Zulu"), "isiZulu", "", "", ("ZA",))
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
		# https://en.wikipedia.org/wiki/List_of_ISO_3166_country_codes
		# https://en.wikipedia.org/wiki/ISO_3166-2
		# https://en.wikipedia.org/wiki/ISO_3166-3
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
		"ES-GA": ("ESP", "724", "Galicia (Spain)", _("Galicia (Spain)"), "Galicia (España)"),
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
		"HT": ("HTI", "332", "Haiti", _("Haiti"), "Haïti"),
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
		"KU": ("KUR", "369", "Kurdistan", _("Kurdistan"), "کوردستان"),
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
		"TH": ("THA", "764", "Thailand", _("Thailand"), "ประเทศไทย"),
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
		("LC_ALL", LC_ALL),
		("LC_ADDRESS", None),
		("LC_COLLATE", LC_COLLATE),
		("LC_CTYPE", LC_CTYPE),
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

	def __init__(self):
		print("[International] International component is initializing.")
		lines = []
		lines = fileReadLines(resolveFilename(SCOPE_CONFIG, "settings"), default=lines, source=MODULE_NAME)
		self.debugMode = "config.crash.debugInternational=True" in lines
		self.availablePackages = []
		self.installedPackages = []
		self.installedDirectories = []
		self.packageLocales = {}
		self.localeList = ["en_US"]
		self.languageList = ["en"]
		self.activeLocale = "en_US"
		self.catalog = None
		self.callbacks = []
		# environ["LANG"] = "C.UTF-8"  # Force the environment to US English so all shell commands run from Enigma2 can be parsed in English (as coded).
		# environ["LANGUAGE"] = "C.UTF-8"
		self.initInternational()

	def initInternational(self):
		print("[International] Initializing locales/languages.")
		self.availablePackages = self.getAvailablePackages(update=True)
		self.installedPackages = self.getInstalledPackages(update=True)
		self.installedDirectories = self.getInstalledDirectories(update=True)
		if len(self.installedDirectories) != len(self.installedPackages):
			print("[International] Warning: Count of installed locale/language packages and locale/language directory entries do not match!")
		self.packageLocales = {}
		for package in self.installedPackages:
			locales = self.packageToLocales(package)
			packageLocales = []
			for locale in locales:
				if locale not in packageLocales:
					packageLocales.append(locale)
				if locale not in self.localeList:
					self.localeList.append(locale)
			self.packageLocales[package] = packageLocales
			language = self.splitPackage(package)[0]
			if language not in self.languageList:
				self.languageList.append(language)
			count = len(packageLocales)
			if self.debugMode:
				print(f"[International] Package '{package}' supports {count} locale{'' if count == 1 else 's'} '{"', '".join(packageLocales)}'.")
		self.localeList.sort()
		self.languageList.sort()

	def getAvailablePackages(self, update=False):
		if update or self.debugMode:
			print(f"[International] There are {len(self.DEFINED_LOCALES)} available locale/language packages in the repository '{"', '".join(self.DEFINED_LOCALES)}'.")
		return self.DEFINED_LOCALES

	def getInstalledPackages(self, update=False):
		if update:
			installedPackages = []
			for file in listdir("/var/lib/opkg/info"):
				if file.startswith("enigma2-locale-") and file.endswith(".control") and "meta" not in file:
					installedPackages.append(file[15:].split(".")[0])
			installedPackages.sort()
			if self.debugMode:
				print(f"[International] There are {len(installedPackages)} installed locale/language packages '{"', '".join(installedPackages)}'.")
		else:
			installedPackages = self.installedPackages
		return installedPackages

	def getInstalledDirectories(self, update=False):  # Adapt language directory entries to match the package format.
		if update:
			global languagePath
			installedDirectories = sorted(listdir(languagePath)) if isdir(languagePath) else []
			if self.debugMode:
				print(f"[International] There are {len(installedDirectories)} installed locale/language directories '{"', '".join(installedDirectories)}'.")
		else:
			installedDirectories = self.installedDirectories
		return installedDirectories

	def getLocale(self):
		return "en_US" if self.activeLocale is None else self.activeLocale

	def splitLocale(self, locale):
		data = locale.split("_", 1)
		if len(data) < 2:
			data.append(None)
		return data

	def getLanguage(self, locale=None):
		if locale is None:
			locale = self.getLocale()
		return self.splitLocale(locale)[0] if len(locale) > 3 else locale  # and locale in self.LANGUAGE_DATA or None

	def getLanguageName(self, item=None):
		return self.LANGUAGE_DATA.get(self.getLanguage(item), tuple([None] * self.LANG_MAX))[self.LANG_NAME]

	def getLanguageTranslated(self, item=None):
		return self.LANGUAGE_DATA.get(self.getLanguage(item), tuple([None] * self.LANG_MAX))[self.LANG_TRANSLATED]

	def getLanguageNative(self, item=None):
		return self.LANGUAGE_DATA.get(self.getLanguage(item), tuple([None] * self.LANG_MAX))[self.LANG_NATIVE]

	def getLanguageEncoding(self, item=None):
		return self.LANGUAGE_DATA.get(self.getLanguage(item), tuple([None] * self.LANG_MAX))[self.LANG_ENCODING] or "UTF-8"

	def getLanguageKeyboard(self, item=None):
		return self.LANGUAGE_DATA.get(self.getLanguage(item), tuple([None] * self.LANG_MAX))[self.LANG_KEYBOARD] or "qwerty"

	def getLanguageCountryCode(self, item=None):
		countries = self.LANGUAGE_DATA.get(self.getLanguage(item), tuple([None] * self.LANG_MAX))[self.LANG_COUNTRYCODES]
		return countries[0] if countries else None

	def getCountry(self, locale=None):
		if locale is None:
			locale = self.getLocale()
		return self.splitLocale(locale)[1] if len(locale) > 3 else locale  # and locale in self.COUNTRY_DATA or None

	def getCountryAlpha3(self, item=None):
		return self.COUNTRY_DATA.get(self.getCountry(item), tuple([None] * self.COUNTRY_MAX))[self.COUNTRY_ALPHA3]

	def getCountryNumeric(self, item=None):
		return self.COUNTRY_DATA.get(self.getCountry(item), tuple([None] * self.COUNTRY_MAX))[self.COUNTRY_NUMERIC]

	def getCountryName(self, item=None):
		return self.COUNTRY_DATA.get(self.getCountry(item), tuple([None] * self.COUNTRY_MAX))[self.COUNTRY_NAME]

	def getCountryTranslated(self, item=None):
		return self.COUNTRY_DATA.get(self.getCountry(item), tuple([None] * self.COUNTRY_MAX))[self.COUNTRY_TRANSLATED]

	def getCountryNative(self, item=None):
		return self.COUNTRY_DATA.get(self.getCountry(item), tuple([None] * self.COUNTRY_MAX))[self.COUNTRY_NATIVE]

	def getNIMCountries(self):
		nimCountries = {}
		for country in self.COUNTRY_DATA.keys():
			nimCountries[self.COUNTRY_DATA[country][self.COUNTRY_ALPHA3]] = self.COUNTRY_DATA[country][self.COUNTRY_TRANSLATED]
		return nimCountries

	def addCallback(self, callback):
		if not callback:
			print(f"[International] Error: The callback '{callback}' can't be empty!")
		elif not callable(callback):
			print(f"[International] Error: The callback '{callback}' is invalid!")
		elif callback in self.callbacks:
			print(f"[International] Error: The callback '{callback}' is already defined!")
		else:
			self.callbacks.append(callback)

	def removeCallback(self, callback):
		if callback in self.callbacks:
			self.callbacks.remove(callback)
		else:
			print(f"[International] Error: The callback '{callback}' is invalid!")

	def activateLocale(self, locale, runCallbacks=True):
		if locale not in self.localeList:
			print(f"[International] Selected locale '{locale}' is not installed or does not exist!")
		elif locale == self.activeLocale:
			print(f"[International] Language '{self.getLanguage(locale)}', locale '{locale}' is already active.")
		else:
			print(f"[International] Activating language '{self.getLanguage(locale)}', locale '{locale}'.")
			global languagePath
			try:
				self.catalog = translation("enigma2", languagePath, languages=[locale], fallback=True)
			except UnicodeDecodeError:
				print(f"[International] Error: The language translation data in '{languagePath}' for '{self.getLanguage(locale)}' ('{locale}') has failed to initialize!")
				self.catalog = translation("enigma2", "/", fallback=True)
			self.catalog.install(names=("ngettext", "pgettext"))
			for category in self.CATEGORIES:
				environ[category[self.CAT_ENVIRONMENT]] = f"{locale}.UTF-8"
				localeError = None
				if category[self.CAT_PYTHON] is not None:
					try:  # Try and set the Python locale to the current locale.
						setlocale(category[self.CAT_PYTHON], locale=(locale, "UTF-8"))
					except LocaleError:
						try:  # If unavailable, try for the Python locale to the language base locale.
							locales = self.packageToLocales(self.getLanguage(locale))
							setlocale(category[self.CAT_PYTHON], locale=(locales[0], "UTF-8"))
							replacement = locales[0]
						except LocaleError:  # If unavailable fall back to the US English locale.
							setlocale(category[self.CAT_PYTHON], locale=("POSIX", ""))
							replacement = "POSIX"
						if localeError is None:
							localeError = replacement
							print(f"[International] Warning: Locale '{locale}' is not available in Python {category[self.CAT_ENVIRONMENT]}, using locale '{replacement}' instead.")
			environ["LC_ALL"] = ""  # This is cleared by popular request.
			environ["LC_TIME"] = f"{locale}.UTF-8"  # Python 2.7 sometimes reverts the LC_TIME environment value, so make sure it has the correct value!
			environ["LANG"] = f"{locale}.UTF-8"
			environ["LANGUAGE"] = f"{locale}.UTF-8"
			environ["GST_SUBTITLE_ENCODING"] = self.getGStreamerSubtitleEncoding()
			self.activeLocale = locale
		if runCallbacks:
			for callback in self.callbacks:
				callback()

	def getActiveCatalog(self):
		return self.catalog

	def getPurgablePackages(self, locale=None):
		if locale is None:
			locale = self.getLocale()
		locales = self.PERMANENT_LOCALES[:]
		if locale not in locales:
			locales.append(locale)
		locales.sort()
		packages = sorted(self.installedPackages)
		for locale in locales:
			for package in packages[:]:
				if locale in self.packageLocales[package]:
					packages.remove(package)
		return packages

	def getPermanentLocales(self, locale=None):
		if locale is None:
			locale = self.getLocale()
		locales = self.PERMANENT_LOCALES[:]
		if locale not in locales:
			locales.append(locale)
		permanent = []
		for locale in locales:
			permanent.append(f"{self.getLanguageName(locale)} ({self.getCountryName(locale)})")
		return permanent

	def packageToLocales(self, package):
		locale = package.replace("-", "_")
		data = self.splitLocale(locale)
		locales = []
		if data[1]:
			locales.append(f"{data[0]}_{data[1].upper()}")
		else:
			for country in self.LANGUAGE_DATA.get(data[0], tuple([None] * self.LANG_MAX))[self.LANG_COUNTRYCODES]:
				locales.append(f"{data[0]}_{country}")
		return locales

	def localeToPackage(self, locale=None):
		if locale is None:
			locale = self.getLocale()
		for package in self.availablePackages:
			if locale in self.packageLocales[package]:
				return package
		return None

	def languageToPackage(self, language=None):
		if language is None:
			language = self.getLanguage()
		for package in self.availablePackages:
			for locale in self.packageLocales[package]:
				if language == self.getLanguage(locale):
					return package
		return None

	def splitPackage(self, package):
		data = package.split("-", 1)
		if len(data) < 2:
			data.append(None)
		else:
			data[1] = data[1].upper()
		return data

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
		return self.LANGUAGE_DATA[language][self.LANG_ENCODING] if language in self.LANGUAGE_DATA else "ISO-8859-15"


international = International()
