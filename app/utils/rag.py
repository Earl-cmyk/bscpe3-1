import re


CHUNK_WORDS = 450
CHUNK_OVERLAP = 60
STOP_WORDS = {"a", "about", "an", "and", "are", "how", "i", "is", "me", "of", "on", "the", "to", "what", "you"}


def note_chunks(title, caption, chunk_words=CHUNK_WORDS, overlap=CHUNK_OVERLAP):
	text = " ".join(f"{title}\n{caption}".split())
	words = text.split()
	if not words:
		return []
	step = max(1, chunk_words - overlap)
	return [" ".join(words[start:start + chunk_words]) for start in range(0, len(words), step)]


def query_terms(query):
	return {term.casefold() for term in re.findall(r"[\w]+", str(query or "")) if term.casefold() not in STOP_WORDS}


def rank_chunks(chunks, query, limit=5):
	terms = query_terms(query)
	if not terms:
		return []
	results = []
	for chunk in chunks:
		content = str(chunk.get("content", ""))
		words = re.findall(r"[\w]+", content.casefold())
		counts = {term: words.count(term) for term in terms}
		score = sum(min(count, 3) for count in counts.values())
		if score:
			results.append((score, chunk))
	return [chunk for _, chunk in sorted(results, key=lambda item: (-item[0], item[1].get("chunk_index", 0)))[:limit]]