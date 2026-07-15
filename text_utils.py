import re

DIACRITICS = re.compile(
    r'[\u0610-\u061A\u064B-\u065F\u0670'
    r'\u06D6-\u06DC\u06DF-\u06E4\u06E7\u06E8\u06EA-\u06ED]'
)

def normalize(text: str) -> str:
    text = DIACRITICS.sub('', text)
    text = re.sub(r'[آأإٱ]', 'ا', text)
    text = re.sub(r'[يى]', 'ي', text)
    text = re.sub(r'ة', 'ه', text)
    return text.strip()

def looks_like_root(word: str) -> bool:
    """3-4 bare Arabic letters with no spaces = likely already a root."""
    clean = normalize(word)
    return bool(re.match(r'^[\u0621-\u064A]{3,4}$', clean))
