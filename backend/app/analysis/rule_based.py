import re
from collections import Counter

from app.analysis.normalization import normalize_topic
from app.analysis.provider import AnalysisResult, ArticleAnalysisInput, EntityMentionResult, EntityTopicAnalyzer, EntityType, TextPart, TopicResult

_STOP = {"the", "a", "an", "and", "or", "of", "in", "on", "for", "to", "from", "with", "der", "die", "das", "ein", "eine", "und", "oder", "von", "im", "in", "zu", "mit", "für", "ist", "are", "was", "were", "this", "that", "said"}
_ORG = {"inc", "corp", "corporation", "company", "ltd", "llc", "gmbh", "ag", "se", "university", "ministerium", "ministry", "foundation", "bank", "group"}
_LOC = {"berlin", "london", "paris", "brussels", "washington", "tokyo", "europe", "germany", "deutschland", "france", "china", "india", "ukraine"}
_EVENT = {"summit", "conference", "election", "olympics", "festival", "gipfel", "wahl", "konferenz"}


class RuleBasedEntityTopicAnalyzer(EntityTopicAnalyzer):
    provider = "local-rules"
    version = "1.0.0"

    def analyze(self, article: ArticleAnalysisInput) -> AnalysisResult:
        entities: list[EntityMentionResult] = []
        pattern = re.compile(r"\b(?:[A-ZÀ-ÖØ-Þ][\w'’-]+)(?:\s+(?:[A-ZÀ-ÖØ-Þ][\w'’-]+|&)){0,4}\b")
        for text_part, field_text in ((TextPart.TITLE, article.title), (TextPart.BODY, article.normalized_text)):
            sentences = list(re.finditer(r"(?:^|(?<=[.!?])\s+)([^.!?]+)", field_text))
            for sentence_index, sentence in enumerate(sentences):
                for match in pattern.finditer(sentence.group(1)):
                    mention = match.group(0).strip()
                    tokens = mention.casefold().split()
                    if not tokens or (len(tokens) == 1 and tokens[0] in _STOP):
                        continue
                    if any(token.rstrip(".") in _ORG for token in tokens):
                        entity_type, confidence = EntityType.ORGANIZATION, 0.9
                    elif mention.casefold() in _LOC:
                        entity_type, confidence = EntityType.LOCATION, 0.88
                    elif any(token in _EVENT for token in tokens):
                        entity_type, confidence = EntityType.EVENT, 0.82
                    elif len(tokens) >= 2:
                        entity_type, confidence = EntityType.PERSON, 0.78
                    else:
                        entity_type, confidence = EntityType.OTHER, 0.62
                    start = sentence.start(1) + match.start()
                    entities.append(EntityMentionResult(mention, mention, entity_type, confidence, min(1.0, 0.45 + len(tokens) * 0.12), text_part, start, start + len(mention), sentence_index))

        text = f"{article.title} {article.normalized_text}".strip()
        words = [normalize_topic(word) for word in re.findall(r"\b[^\W\d_][\w-]{3,}\b", text.casefold(), re.UNICODE)]
        counts = Counter(word for word in words if word and word not in _STOP and len(word) >= 4)
        phrases = Counter()
        significant = [w for w in words if w and w not in _STOP and len(w) >= 4]
        for left, right in zip(significant, significant[1:]):
            if left != right:
                phrases[f"{left} {right}"] += 1
        candidates = [(name, count + (1 if " " in name else 0)) for name, count in counts.items() if count >= 2]
        candidates += [(name, score + 1) for name, score in phrases.items() if score >= 2]
        candidates.sort(key=lambda item: (-item[1], item[0]))
        maximum = max((score for _, score in candidates), default=1)
        topics = tuple(TopicResult(name, score / maximum, min(0.95, 0.55 + score * 0.08)) for name, score in candidates[:20])
        return AnalysisResult(tuple(entities), topics)
