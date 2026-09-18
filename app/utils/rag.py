import re


CHUNK_WORDS = 450
CHUNK_OVERLAP = 60
STOP_WORDS = {"a", "about", "an", "and", "are", "can", "do", "does", "explain", "from", "how", "i", "in", "is", "me", "my", "of", "on", "please", "teach", "the", "to", "what", "you"}


def note_chunks(title, caption, chunk_words=CHUNK_WORDS, overlap=CHUNK_OVERLAP):
	text = " ".join(f"{title}\n{caption}".split())
	words = text.split()
	if not words:
		return []
	step = max(1, chunk_words - overlap)
	return [" ".join(words[start:start + chunk_words]) for start in range(0, len(words), step)]


def query_terms(query):
	return {term.casefold().strip("_'’") for term in re.findall(r"[\w]+(?:['’][\w]+)?", str(query or "")) if term.casefold().strip("_'’") not in STOP_WORDS}


def rank_chunks(chunks, query, limit=5):
	query_text = " ".join(str(query or "").casefold().split())
	terms = query_terms(query_text)
	if not terms:
		return []
	results = []
	for chunk in chunks:
		content = str(chunk.get("content", ""))
		content_text = " ".join(content.casefold().split())
		words = re.findall(r"[\w]+(?:['’][\w]+)?", content_text)
		counts = {term: words.count(term) for term in terms}
		score = sum(min(count, 3) for count in counts.values())
		if query_text and query_text in content_text:
			score += 8
		if str(chunk.get("title", "")).casefold() and all(term in str(chunk.get("title", "")).casefold() for term in terms):
			score += 5
		if str(chunk.get("course", "")).casefold() and str(chunk.get("course", "")).casefold() in query_text:
			score += 3
		if score:
			result = dict(chunk)
			result["score"] = score
			results.append((score, result))
	return [chunk for _, chunk in sorted(results, key=lambda item: (-item[0], item[1].get("chunk_index", 0), item[1].get("note_id", 0)))[:limit]]