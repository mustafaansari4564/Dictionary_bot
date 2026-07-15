import re
import logging
from text_utils import normalize, looks_like_root

logger = logging.getLogger(__name__)

DIACRITICS = re.compile(
    r'[\u0610-\u061A\u064B-\u065F\u0670'
    r'\u06D6-\u06DC\u06DF-\u06E4\u06E7\u06E8\u06EA-\u06ED]'
)

def strip_diacritics(text):
    return DIACRITICS.sub('', text)

def normalize_root(text):
    """Extended normalization for root extraction — handles hamza variants."""
    text = strip_diacritics(text)
    text = re.sub(r'[آأإٱأ]', 'ا', text)   # alef variants → ا
    text = re.sub(r'[يى]',     'ي', text)   # ya variants → ي
    text = re.sub(r'ة',        'ه', text)   # ta marbuta → ha
    text = re.sub(r'[ؤئء]',   'ا', text)   # hamza variants → ا
    return text.strip()

ARABIC_ONLY = re.compile(r'^[\u0621-\u064A]+$')

def is_arabic(text):
    return bool(ARABIC_ONLY.match(text)) and len(text) >= 2

def is_valid_root(w):
    return bool(re.match(r'^[\u0621-\u064A]{2,5}$', w))

def is_three_letter_root(w):
    """Only 3-letter bare words are unambiguously roots."""
    return bool(re.match(r'^[\u0621-\u064A]{3}$', w))

# ── Special cases ─────────────────────────────────────────────────────────────
SPECIAL = {
    'الله':  'اله',
    'اللهم': 'اله',
    'إله':   'اله',
    'آله':   'اله',
}

# ── Prefixes ──────────────────────────────────────────────────────────────────
PREFIXES = [
    'مست', 'است', 'انت', 'افت', 'اقت',
    'مت', 'ال',
]

VERB_PREFIXES = ['ي', 'ت', 'ن', 'أ', 'ا']

# ── Suffixes ──────────────────────────────────────────────────────────────────
SUFFIXES = [
    'ونهم', 'ونها', 'تهم', 'تها',
    'ونك', 'وني', 'تكم', 'تني',
    'ون', 'ين', 'ان', 'ات', 'ية',
    'ها', 'هم', 'هن', 'كم', 'كن', 'نا',
    'ني', 'ة', 'ه', 'ن',
]

def apply_prefixes(word):
    w = word
    if w.startswith('ال') and len(w) - 2 >= 2:
        w = w[2:]
    for p in PREFIXES:
        if p == 'ال':
            continue
        if w.startswith(p) and len(w) - len(p) >= 2:
            w = w[len(p):]
            break
    for vp in VERB_PREFIXES:
        if w.startswith(vp) and 3 <= len(w) - 1 <= 5:
            w = w[1:]
            break
    # م noun patterns (مفعل، مفعول، مفاعل)
    if w.startswith('م') and len(w) - 1 >= 3:
        w = w[1:]
    return w

def apply_suffixes(word):
    for s in SUFFIXES:
        if word.endswith(s) and len(word) - len(s) >= 3:
            return word[:-len(s)]
    return word

def remove_interior_weak(word):
    if len(word) <= 3:
        return word
    result = word[0]
    for ch in word[1:]:
        if ch not in 'اوي':
            result += ch
    return result if len(result) >= 2 else word


def simple_extract(word: str) -> str | None:
    word = strip_diacritics(word).strip()
    if not word or not is_arabic(word):
        return None

    # Special cases
    if word in SPECIAL:
        return SPECIAL[word]
    norm_check = normalize_root(word)
    if norm_check in SPECIAL.values():
        return norm_check

    # Unambiguous 3-letter root — return directly
    if is_three_letter_root(normalize_root(word)):
        return normalize_root(word)

    # Pipeline: prefix → suffix → weak removal
    w = apply_prefixes(word)
    w = apply_suffixes(w)
    w_weak = remove_interior_weak(w)
    w_norm = normalize_root(w_weak)

    if is_valid_root(w_norm):
        return w_norm

    # Try without weak removal
    w_norm2 = normalize_root(w)
    if is_valid_root(w_norm2):
        return w_norm2

    # Last resort: strip ال + weak removal
    if word.startswith('ال') and len(word) > 4:
        bare = normalize_root(remove_interior_weak(word[2:]))
        if is_valid_root(bare):
            return bare

    return None


# ── Optional libraries ────────────────────────────────────────────────────────
_analyzer  = None
_camel_ok  = False
_init_done = False

def _load_camel():
    global _analyzer, _camel_ok, _init_done
    if _init_done:
        return
    _init_done = True
    try:
        from camel_tools.morphology.database import MorphologyDB
        from camel_tools.morphology.analyzer import Analyzer
        db = MorphologyDB.builtin_db('calima-msa-r13')
        _analyzer = Analyzer(db)
        _camel_ok = True
        logger.info("camel_tools loaded")
    except Exception:
        logger.info("camel_tools not available — using built-in extractor")

def _try_pyarabic(word: str) -> str | None:
    try:
        from pyarabic import araby
        root = araby.light_stemmer(word)
        if root:
            r = normalize(root)
            if 2 <= len(r) <= 5:
                return r
    except Exception:
        pass
    return None


def extract_root(word: str) -> str | None:
    word = word.strip()
    if not word:
        return None

    bare = strip_diacritics(word)
    if is_three_letter_root(normalize_root(bare)):
        return normalize_root(bare)

    _load_camel()
    if _camel_ok and _analyzer:
        try:
            analyses = _analyzer.analyze(word)
            roots = []
            for a in analyses:
                root = a.get('root', '')
                if root and root not in ('NOAN', ''):
                    clean = normalize(root.replace('.', ''))
                    if 2 <= len(clean) <= 5:
                        roots.append(clean)
            if roots:
                return max(set(roots), key=roots.count)
        except Exception as e:
            logger.error(f"camel_tools error: {e}")

    result = _try_pyarabic(word)
    if result:
        return result

    return simple_extract(word)