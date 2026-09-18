import re


NO_CONTEXT_MESSAGE = "I couldn't find enough information about that in your Notes."


def study_mode(text):
    value = str(text or "").casefold()
    if re.search(r"\b(quiz|test me|ask me)\b", value):
        return "quiz"
    if re.search(r"\b(practice|problem|exercise|drill)\b", value):
        return "practice"
    if re.search(r"\b(review|revise|what should i study|study plan)\b", value):
        return "review"
    return "explain"


def compose_study_response(query, matches, mode="explain"):
    if not matches:
        return {
            "mode": mode,
            "message": NO_CONTEXT_MESSAGE,
            "answer": "",
            "sections": [],
            "sources": [],
            "coverage": 0.0,
        }

    sources = [_source(match) for match in matches]
    if mode == "quiz":
        return _quiz_response(query, matches, sources)
    if mode == "practice":
        return _practice_response(query, matches, sources)
    if mode == "review":
        return _review_response(matches, sources)
    sections = _explanation_sections(query, matches)
    answer = "\n\n".join(section["text"] for section in sections)
    return {
        "mode": "explain",
        "message": answer,
        "answer": answer,
        "sections": sections,
        "sources": sources,
        "coverage": _coverage(matches),
    }


def _explanation_sections(query, matches):
    terms = _terms(query)
    selected = []
    seen = set()
    for match in matches:
        content = str(match.get("content") or match.get("snippet") or "")
        sentences = _sentences(content)
        relevant = [sentence for sentence in sentences if not terms or terms.intersection(_terms(sentence))]
        for sentence in relevant or sentences[:2]:
            normalized = " ".join(sentence.casefold().split())
            if normalized and normalized not in seen:
                seen.add(normalized)
                selected.append((sentence, match))
            if len(selected) >= 8:
                break
        if len(selected) >= 8:
            break
    grouped = []
    for sentence, match in selected:
        source = _source_label(match)
        grouped.append({"text": sentence, "source": source, "source_id": match.get("note_id")})
    return grouped


def _quiz_response(query, matches, sources):
    topic = _topic_label(query, matches)
    answer = f"Quiz: Explain {topic} using your Notes. Include the definition, the main steps, and one example."
    return {
        "mode": "quiz",
        "message": answer,
        "answer": answer,
        "sections": [{"text": answer, "source": _source_label(matches[0]), "source_id": matches[0].get("note_id")}],
        "prompt": answer,
        "sources": sources,
        "coverage": _coverage(matches),
    }


def _practice_response(query, matches, sources):
    topic = _topic_label(query, matches)
    evidence = _explanation_sections(query, matches)[:3]
    answer = f"Practice {topic}: write a short explanation and solve a new example using the method shown in your Notes. Check your work against these ideas:\n" + "\n".join(f"- {item['text']}" for item in evidence)
    return {
        "mode": "practice",
        "message": answer,
        "answer": answer,
        "sections": evidence,
        "prompt": f"Create and solve one practice problem about {topic}.",
        "sources": sources,
        "coverage": _coverage(matches),
    }


def _review_response(matches, sources):
    topics = []
    for match in matches:
        title = str(match.get("title") or "").strip()
        if title and title not in topics:
            topics.append(title)
    answer = "Review these topics from your Notes:\n" + "\n".join(f"- {topic}" for topic in topics[:8])
    return {
        "mode": "review",
        "message": answer,
        "answer": answer,
        "sections": [{"text": answer, "source": "Your Notes", "source_id": None}],
        "topics": topics,
        "sources": sources,
        "coverage": _coverage(matches),
    }


def _source(match):
    return {
        "note_id": match.get("note_id"),
        "title": match.get("title", "Untitled note"),
        "course": match.get("course", ""),
        "chunk_index": match.get("chunk_index", 0),
        "score": match.get("score", 0),
        "source_type": match.get("source_type", "note"),
        "snippet": match.get("snippet") or str(match.get("content") or "")[:240],
    }


def _source_label(match):
    title = str(match.get("title") or "Untitled note")
    course = str(match.get("course") or "").strip()
    return f"{title} ({course})" if course else title


def _topic_label(query, matches):
    terms = " ".join(sorted(_terms(query)))
    return terms or str(matches[0].get("title") or "this topic")


def _sentences(content):
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+|\n+", content) if part.strip()]


def _terms(value):
    return {term.casefold() for term in re.findall(r"[\w]+(?:['’][\w]+)?", str(value or "")) if len(term) > 2}


def _coverage(matches):
    scores = [float(match.get("score", 0) or 0) for match in matches]
    if not scores:
        return 0.0
    return round(min(1.0, max(scores) / 12), 2)
