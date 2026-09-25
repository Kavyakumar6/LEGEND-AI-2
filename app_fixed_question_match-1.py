import streamlit as st
from pathlib import Path
import json, re

st.set_page_config(page_title="LEGEND AI", page_icon="📚", layout="wide")

st.markdown("""
<style>
html, body, [data-testid="stAppViewContainer"] {
    background:#0b0b0b !important;
    color:#f5f5f5 !important;
}
[data-testid="stHeader"] { background:#0b0b0b !important; }
[data-testid="stSidebar"] {
    background:#050505 !important;
    border-right:1px solid #262626 !important;
}
.block-container { max-width:1050px; padding-top:1.5rem; }
.hero {
    background:#111;
    border:1px solid #292929;
    border-radius:24px;
    padding:25px;
    margin-bottom:18px;
}
.hero h1 { margin:0; font-size:2.3rem; }
.hero p { color:#aaa; margin:.35rem 0 0; }
.badge {
    display:inline-block;
    background:#1b1b1b;
    border:1px solid #2a2a2a;
    border-radius:999px;
    padding:5px 10px;
    margin:9px 5px 0 0;
    color:#bbb;
}
.answer {
    background:#151515;
    border:1px solid #303030;
    border-radius:20px;
    padding:20px;
    margin-top:16px;
}
</style>
""", unsafe_allow_html=True)

DATA = Path(__file__).parent / "data"

@st.cache_data
def load_bank():
    rows = []
    for path in sorted(DATA.glob("*.jsonl")):
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                try:
                    item = json.loads(line)
                    item["_file"] = path.name
                    rows.append(item)
                except Exception:
                    pass
    return rows

BANK = load_bank()

def norm(s):
    return re.sub(r"\s+", " ", s.lower()).strip()

def search_bank(query, cls, subject, stream, limit=1):
    q = norm(query)
    q_words = set(x for x in re.findall(r"\w+", q) if len(x) > 2)

    # Prefer the student's selected class/stream/subject.
    preferred = []
    for r in BANK:
        rclass = str(r.get("class", "")).lower()
        rstream = str(r.get("stream", "")).lower()
        rsubject = str(r.get("subject", "")).lower()

        class_ok = cls == "All" or cls.lower() in rclass
        stream_ok = stream == "All" or stream.lower() in rstream
        subject_ok = subject == "All Subjects" or subject.lower() == rsubject

        if class_ok and stream_ok and subject_ok:
            preferred.append(r)

    pool = preferred or BANK

    # IMPORTANT: search ONLY the question text.
    # Do not score words found in answers/topics, because that can
    # return an unrelated question's answer.
    exact = [r for r in pool if norm(str(r.get("question", ""))) == q]
    if exact:
        return exact[:1]

    scored = []
    for r in pool:
        rq = norm(str(r.get("question", "")))
        if not rq:
            continue

        r_words = set(x for x in re.findall(r"\w+", rq) if len(x) > 2)
        if not q_words or not r_words:
            continue

        common = q_words & r_words
        # Require meaningful overlap with the QUESTION itself.
        coverage = len(common) / len(q_words)
        jaccard = len(common) / len(q_words | r_words)

        # Stronger match for longer/near-identical wording.
        from difflib import SequenceMatcher
        similarity = SequenceMatcher(None, q, rq).ratio()

        score = (coverage * 0.45) + (jaccard * 0.25) + (similarity * 0.30)

        if score >= 0.38:
            scored.append((score, r))

    scored.sort(key=lambda x: x[0], reverse=True)

    # Return only one genuinely relevant result.
    # If nothing is sufficiently similar, return no result instead of
    # showing a random/unrelated answer.
    return [scored[0][1]] if scored else []

with st.sidebar:
    st.markdown("# 📚 LEGEND AI")
    st.caption("Student Study Assistant")
    st.divider()

    if st.button("✏️ New Chat", use_container_width=True):
        st.session_state.pop("results", None)
        st.rerun()

    st.markdown("### Classes")
    st.caption("9 • 10 • 11 • 12")

    st.markdown("### Subjects")
    st.caption("Science • Maths • English • Hindi")
    st.caption("Physics • Chemistry • Biology")
    st.caption("Commerce • Arts / Humanities")

st.markdown("""
<div class="hero">
<h1>📚 LEGEND AI</h1>
<p>Student-friendly question-bank search</p>
<span class="badge">Class 9–12</span>
<span class="badge">Science</span>
<span class="badge">Commerce</span>
<span class="badge">Arts</span>
</div>
""", unsafe_allow_html=True)

st.markdown("## 🔎 Ask LEGEND AI")

c1, c2, c3 = st.columns(3)
with c1:
    cls = st.selectbox("Class", ["All","9","10","11","12"])
with c2:
    stream = st.selectbox("Stream", ["All","Science","Commerce","Arts"])
with c3:
    subject = st.selectbox(
        "Subject",
        ["All Subjects","Science","Mathematics","Maths","English","Hindi",
         "Physics","Chemistry","Biology","Accountancy","Business Studies",
         "Economics","History","Political Science","Geography","Reasoning",
         "Quantitative Aptitude","Revision","Exam Practice","Concept Builder",
         "English Skills","Social Science"]
    )

query = st.text_input(
    "Question",
    placeholder="Apna question yahan likho…",
    label_visibility="collapsed"
)

if st.button("🔍 Search / Ask", type="primary", use_container_width=True):
    if not query.strip():
        st.warning("Pehle question likho.")
    else:
        st.session_state.results = search_bank(query, cls, subject, stream)

if "results" in st.session_state:
    results = st.session_state.results

    if results:
        st.success(f"{len(results)} matching result(s) found")

        for i, r in enumerate(results, 1):
            with st.container(border=True):
                st.markdown(f"**{i}. {r.get('question','')}**")
                st.caption(
                    f"Class: {r.get('class','')} • "
                    f"Stream: {r.get('stream','')} • "
                    f"Subject: {r.get('subject','')} • "
                    f"Topic: {r.get('topic','')}"
                )
                st.markdown(f"**Answer:** {r.get('answer','')}")
    else:
        st.info(
            "Is question ka matching result abhi question bank mein nahi mila. "
            "Question ko thoda different wording mein try karo."
        )
else:
    st.markdown("""
    <div class="answer">
    <b>👋 Welcome!</b><br><br>
    Class, stream aur subject choose karo aur apna question search karo.
    <br><br>
    Students ko database chunks dikhte nahi hain — app background mein
    connected question-bank ko search karta hai.
    </div>
    """, unsafe_allow_html=True)

st.caption(f"Connected starter records: {len(BANK):,}")
