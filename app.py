import streamlit as st
from pathlib import Path
import json
import re
import zipfile
from difflib import SequenceMatcher
from datetime import datetime

# Optional free translation backend. The app still works if this package/API is unavailable.
try:
    from deep_translator import GoogleTranslator
    TRANSLATION_AVAILABLE = True
except Exception:
    GoogleTranslator = None
    TRANSLATION_AVAILABLE = False

# ============================================================
# LEGEND AI — Professional UI + Chat History + ZIP Question Bank
# ============================================================

st.set_page_config(
    page_title="LEGEND AI",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

DATA = Path(__file__).parent / "data"

# ----------------------------- Languages -----------------------------

LANGUAGES = [
    "English", "Hinglish", "Hindi", "Bengali", "Punjabi", "Marathi",
    "Gujarati", "Tamil", "Telugu", "Kannada", "Malayalam", "Urdu",
    "Odia", "Assamese", "Nepali", "Sanskrit", "Kashmiri", "Sindhi",
    "Konkani", "Maithili", "Bhojpuri", "Dogri", "Manipuri", "Bodo",
    "Santali", "French", "Spanish", "German", "Italian", "Portuguese",
    "Dutch", "Russian", "Ukrainian", "Polish", "Czech", "Slovak",
    "Hungarian", "Romanian", "Bulgarian", "Serbian", "Croatian",
    "Bosnian", "Slovenian", "Greek", "Turkish", "Arabic", "Persian",
    "Hebrew", "Chinese", "Japanese", "Korean", "Thai", "Vietnamese",
    "Indonesian", "Malay", "Filipino", "Swahili", "Zulu", "Afrikaans",
    "Amharic", "Somali", "Tamil-English", "Telugu-English",
    "Kannada-English", "Bangla-English", "Punjabi-English",
    "Marathi-English", "Gujarati-English", "Nepali-English",
]

# ----------------------------- Styling -----------------------------

st.markdown("""
<style>
:root {
    --bg: #0a0b0f;
    --panel: #11131a;
    --panel2: #151822;
    --border: #252936;
    --muted: #9aa1b2;
    --text: #f4f6fb;
    --accent: #7c5cff;
}

html, body, [data-testid="stAppViewContainer"] {
    background: var(--bg) !important;
    color: var(--text) !important;
}

[data-testid="stHeader"] {
    background: rgba(10,11,15,.88) !important;
}

[data-testid="stSidebar"] {
    background: #0d0f14 !important;
    border-right: 1px solid var(--border) !important;
}

.block-container {
    max-width: 1180px;
    padding-top: 1.2rem;
    padding-bottom: 5rem;
}

.hero {
    background: linear-gradient(135deg, #151827 0%, #10121a 65%, #12101d 100%);
    border: 1px solid var(--border);
    border-radius: 26px;
    padding: 28px;
    margin-bottom: 20px;
    box-shadow: 0 18px 50px rgba(0,0,0,.22);
}

.hero h1 {
    margin: 0;
    font-size: 2.35rem;
    letter-spacing: -0.04em;
}

.hero p {
    color: var(--muted);
    margin: .45rem 0 0;
}

.badge {
    display: inline-block;
    background: #1a1d28;
    border: 1px solid #2a2e3b;
    border-radius: 999px;
    padding: 6px 11px;
    margin: 12px 6px 0 0;
    color: #c8cddd;
    font-size: .86rem;
}

.chat-card {
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 22px;
    padding: 20px;
    margin: 14px 0;
}

.user-bubble {
    background: #171a25;
    border: 1px solid #2a2e3b;
    border-radius: 18px;
    padding: 15px 17px;
    margin: 10px 0;
}

.ai-bubble {
    background: #111821;
    border: 1px solid #27313d;
    border-radius: 18px;
    padding: 17px;
    margin: 10px 0 20px;
}

.small-muted {
    color: var(--muted);
    font-size: .84rem;
}

.history-item {
    background: #11131a;
    border: 1px solid #232733;
    border-radius: 13px;
    padding: 10px 12px;
    margin: 6px 0;
}

.stButton > button {
    border-radius: 12px !important;
}

div[data-testid="stTextInput"] input {
    border-radius: 14px !important;
}

div[data-testid="stSelectbox"] > div {
    border-radius: 12px !important;
}

footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ----------------------------- Session State -----------------------------

if "chats" not in st.session_state:
    st.session_state.chats = []

if "active_chat" not in st.session_state:
    st.session_state.active_chat = None

if "language" not in st.session_state:
    st.session_state.language = "Hinglish"

# ----------------------------- Question Bank Loader -----------------------------

@st.cache_data(show_spinner=False)
def load_bank():
    rows = []
    seen_ids = set()

    def add_item(item, source_name):
        if not isinstance(item, dict):
            return

        item_id = str(item.get("id", "")).strip()
        if item_id:
            if item_id in seen_ids:
                return
            seen_ids.add(item_id)

        item["_file"] = source_name
        rows.append(item)

    if not DATA.exists():
        return rows

    # Direct JSONL files, including nested folders.
    for path in sorted(DATA.rglob("*.jsonl")):
        try:
            with path.open("r", encoding="utf-8") as f:
                for line in f:
                    try:
                        add_item(
                            json.loads(line),
                            str(path.relative_to(DATA))
                        )
                    except Exception:
                        pass
        except Exception:
            pass

    # JSONL files directly inside ZIP archives, without extraction.
    for zip_path in sorted(DATA.rglob("*.zip")):
        try:
            with zipfile.ZipFile(zip_path, "r") as z:
                for member in sorted(z.namelist()):
                    if member.endswith("/") or not member.lower().endswith(".jsonl"):
                        continue

                    try:
                        with z.open(member, "r") as f:
                            for raw_line in f:
                                try:
                                    add_item(
                                        json.loads(raw_line.decode("utf-8")),
                                        f"{zip_path.name} → {member}"
                                    )
                                except Exception:
                                    pass
                    except Exception:
                        pass
        except (zipfile.BadZipFile, OSError):
            pass

    return rows

BANK = load_bank()

# ----------------------------- Search -----------------------------

def norm(value):
    return re.sub(r"\s+", " ", str(value).lower()).strip()

def tokenize(value):
    # Unicode-friendly tokenization for English + Indian scripts.
    return set(x for x in re.findall(r"\w+", norm(value), flags=re.UNICODE) if len(x) > 1)

def search_bank(query, cls, subject, stream, limit=1):
    q = norm(query)
    q_words = tokenize(q)

    preferred = []
    for r in BANK:
        rclass = norm(r.get("class", ""))
        rstream = norm(r.get("stream", ""))
        rsubject = norm(r.get("subject", ""))

        class_ok = cls == "All" or norm(cls) in rclass
        stream_ok = stream == "All" or norm(stream) in rstream
        subject_ok = subject == "All Subjects" or norm(subject) == rsubject

        if class_ok and stream_ok and subject_ok:
            preferred.append(r)

    pool = preferred if preferred else BANK

    exact = [r for r in pool if norm(r.get("question", "")) == q]
    if exact:
        return exact[:1]

    scored = []
    for r in pool:
        rq = norm(r.get("question", ""))
        if not rq:
            continue

        r_words = tokenize(rq)
        if not q_words or not r_words:
            continue

        common = q_words & r_words
        coverage = len(common) / len(q_words)
        jaccard = len(common) / len(q_words | r_words)
        similarity = SequenceMatcher(None, q, rq).ratio()

        score = (coverage * 0.45) + (jaccard * 0.25) + (similarity * 0.30)

        if score >= 0.38:
            scored.append((score, r))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [scored[0][1]] if scored else []

# ----------------------------- Free Translation -----------------------------

LANGUAGE_CODES = {
    "English": "en", "Hindi": "hi", "Bengali": "bn", "Punjabi": "pa",
    "Marathi": "mr", "Gujarati": "gu", "Tamil": "ta", "Telugu": "te",
    "Kannada": "kn", "Malayalam": "ml", "Urdu": "ur", "Odia": "or",
    "Assamese": "as", "Nepali": "ne", "Sanskrit": "sa", "Kashmiri": "ks",
    "Sindhi": "sd", "Konkani": "gom", "Maithili": "mai", "Bhojpuri": "bho",
    "Dogri": "doi", "Manipuri": "mni", "Bodo": "brx", "Santali": "sat",
    "French": "fr", "Spanish": "es", "German": "de", "Italian": "it",
    "Portuguese": "pt", "Dutch": "nl", "Russian": "ru", "Ukrainian": "uk",
    "Polish": "pl", "Czech": "cs", "Slovak": "sk", "Hungarian": "hu",
    "Romanian": "ro", "Bulgarian": "bg", "Serbian": "sr", "Croatian": "hr",
    "Bosnian": "bs", "Slovenian": "sl", "Greek": "el", "Turkish": "tr",
    "Arabic": "ar", "Persian": "fa", "Hebrew": "iw", "Chinese": "zh-CN",
    "Japanese": "ja", "Korean": "ko", "Thai": "th", "Vietnamese": "vi",
    "Indonesian": "id", "Malay": "ms", "Filipino": "tl", "Swahili": "sw",
    "Zulu": "zu", "Afrikaans": "af", "Amharic": "am", "Somali": "so",
}

@st.cache_data(show_spinner=False, ttl=86400)
def translate_text(text, target_language):
    """
    Free translation via Google Translate through deep-translator.
    If translation is unavailable or fails, return the original text.
    Hinglish / regional-English hybrid labels are left unchanged because
    they are not standard translation targets.
    """
    if not text or not text.strip():
        return text

    if target_language in {
        "Hinglish", "Tamil-English", "Telugu-English", "Kannada-English",
        "Bangla-English", "Punjabi-English", "Marathi-English",
        "Gujarati-English", "Nepali-English"
    }:
        return text

    if not TRANSLATION_AVAILABLE:
        return text

    target_code = LANGUAGE_CODES.get(target_language)
    if not target_code:
        return text

    try:
        # Keep very long answers safe for the free backend.
        chunks = []
        current = ""
        for paragraph in text.split("\n"):
            if len(current) + len(paragraph) > 4500:
                if current:
                    chunks.append(current)
                current = paragraph
            else:
                current = (current + "\n" + paragraph).strip()

        if current:
            chunks.append(current)

        translated = []
        for chunk in chunks:
            translated.append(
                GoogleTranslator(source="auto", target=target_code).translate(chunk)
            )

        return "\n".join(translated)
    except Exception:
        return text

# ----------------------------- Chat Helpers -----------------------------

def new_chat():
    chat = {
        "id": datetime.now().strftime("%Y%m%d%H%M%S%f"),
        "title": "New study chat",
        "messages": [],
        "created": datetime.now().strftime("%d %b %Y, %H:%M"),
    }
    st.session_state.chats.insert(0, chat)
    st.session_state.active_chat = chat["id"]

def get_active_chat():
    for chat in st.session_state.chats:
        if chat["id"] == st.session_state.active_chat:
            return chat
    return None

def ensure_chat():
    if not st.session_state.chats:
        new_chat()
    elif not get_active_chat():
        st.session_state.active_chat = st.session_state.chats[0]["id"]

def clear_history():
    st.session_state.chats = []
    st.session_state.active_chat = None
    new_chat()

ensure_chat()

# ----------------------------- Sidebar -----------------------------

with st.sidebar:
    st.markdown("## 📚 LEGEND AI")
    st.caption("Your student study workspace")
    st.divider()

    if st.button("＋ New chat", use_container_width=True, type="primary"):
        new_chat()
        st.rerun()

    st.markdown("### Recent chats")

    for chat in st.session_state.chats[:12]:
        label = chat["title"][:32]
        if st.button(f"💬 {label}", key=f"chat_{chat['id']}", use_container_width=True):
            st.session_state.active_chat = chat["id"]
            st.rerun()

    st.divider()

    if st.button("🗑️ Clear chat history", use_container_width=True):
        clear_history()
        st.rerun()

    st.divider()

    st.markdown("### Study settings")
    st.session_state.language = st.selectbox(
        "Preferred language",
        LANGUAGES,
        index=LANGUAGES.index(st.session_state.language)
    )

    st.caption(f"Languages available: {len(LANGUAGES)}+")
    if TRANSLATION_AVAILABLE:
        st.caption("🆓 Free translation: ON")
    else:
        st.caption("🆓 Free translation: add deep-translator in requirements.txt")
    st.caption("Hinglish is supported as a first-class input/UI option.")

    st.divider()
    st.caption(f"📦 Connected records: {len(BANK):,}")
    st.caption("ZIP + JSONL reader enabled")

# ----------------------------- Main Header -----------------------------

st.markdown("""
<div class="hero">
    <h1>📚 LEGEND AI</h1>
    <p>Professional student study assistant • question-bank search • chat history</p>
    <span class="badge">Class 9–12</span>
    <span class="badge">65+ Languages</span>
    <span class="badge">Hinglish</span>
    <span class="badge">ZIP Question Banks</span>
</div>
""", unsafe_allow_html=True)

chat = get_active_chat()

# ----------------------------- Chat History -----------------------------

if chat and chat["messages"]:
    for msg in chat["messages"]:
        if msg["role"] == "user":
            st.markdown(
                f'<div class="user-bubble"><b>You</b><br>{msg["content"]}</div>',
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                f'<div class="ai-bubble"><b>LEGEND AI</b><br>{msg["content"]}</div>',
                unsafe_allow_html=True
            )
else:
    st.markdown("""
    <div class="chat-card">
        <h3>👋 Welcome to LEGEND AI</h3>
        <p class="small-muted">
        Choose your class, stream and subject, then ask a question.
        Your chat history stays available during this app session.
        </p>
    </div>
    """, unsafe_allow_html=True)

# ----------------------------- Controls -----------------------------

st.markdown("### Ask your question")

c1, c2, c3 = st.columns(3)

with c1:
    cls = st.selectbox("Class", ["All", "9", "10", "11", "12"])

with c2:
    stream = st.selectbox(
        "Stream",
        ["All", "Science", "Commerce", "Arts"]
    )

with c3:
    subject = st.selectbox(
        "Subject",
        [
            "All Subjects", "Science", "Mathematics", "Maths", "English", "Hindi",
            "Physics", "Chemistry", "Biology", "Accountancy", "Business Studies",
            "Economics", "History", "Political Science", "Geography", "Reasoning",
            "Quantitative Aptitude", "Revision", "Exam Practice",
            "Concept Builder", "English Skills", "Social Science"
        ]
    )

placeholder_map = {
    "Hinglish": "Apna question yahan likho…",
    "Hindi": "अपना प्रश्न यहाँ लिखें…",
    "English": "Ask your question here…",
}

placeholder = placeholder_map.get(
    st.session_state.language,
    "Ask your question here…"
)

query = st.text_area(
    "Question",
    placeholder=placeholder,
    height=95,
    label_visibility="collapsed"
)

ask = st.button("🔎 Ask LEGEND AI", type="primary", use_container_width=True)

if ask:
    if not query.strip():
        st.warning("Pehle question likho.")
    else:
        results = search_bank(query, cls, subject, stream)

        # Store only one result, preserving the original app's behavior.
        if results:
            r = results[0]
            answer = str(r.get("answer", "")).strip()

            # Translate the stored answer for the selected language.
            # Hinglish is intentionally left as-is because it is a hybrid
            # style rather than a standard translation target.
            translated_answer = translate_text(answer, st.session_state.language)

            chat["messages"].append({
                "role": "user",
                "content": query.strip(),
            })

            answer_text = (
                f"{translated_answer}<br><br>"
                f"<span class='small-muted'>"
                f"Class: {r.get('class','')} • "
                f"Stream: {r.get('stream','')} • "
                f"Subject: {r.get('subject','')} • "
                f"Topic: {r.get('topic','')}"
                f"</span>"
            )

            chat["messages"].append({
                "role": "assistant",
                "content": answer_text,
            })

            if chat["title"] == "New study chat":
                chat["title"] = query.strip()[:38]

            st.rerun()

        else:
            chat["messages"].append({
                "role": "user",
                "content": query.strip(),
            })
            chat["messages"].append({
                "role": "assistant",
                "content": (
                    "Is question ka matching result abhi question bank mein nahi mila. "
                    "Question ko thoda different wording mein try karo."
                ),
            })

            if chat["title"] == "New study chat":
                chat["title"] = query.strip()[:38]

            st.rerun()

# ----------------------------- Footer -----------------------------

st.markdown(
    f'<div class="small-muted" style="text-align:center;margin-top:35px;">'
    f'LEGEND AI • {len(BANK):,} connected starter records • '
    f'{len(LANGUAGES)}+ language options • free translation • ZIP reader active'
    f'</div>',
    unsafe_allow_html=True
)
