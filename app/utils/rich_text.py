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
}
ALLOWED_ATTRIBUTES = {"a": ["href", "target", "rel"], "span": ["class", "style"], "font": ["color"]}
ALLOWED_PROTOCOLS = {"http", "https"}
ALLOWED_CLASSES = {"text-color-red", "text-color-blue", "text-color-green", "highlight-yellow", "highlight-blue", "highlight-green"}
ALLOWED_COLORS = {"#b42318", "#176b87", "#2f7d32", "rgb(180, 35, 24)", "rgb(23, 107, 135)", "rgb(47, 125, 50)"}
ALLOWED_HIGHLIGHTS = {"background-color: rgb(255, 240, 168)", "background-color: rgb(207, 235, 255)", "background-color: rgb(211, 241, 214)"}


def _link_is_safe(value):
	parts = urlsplit(value)
	return parts.scheme.lower() in ALLOWED_PROTOCOLS and bool(parts.netloc)


def _filter_attributes(tag, name, value):
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