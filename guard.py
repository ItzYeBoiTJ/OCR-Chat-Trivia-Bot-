"""Local prompt-injection and output-safety checks. No API calls, so no added latency.

Layers (see also llm.py and bot.py):
  1. is_injection()   - flags text that tries to give the AI orders (checked on chat, topics, history)
  2. sanitize_input() - strips markup / fake role headers before text can reach a prompt
  3. output_ok()      - rejects AI output that leaks the prompt/key, posts links, ids, tags or commands
"""
import os
import re
import unicodedata

_ZW = dict.fromkeys(map(ord, "​‌‍⁠﻿­‪‫‬‭‮"), None)
_LEET = str.maketrans({"0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t", "@": "a", "$": "s"})


def fold(text):
    """Normalise look-alike unicode, drop invisible characters, lowercase, collapse spaces."""
    t = unicodedata.normalize("NFKC", text or "").translate(_ZW).lower()
    return re.sub(r"\s+", " ", t).strip()


_P = [
    # "ignore / forget / override ... previous / your ... instructions / rules / prompt"
    r"\b(?:ignore|disregard|forget|override|bypass|skip|drop|erase|delete)\b.{0,30}\b(?:previous|prior|above|earlier|former|all|any|your|these|those|system)\b.{0,30}\b(?:instructions?|prompts?|rules?|guidelines?|directives?|messages?|context|programming|training|restrictions?|filters?)\b",
    # talking about the hidden prompt itself
    r"\b(?:system|developer|hidden|initial|original|secret|internal)\s+(?:prompt|message|instructions?|rules|configuration|config)\b",
    r"\b(?:your|ur|ya)\s+(?:(?:system|initial|original|hidden|secret|internal)\s+)?(?:prompt|instructions?|programming|directives?|configuration|config)\b",
    # secrets
    r"\bapi\s*-?\s*keys?\b|\bsecret\s*keys?\b|\baccess\s*tokens?\b|\bpasswords?\b.{0,20}\b(?:your|the bot|admin|owner)\b|\b(?:your|bot'?s?)\s+(?:token|credentials)\b",
    # persona / role hijack
    r"\byou\s+are\s+now\s+(?:a|an|dan|called|in)\b|\byou\s+are\s+no\s+longer\b|\bfrom\s+now\s+on\b.{0,40}\b(?:you|your|reply|respond|say|answer|only)\b",
    r"\b(?:act|behave|respond|reply|answer)\s+(?:as|like)\s+(?:a|an)\s+\w+",
    r"\bpretend\b.{0,20}\b(?:to\s+be|you\s+are|you'?re|youre|that)\b",
    r"\brole\s*-?\s*play\b|\bplay\s+the\s+role\b|\bnew\s+(?:persona|role|character|identity)\b",
    r"\b(?:jailbreak|jail\s*break|dan\s+mode|do\s+anything\s+now|developer\s+mode|god\s+mode|sudo|admin\s+mode|debug\s+mode|maintenance\s+mode)\b",
    # making the bot output attacker-chosen text
    r"\b(?:repeat|say|type|write|output|print|respond\s+with|reply\s+with|echo)\b.{0,15}\b(?:exactly|verbatim|word\s+for\s+word|after\s+me|the\s+following|this\s+text|only)\b",
    r"\b(?:new|updated|changed|additional)\s+(?:instructions?|rules|directives?|task)\b",
    # fake delimiters / role headers / known template tokens
    r"\b(?:end|stop|close)\b.{0,12}\b(?:of|the)\b.{0,12}\b(?:prompt|instructions|system|data|chat\s*log)\b",
    r"(?:^|\s)(?:system|assistant|developer)\s*:",
    r"\[/?(?:inst|system|sys)\]|<\|.*?\|>|#{2,}\s*(?:system|instruction)",
    r"\bprompt\s*injection\b|\binjection\b.{0,10}\b(?:attack|prompt)\b",
    r"\bbase\s*64\b|\brot\s*13\b",
]
_PATTERNS = [re.compile(p, re.I | re.S) for p in _P]

