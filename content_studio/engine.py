import base64
import csv
import difflib
import hashlib
import html
import io
import json
import math
import re
import unicodedata
import urllib.parse
from collections import Counter


PT_STOP = {
    "a","o","as","os","um","uma","uns","umas","de","da","do","das","dos","e","é",
    "em","no","na","nos","nas","para","por","com","sem","que","se","ao","aos","à",
    "às","ou","como","mais","menos","muito","muita","muitos","muitas","já","não",
    "sim","ser","ter","seu","sua","seus","suas","isso","isto","essa","esse","essas",
    "esses","também","quando","onde","quem","qual","quais","porque","sobre","entre"
}


class ContentStudio:
    def _text(self, params, key="text"):
        return str((params or {}).get(key, ""))

    def _words(self, text):
        return re.findall(r"\b[\wÀ-ÿ'-]+\b", text, flags=re.UNICODE)

    def execute(self, operation, **params):
        text = self._text(params)

        if operation == "word_count":
            return {"ok": True, "count": len(self._words(text))}
        if operation == "char_count":
            return {"ok": True, "count": len(text)}
        if operation == "char_count_no_spaces":
            return {"ok": True, "count": len(re.sub(r"\s+", "", text))}
        if operation == "sentence_count":
            items = [x for x in re.split(r"(?<=[.!?])\s+", text.strip()) if x]
            return {"ok": True, "count": len(items), "items": items[:200]}
        if operation == "paragraph_count":
            items = [x.strip() for x in re.split(r"\n\s*\n", text) if x.strip()]
            return {"ok": True, "count": len(items), "items": items[:200]}
        if operation == "line_count":
            return {"ok": True, "count": len(text.splitlines())}
        if operation == "reading_time":
            words = len(self._words(text))
            return {"ok": True, "words": words, "minutes": round(words / 200, 2)}
        if operation == "normalize_spaces":
            return {"ok": True, "text": re.sub(r"[ \t]+", " ", text)}
        if operation == "normalize_whitespace":
            return {"ok": True, "text": re.sub(r"\s+", " ", text).strip()}
        if operation == "trim_lines":
            return {"ok": True, "text": "\n".join(x.strip() for x in text.splitlines())}
        if operation == "remove_blank_lines":
            return {"ok": True, "text": "\n".join(x for x in text.splitlines() if x.strip())}
        if operation == "dedupe_lines":
            seen = set()
            out = []
            for line in text.splitlines():
                key = line.strip()
                if key not in seen:
                    seen.add(key)
                    out.append(line)
            return {"ok": True, "text": "\n".join(out)}
        if operation == "sort_lines":
            reverse = bool(params.get("reverse", False))
            return {"ok": True, "text": "\n".join(sorted(text.splitlines(), key=str.lower, reverse=reverse))}
        if operation == "unique_words":
            words = []
            seen = set()
            for w in self._words(text):
                k = w.lower()
                if k not in seen:
                    seen.add(k)
                    words.append(w)
            return {"ok": True, "items": words, "count": len(words)}
        if operation == "top_words":
            limit = int(params.get("limit", 20))
            words = [w.lower() for w in self._words(text) if len(w) >= 3 and w.lower() not in PT_STOP]
            items = [{"word": w, "count": c} for w,c in Counter(words).most_common(limit)]
            return {"ok": True, "items": items}
        if operation == "bigrams":
            limit = int(params.get("limit", 20))
            words = [w.lower() for w in self._words(text) if len(w) >= 2]
            grams = [" ".join(words[i:i+2]) for i in range(max(0, len(words)-1))]
            return {"ok": True, "items": [{"value":x,"count":c} for x,c in Counter(grams).most_common(limit)]}
        if operation == "trigrams":
            limit = int(params.get("limit", 20))
            words = [w.lower() for w in self._words(text) if len(w) >= 2]
            grams = [" ".join(words[i:i+3]) for i in range(max(0, len(words)-2))]
            return {"ok": True, "items": [{"value":x,"count":c} for x,c in Counter(grams).most_common(limit)]}
        if operation == "slugify":
            s = unicodedata.normalize("NFKD", text)
            s = "".join(ch for ch in s if not unicodedata.combining(ch))
            s = re.sub(r"[^A-Za-z0-9]+", "-", s).strip("-").lower()
            return {"ok": True, "text": s}
        if operation == "clean_filename":
            value = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', "_", text).strip(" .")
            return {"ok": True, "text": value[:180]}
        if operation == "lowercase":
            return {"ok": True, "text": text.lower()}
        if operation == "uppercase":
            return {"ok": True, "text": text.upper()}
        if operation == "title_case":
            return {"ok": True, "text": text.title()}
        if operation == "sentence_case":
            stripped = text.strip()
            return {"ok": True, "text": (stripped[:1].upper() + stripped[1:]) if stripped else ""}
        if operation == "strip_accents":
            s = unicodedata.normalize("NFKD", text)
            return {"ok": True, "text": "".join(ch for ch in s if not unicodedata.combining(ch))}
        if operation == "strip_html":
            return {"ok": True, "text": re.sub(r"<[^>]+>", "", html.unescape(text))}
        if operation == "html_escape":
            return {"ok": True, "text": html.escape(text)}
        if operation == "html_unescape":
            return {"ok": True, "text": html.unescape(text)}
        if operation == "url_encode":
            return {"ok": True, "text": urllib.parse.quote(text)}
        if operation == "url_decode":
            return {"ok": True, "text": urllib.parse.unquote(text)}
        if operation == "base64_encode":
            return {"ok": True, "text": base64.b64encode(text.encode("utf-8")).decode("ascii")}
        if operation == "base64_decode":
            try:
                return {"ok": True, "text": base64.b64decode(text).decode("utf-8")}
            except Exception as exc:
                return {"ok": False, "error": str(exc)}
        if operation == "sha256":
            return {"ok": True, "value": hashlib.sha256(text.encode("utf-8")).hexdigest()}
        if operation == "md5":
            return {"ok": True, "value": hashlib.md5(text.encode("utf-8")).hexdigest()}
        if operation == "extract_urls":
            items = sorted(set(re.findall(r"https?://[^\s<>\"]+", text)))
            return {"ok": True, "items": items, "count": len(items)}
        if operation == "extract_emails":
            items = sorted(set(re.findall(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", text)))
            return {"ok": True, "items": items, "count": len(items)}
        if operation == "extract_phones":
            items = sorted(set(re.findall(r"(?:\+?55\s*)?(?:\(?\d{2}\)?\s*)?\d{4,5}[-.\s]?\d{4}", text)))
            return {"ok": True, "items": items, "count": len(items)}
        if operation == "extract_numbers":
            items = re.findall(r"[-+]?\d+(?:[.,]\d+)?", text)
            return {"ok": True, "items": items, "count": len(items)}
        if operation == "extract_dates_br":
            items = sorted(set(re.findall(r"\b(?:0?[1-9]|[12]\d|3[01])[/.-](?:0?[1-9]|1[0-2])[/.-](?:\d{2}|\d{4})\b", text)))
            return {"ok": True, "items": items, "count": len(items)}
        if operation == "extract_hashtags":
            items = sorted(set(re.findall(r"(?<!\w)#[\wÀ-ÿ_]+", text)))
            return {"ok": True, "items": items, "count": len(items)}
        if operation == "extract_mentions":
            items = sorted(set(re.findall(r"(?<!\w)@[\w._]+", text)))
            return {"ok": True, "items": items, "count": len(items)}
        if operation == "hashtags_from_keywords":
            limit = int(params.get("limit", 12))
            words = [w.lower() for w in self._words(text) if len(w) >= 4 and w.lower() not in PT_STOP]
            tags = []
            for w,_ in Counter(words).most_common(limit):
                clean = re.sub(r"\W+", "", unicodedata.normalize("NFKD", w).encode("ascii","ignore").decode())
                if clean:
                    tags.append("#" + clean)
            return {"ok": True, "items": tags, "text": " ".join(tags)}
        if operation == "find_replace":
            old = str(params.get("find", ""))
            new = str(params.get("replace", ""))
            return {"ok": True, "text": text.replace(old, new)}
        if operation == "prefix_lines":
            prefix = str(params.get("prefix", "• "))
            return {"ok": True, "text": "\n".join(prefix + x for x in text.splitlines())}
        if operation == "number_lines":
            return {"ok": True, "text": "\n".join(f"{i}. {x}" for i,x in enumerate(text.splitlines(), 1))}
        if operation == "truncate":
            limit = int(params.get("limit", 160))
            suffix = str(params.get("suffix", "…"))
            return {"ok": True, "text": text if len(text) <= limit else text[:max(0,limit-len(suffix))].rstrip() + suffix}
        if operation == "excerpt":
            limit = int(params.get("words", 30))
            words = self._words(text)
            return {"ok": True, "text": " ".join(words[:limit]) + ("…" if len(words) > limit else "")}
        if operation == "split_sentences":
            items = [x.strip() for x in re.split(r"(?<=[.!?])\s+", text.strip()) if x.strip()]
            return {"ok": True, "items": items, "count": len(items)}
        if operation == "split_paragraphs":
            items = [x.strip() for x in re.split(r"\n\s*\n", text) if x.strip()]
            return {"ok": True, "items": items, "count": len(items)}
        if operation == "split_carousel":
            max_chars = int(params.get("max_chars", 320))
            sentences = [x.strip() for x in re.split(r"(?<=[.!?])\s+", text.strip()) if x.strip()]
            slides, current = [], ""
            for s in sentences:
                candidate = (current + " " + s).strip()
                if current and len(candidate) > max_chars:
                    slides.append(current)
                    current = s
                else:
                    current = candidate
            if current:
                slides.append(current)
            return {"ok": True, "items": slides, "count": len(slides)}
        if operation == "instagram_limit":
            return {"ok": True, "chars": len(text), "limit": 2200, "remaining": 2200-len(text), "within": len(text) <= 2200}
        if operation == "meta_title_check":
            n = len(text.strip())
            return {"ok": True, "chars": n, "recommended_min": 30, "recommended_max": 60, "within": 30 <= n <= 60}
        if operation == "meta_description_check":
            n = len(text.strip())
            return {"ok": True, "chars": n, "recommended_min": 120, "recommended_max": 160, "within": 120 <= n <= 160}
        if operation == "headline_length":
            n = len(text.strip())
            return {"ok": True, "chars": n, "words": len(self._words(text))}
        if operation == "keyword_density":
            keyword = str(params.get("keyword", "")).strip().lower()
            words = [w.lower() for w in self._words(text)]
            hits = sum(1 for w in words if w == keyword)
            return {"ok": True, "keyword": keyword, "hits": hits, "words": len(words), "density_percent": round((hits/max(1,len(words)))*100, 2)}
        if operation == "json_validate":
            try:
                data = json.loads(text)
                return {"ok": True, "valid": True, "type": type(data).__name__}
            except Exception as exc:
                return {"ok": True, "valid": False, "error": str(exc)}
        if operation == "json_pretty":
            try:
                return {"ok": True, "text": json.dumps(json.loads(text), indent=2, ensure_ascii=False)}
            except Exception as exc:
                return {"ok": False, "error": str(exc)}
        if operation == "json_minify":
            try:
                return {"ok": True, "text": json.dumps(json.loads(text), separators=(",",":"), ensure_ascii=False)}
            except Exception as exc:
                return {"ok": False, "error": str(exc)}
        if operation == "csv_to_json":
            try:
                rows = list(csv.DictReader(io.StringIO(text)))
                return {"ok": True, "data": rows, "count": len(rows)}
            except Exception as exc:
                return {"ok": False, "error": str(exc)}
        if operation == "json_to_csv":
            try:
                data = json.loads(text)
                if not isinstance(data, list) or not data:
                    return {"ok": False, "error": "JSON deve ser uma lista não vazia de objetos."}
                fields = sorted({k for row in data if isinstance(row, dict) for k in row})
                buf = io.StringIO()
                writer = csv.DictWriter(buf, fieldnames=fields)
                writer.writeheader()
                writer.writerows(data)
                return {"ok": True, "text": buf.getvalue()}
            except Exception as exc:
                return {"ok": False, "error": str(exc)}
        if operation == "similarity":
            other = str(params.get("other", ""))
            return {"ok": True, "ratio": round(difflib.SequenceMatcher(None, text, other).ratio(), 4)}
        if operation == "diff":
            other = str(params.get("other", ""))
            lines = difflib.unified_diff(text.splitlines(), other.splitlines(), fromfile="A", tofile="B", lineterm="")
            return {"ok": True, "text": "\n".join(lines)}
        if operation == "add_utm":
            source = str(params.get("utm_source", "jarvis"))
            medium = str(params.get("utm_medium", "assistant"))
            campaign = str(params.get("utm_campaign", ""))
            parsed = urllib.parse.urlsplit(text.strip())
            q = dict(urllib.parse.parse_qsl(parsed.query, keep_blank_values=True))
            q["utm_source"] = source
            q["utm_medium"] = medium
            if campaign:
                q["utm_campaign"] = campaign
            out = urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urllib.parse.urlencode(q), parsed.fragment))
            return {"ok": True, "text": out}
        if operation == "parse_query":
            parsed = urllib.parse.urlsplit(text.strip())
            return {"ok": True, "data": dict(urllib.parse.parse_qsl(parsed.query, keep_blank_values=True))}
        if operation == "outline_markdown":
            items = []
            for line in text.splitlines():
                m = re.match(r"^(#{1,6})\s+(.+)$", line.strip())
                if m:
                    items.append({"level": len(m.group(1)), "text": m.group(2).strip()})
            return {"ok": True, "items": items}
        if operation == "extract_bullets":
            items = []
            for line in text.splitlines():
                m = re.match(r"^\s*(?:[-*•]|\d+[.)])\s+(.+)$", line)
                if m:
                    items.append(m.group(1).strip())
            return {"ok": True, "items": items, "count": len(items)}
        if operation == "extract_quotes":
            items = re.findall(r'[“"](.*?)[”"]', text, flags=re.S)
            return {"ok": True, "items": [x.strip() for x in items if x.strip()], "count": len(items)}
        if operation == "whitespace_report":
            return {
                "ok": True,
                "tabs": text.count("\t"),
                "double_spaces": len(re.findall(r" {2,}", text)),
                "blank_lines": len(re.findall(r"\n\s*\n", text)),
                "trailing_spaces": len(re.findall(r"[ \t]+\n", text)),
            }
        if operation == "social_caption_stats":
            return {
                "ok": True,
                "chars": len(text),
                "words": len(self._words(text)),
                "hashtags": len(re.findall(r"(?<!\w)#[\wÀ-ÿ_]+", text)),
                "mentions": len(re.findall(r"(?<!\w)@[\w._]+", text)),
                "urls": len(re.findall(r"https?://[^\s]+", text)),
            }

        return {"ok": False, "error": f"Operação de conteúdo desconhecida: {operation}"}
