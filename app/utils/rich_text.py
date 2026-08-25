from urllib.parse import urlsplit

import bleach


ALLOWED_TAGS = {
	"p",
	"br",
	"strong",
	"em",
	"u",
	"ul",
	"ol",
	"li",
	"a",
	"span",
	"font",
	"h1",
	"h2",
	"h3",
	"table",
	"caption",
	"thead",
	"tbody",
	"tfoot",
	"tr",
	"th",
	"td",
}
ALLOWED_ATTRIBUTES = {"a": ["href", "target", "rel"], "span": ["class", "style"], "font": ["color", "face", "size"]}
ALLOWED_PROTOCOLS = {"http", "https"}
ALLOWED_CLASSES = {"text-color-red", "text-color-blue", "text-color-green", "highlight-yellow", "highlight-blue", "highlight-green"}
ALLOWED_COLORS = {"#b42318", "#176b87", "#2f7d32", "#d65a68", "rgb(180, 35, 24)", "rgb(23, 107, 135)", "rgb(47, 125, 50)", "rgb(214, 90, 104)"}
ALLOWED_HIGHLIGHTS = {"background-color: rgb(255, 240, 168)", "background-color: rgb(207, 235, 255)", "background-color: rgb(211, 241, 214)", "background-color: rgb(84, 38, 44)"}
ALLOWED_FONT_FAMILIES = {"serif", "sans-serif", "monospace", "Georgia", "Verdana", "Courier New"}
ALLOWED_FONT_SIZES = {"1", "2", "3", "4", "5", "6", "7"}


def _link_is_safe(value):
	parts = urlsplit(value)
	return parts.scheme.lower() in ALLOWED_PROTOCOLS and bool(parts.netloc)


def _filter_attributes(tag, name, value):
	if tag in {"td", "th"} and name in {"rowspan", "colspan"}:
		try:
			return 1 <= int(value) <= 20
		except (TypeError, ValueError):
			return False
	if tag == "th" and name == "scope":
		return value in {"row", "col"}
	if tag == "a" and name == "href":
		return _link_is_safe(value)
	if tag == "a" and name in {"target", "rel"}:
		return True
	if tag == "span" and name == "class":
		return set(value.split()).issubset(ALLOWED_CLASSES)
	if tag == "span" and name == "style":
		return value.strip().lower().rstrip(";") in {item.lower() for item in ALLOWED_HIGHLIGHTS}
	if tag == "font" and name == "color":
		return value.strip().lower() in {item.lower() for item in ALLOWED_COLORS}
	if tag == "font" and name == "face":
		return value.strip() in ALLOWED_FONT_FAMILIES
	if tag == "font" and name == "size":
		return value.strip() in ALLOWED_FONT_SIZES
	return False


def sanitize_rich_text(value):
	cleaned = bleach.clean(
		str(value or ""),
		tags=ALLOWED_TAGS,
		attributes=_filter_attributes,
		protocols=ALLOWED_PROTOCOLS,
		strip=True,
		strip_comments=True,
	)
	return cleaned.strip()


def rich_text_plain(value):
	return bleach.clean(str(value or ""), tags=[], strip=True).strip()