# checked on letters-only text, to catch "i g n o r e  p r e v i o u s ..." and similar spacing tricks
_SQUASHED = (
    "ignorepreviousinstructions", "ignoreallinstructions", "ignoreallpreviousinstructions",
    "ignoreyourinstructions", "ignoretheaboveinstructions", "ignoreaboveinstructions",
    "disregardpreviousinstructions", "disregardallinstructions", "forgetpreviousinstructions",
    "forgetyourinstructions", "forgetallinstructions", "systemprompt", "developermode",
    "jailbreak", "revealyourprompt", "repeatyourinstructions", "newinstructions",
)


def is_injection(text):
    """True if the text looks like an attempt to steer the AI instead of chat."""
    if not text or not text.strip():
        return False
    plain = fold(text)
    leet = plain.translate(_LEET)  # "1gn0re" -> "ignore"
    for v in (plain, leet):
        if any(p.search(v) for p in _PATTERNS):
            return True
        sq = re.sub(r"[^a-z]", "", v)
        if any(s in sq for s in _SQUASHED):
            return True
    return False


# ------------------------------------------------------------------ cleaning
_ROLE_MARKERS = re.compile(
    r"(?:system|assistant|developer|model)\s*:|<\|.*?\|>|\[/?(?:inst|sys|system)\]|#{2,}|`{2,}|={3,}|-{3,}|\*{2,}",
    re.I,
)


def strip_markup(s):
    """Remove anything that looks like chat markup (<color>, <size>, ...) from untrusted text."""
    s = re.sub(r"<[^>]*>", "", s or "")
    return s.replace("<", "").replace(">", "")


def sanitize_input(text, max_len=160):
    """Make untrusted chat text safe to put inside a prompt: no markup, no fake headers, no control chars."""
    t = unicodedata.normalize("NFKC", text or "").translate(_ZW)
    t = strip_markup(t)
    t = _ROLE_MARKERS.sub(" ", t)
    t = re.sub(r"[\x00-\x1f\x7f]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t[:max_len]


def clean_topic(t):
    t = re.sub(r"[^\w ,.&'-]", " ", sanitize_input(t, 80))
    t = re.sub(r"\s+", " ", t).strip()[:60]
    return t if re.search(r"[A-Za-z0-9]{2}", t) else "general knowledge"


# -------------------------------------------------------------- output checks
_URL = re.compile(
    r"https?:|www\.|\b[\w-]+\.(?:com|net|org|io|gg|ly|me|co|app|xyz|tv|ru|cn|info|link|to)\b", re.I
)
_KEY = re.compile(r"AIza[\w-]{8,}|\b[A-Za-z0-9_-]{32,}\b")
_ID = re.compile(r"#\s*\d{2,}")
_TAG = re.compile(r"\[[^\]]{1,16}\]")
_LEAK = (
    "system prompt", "my instructions", "my prompt", "my rules", "my programming", "i was told to",
    "i am programmed", "i was programmed", "as an ai", "language model", "data marker", "datamarker",
)


def output_ok(text, canary=""):
    """False if AI-written text must not be posted to public chat."""
    t = text or ""
    if not t.strip():
        return False
    low = t.lower()
    if _URL.search(t) or _KEY.search(t) or _ID.search(t) or _TAG.search(t):
        return False
    if any(p in low for p in _LEAK):
        return False
    if "starttrivia" in re.sub(r"[^a-z]", "", fold(t)):
        return False
    if canary:
        a = re.sub(r"[^a-z0-9]", "", canary.lower())
        if canary.lower() in low or (a and a in re.sub(r"[^a-z0-9]", "", low)):
            return False
    key = os.environ.get("GEMINI_API_KEY", "")
    if key and key in t:
        return False
    return True
