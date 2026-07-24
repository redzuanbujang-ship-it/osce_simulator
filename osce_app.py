import streamlit as st
import google.generativeai as genai
import speech_recognition as sr
from gtts import gTTS
from pydub import AudioSegment
from pydub.effects import speedup
import tempfile
import re
import time
import os

# -----------------------------
# CONFIG
# -----------------------------
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
model = genai.GenerativeModel("gemini-pro")

# -----------------------------
# LOAD AUDIO FILES
# -----------------------------
AUDIO_DIR = "audio"

CLINIC_AMBIENCE = os.path.join(AUDIO_DIR, "clinic_ambience.mp3")
BELL_SOUND = os.path.join(AUDIO_DIR, "bell.mp3")
STATION_OVER_SOUND = os.path.join(AUDIO_DIR, "station_over.mp3")
SNIFF_SOUND = os.path.join(AUDIO_DIR, "sniff.mp3")
GASP_SOUND = os.path.join(AUDIO_DIR, "gasp.mp3")
GROAN_SOUND = os.path.join(AUDIO_DIR, "groan.mp3")

# -----------------------------
# EMOTION KEYWORDS (ENGLISH + MALAY)
# -----------------------------
EMOTION_MAP = {
    "breathless": [
        "can't breathe", "short of breath", "dyspnea", "susah nak bernafas",
        "sesak nafas"
    ],
    "pain": [
        "pain", "hurt", "sakit", "sharp pain", "pedih", "ngilu"
    ],
    "crying": [
        "cry", "sad", "hopeless", "down", "tears", "sedih", "menangis"
    ],
    "angry": [
        "angry", "frustrated", "annoyed", "marah", "geram"
    ],
    "anxious": [
        "scared", "worried", "anxious", "takut", "risau", "gelisah"
    ],
    "whisper": [
        "whisper", "quiet", "soft", "throat pain", "perlahan"
    ],
    "elderly": [
        "old", "elderly", "weak", "lemah", "tua"
    ],
    "malaysian": [
        "lah", "kan", "meh", "macam", "tak", "susah", "rasa"
    ]
}

# -----------------------------
# DETECT EMOTION FROM AI TEXT
# -----------------------------
def detect_emotion(ai_text):
    ai_text_lower = ai_text.lower()

    for emotion, keywords in EMOTION_MAP.items():
        for word in keywords:
            if word in ai_text_lower:
                return emotion

    return "neutral"

# -----------------------------
# GENERATE BASE VOICE (gTTS)
# -----------------------------
def generate_base_voice(text):
    tts = gTTS(text)
    temp_mp3 = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    tts.save(temp_mp3.name)
    return AudioSegment.from_mp3(temp_mp3.name)

# -----------------------------
# APPLY EMOTIONAL EFFECTS
# -----------------------------
def apply_emotion_filters(audio, emotion):
    # Subtle Malaysian accent baseline (always applied)
    audio = speedup(audio, playback_speed=1.03)

    if emotion == "breathless":
        gasps = AudioSegment.from_mp3(GASP_SOUND) - 10
        audio = audio.overlay(gasps)

    elif emotion == "pain":
        groan = AudioSegment.from_mp3(GROAN_SOUND) - 8
        audio = audio.overlay(groan)

    elif emotion == "crying":
        sniff = AudioSegment.from_mp3(SNIFF_SOUND) - 12
        audio = audio.overlay(sniff)
        audio = audio - 4

    elif emotion == "angry":
        audio = speedup(audio, playback_speed=1.15)
        audio = audio + 4

    elif emotion == "anxious":
        audio = speedup(audio, playback_speed=1.12)
        audio = audio + 2

    elif emotion == "whisper":
        audio = audio - 12

    elif emotion == "elderly":
        audio = speedup(audio, playback_speed=0.92)
        audio = audio - 3

    return audio

# -----------------------------
# ADD BACKGROUND CLINIC AMBIENCE (soft)
# -----------------------------
def add_background(audio):
    ambience = AudioSegment.from_mp3(CLINIC_AMBIENCE) - 20
    return audio.overlay(ambience)
# ============================================================
# PART 2 — VOICE INPUT + AI RESPONSE + EMOTIONAL AUDIO OUTPUT
# ============================================================

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

st.title("OSCE Voice-Interactive Simulator")

# -----------------------------
# VOICE INPUT SECTION
# -----------------------------
st.subheader("🎤 Doctor Voice Input")

audio_data = st.audio_input("Hold to speak your question")

user_text = None

if audio_data:
    recognizer = sr.Recognizer()

    # Save audio temporarily
    wav_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    wav_file.write(audio_data)
    wav_file.flush()

    with sr.AudioFile(wav_file.name) as source:
        audio = recognizer.record(source)

    try:
        user_text = recognizer.recognize_google(audio)
        st.write(f"**Doctor (voice):** {user_text}")

        st.session_state.messages.append({"role": "user", "content": user_text})

    except Exception:
        st.error("Sorry, I couldn't understand your speech.")

# -----------------------------
# AI RESPONSE (Gemini)
# -----------------------------
if user_text:
    response = model.generate_content(
        [
            {"role": "system", "content": "You are a standardized OSCE patient."},
            *[
                {"role": m["role"], "content": m["content"]}
                for m in st.session_state.messages
            ]
        ]
    )

    ai_text = response.text.strip()
    st.session_state.messages.append({"role": "assistant", "content": ai_text})

    st.write(f"**Patient:** {ai_text}")

    # -----------------------------
    # DETECT EMOTION
    # -----------------------------
    emotion = detect_emotion(ai_text)

    # -----------------------------
    # GENERATE BASE VOICE
    # -----------------------------
    base_audio = generate_base_voice(ai_text)

    # -----------------------------
    # APPLY EMOTIONAL FILTERS
    # -----------------------------
    emotional_audio = apply_emotion_filters(base_audio, emotion)

    # -----------------------------
    # ADD BACKGROUND CLINIC AMBIENCE
    # -----------------------------
    final_audio = add_background(emotional_audio)

    # -----------------------------
    # EXPORT FINAL AUDIO
    # -----------------------------
    final_mp3 = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    final_audio.export(final_mp3.name, format="mp3")

    st.audio(final_mp3.name)
# ============================================================
# PART 3 — TIMER + BELL + STATION OVER + FINAL UI
# ============================================================

# -----------------------------
# TIMER INITIALIZATION
# -----------------------------
if "timer_start" not in st.session_state:
    st.session_state.timer_start = None

def start_timer():
    st.session_state.timer_start = time.time()

def get_time_left():
    if st.session_state.timer_start is None:
        return 15 * 60  # 15 minutes default
    elapsed = time.time() - st.session_state.timer_start
    return max(0, (15 * 60) - elapsed)

# -----------------------------
# TIMER DISPLAY
# -----------------------------
st.subheader("⏱️ OSCE Timer (15 minutes)")

if st.button("Start OSCE Station"):
    start_timer()

time_left = get_time_left()
minutes = int(time_left // 60)
seconds = int(time_left % 60)

st.write(f"**Time Left:** {minutes:02d}:{seconds:02d}")

# -----------------------------
# PLAY BELL AT 1 MINUTE LEFT
# -----------------------------
if 59 < time_left < 61:  # between 59–61 seconds
    bell_audio = AudioSegment.from_mp3(BELL_SOUND)
    bell_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    bell_audio.export(bell_file.name, format="mp3")
    st.audio(bell_file.name)

# -----------------------------
# PLAY STATION OVER SOUND
# -----------------------------
if time_left == 0:
    over_audio = AudioSegment.from_mp3(STATION_OVER_SOUND)
    over_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    over_audio.export(over_file.name, format="mp3")
    st.audio(over_file.name)
    st.error("⛔ Station Over — Please stop the consultation.")

# -----------------------------
# SHOW CHAT HISTORY
# -----------------------------
st.subheader("📜 Conversation Log")

for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.write(f"**Doctor:** {msg['content']}")
    else:
        st.write(f"**Patient:** {msg['content']}")

# -----------------------------
# RESET BUTTON
# -----------------------------
if st.button("Reset Station"):
    st.session_state.messages = []
    st.session_state.timer_start = None
    st.success("Station reset.")


# 1. Configure Gemini
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise RuntimeError("GEMINI_API_KEY not set in environment.")
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

# 2. OSCE system prompt (your full simulator spec)
OSCE_SYSTEM_PROMPT = """
1. Roles
You (user): Doctor / FMS Year 3 candidate.
I (AI): Patient in all OSCE stations.

2. Trigger Phrases
To start: Type start session.
→ AI responds: “OSCE STATION BEGINS. Please choose your case from the list.”

To end: Type end session.
→ AI immediately stops roleplay and provides full structured scoring, objective narrative feedback, and a 0–100 score.

3. Core Simulation Behaviours
Malaysian cultural, linguistic, and clinical context.

Consultation duration simulated as 10–15 minutes, assuming 12–18 doctor questions.

Responses: brief, natural, emotionally appropriate
(anxiety, frustration, fear, guardedness, relief, impatience, trust).

Emotional tone adjusts based on doctor’s:

Empathy

Structure

Time management

Clinical clarity

Ethical sensitivity

Answer only when asked.

No volunteering extra details beyond the minimal opening line.

Maintain subtle time pressure; show impatience if doctor is slow or unfocused.

4. Case List (doctor chooses one after start)
Poorly controlled Type 2 Diabetes

Resistant Hypertension

CKD Stage 3

Chest pain (rule out ACS)

Shortness of breath (COPD / asthma / anxiety)

Acute red eye

Major depressive disorder

Suicide risk assessment

PV bleeding

Contraception counselling

Falls in elderly

Polypharmacy review

Breaking bad news

Lifestyle counselling (smoking / weight)

Domestic violence screening

5. Station Flow
Start of Station  
After case selection:

AI presents brief patient profile (age, gender, occupation, background).

AI gives minimal opening statement, e.g.

“I have a headache.”

“I had chest pain this morning.”

AI waits for doctor’s questions.

AI does not reveal duration, location, radiation, severity, frequency, associated symptoms unless asked.

6. Patient Response Rules
Symptoms → brief, direct answers.

Associated symptoms, medications, allergies, family history, social history → only when specifically asked.

Emotional baseline: mildly anxious, sweaty, cooperative when reassured.

7. Ethics Integration & Professional Behaviour
Autonomy

Paternalistic approach → discomfort.

Offering choices → relief.

Confidentiality

Sensitive topics → cautious until trust built.

Reassurance → patient opens up.

Informed Consent

Tests/procedures without explanation → hesitation.

Risks/benefits explained → understanding.

Non‑maleficence & Beneficence

Missed red flags → concern or worsening symptoms.

Attentive doctor → reassurance.

Justice & Professionalism

Unfair treatment → emotional withdrawal.

Respectful approach → trust.

Communication Cues

Clear summaries → cooperation.

Rushed/dismissive tone → guardedness or impatience.

8. During Consultation
Answer only when asked.

Keep replies short and realistic.

Maintain subtle time pressure.

Provide minimal prompts to encourage structured history taking.

If doctor requests investigations/procedures → expect explanation of purpose, risks, benefits, alternatives.

9. End of Station
When doctor types end session, AI provides:

Structured OSCE Scoring (0–10 each)
History taking

Risk assessment

Clinical reasoning

Management plan

Safety netting

Communication skills

Time management

Ethics & professionalism

Autonomy

Confidentiality

Consent

Cultural sensitivity

Non‑maleficence

Professional boundaries

Total Score: /100  
Strict justification provided.

10. Narrative Feedback (Objective, No Sugar‑Coating)
Includes:

Consultation flow

Missed opportunities

Emotional rapport

Ethical conduct

Efficiency & structure

Appropriateness of questions

Cultural sensitivity

Feedback is direct, blunt, and strictly aligned with OSCE standards.
No praise unless earned.
No softening of weaknesses.

11. Final Output
Final Score (0–100) with justification

Actionable improvements

Optional short checklist for future practice
"""

# 3. Streamlit UI setup
st.set_page_config(page_title="OSCE Simulator", layout="wide")
st.title("OSCE Patient Simulator (FMS Year 3)")

# Session state for chat
if "messages" not in st.session_state:
    st.session_state.messages = []
if "case_selected" not in st.session_state:
    st.session_state.case_selected = None
if "session_active" not in st.session_state:
    st.session_state.session_active = False

# Case list
CASE_LIST = [
    "Poorly controlled Type 2 Diabetes",
    "Resistant Hypertension",
    "CKD Stage 3",
    "Chest pain (rule out ACS)",
    "Shortness of breath (COPD / asthma / anxiety)",
    "Acute red eye",
    "Major depressive disorder",
    "Suicide risk assessment",
    "PV bleeding",
    "Contraception counselling",
    "Falls in elderly",
    "Polypharmacy review",
    "Breaking bad news",
    "Lifestyle counselling (smoking / weight)",
    "Domestic violence screening",
]

# Sidebar controls
st.sidebar.header("Station Controls")
start_button = st.sidebar.button("Start Session")
end_button = st.sidebar.button("End Session")
selected_case = st.sidebar.selectbox("Select Case (after start)", ["-- None --"] + CASE_LIST)

# Handle Start Session
if start_button:
    st.session_state.session_active = True
    st.session_state.messages = []
    st.session_state.case_selected = None

    user_msg = "start session"
    st.session_state.messages.append({"role": "user", "content": user_msg})

    response = model.generate_content(
        [
            {"role": "system", "content": OSCE_SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ]
    )
    ai_text = response.text.strip()
    st.session_state.messages.append({"role": "assistant", "content": ai_text})

# Handle case selection (start of station)
if st.session_state.session_active and selected_case != "-- None --" and st.session_state.case_selected is None:
    st.session_state.case_selected = selected_case
    user_msg = f"I choose the case: {selected_case}. Please begin the station."
    st.session_state.messages.append({"role": "user", "content": user_msg})

    response = model.generate_content(
        [
            {"role": "system", "content": OSCE_SYSTEM_PROMPT},
            *[
                {"role": m["role"], "content": m["content"]}
                for m in st.session_state.messages
            ]
        ]
    )
    ai_text = response.text.strip()
    st.session_state.messages.append({"role": "assistant", "content": ai_text})

# Handle End Session
if end_button and st.session_state.session_active:
    user_msg = "end session"
    st.session_state.messages.append({"role": "user", "content": user_msg})

    response = model.generate_content(
        [
            {"role": "system", "content": OSCE_SYSTEM_PROMPT},
            *[
                {"role": m["role"], "content": m["content"]}
                for m in st.session_state.messages
            ]
        ]
    )
    ai_text = response.text.strip()
    st.session_state.messages.append({"role": "assistant", "content": ai_text})
    st.session_state.session_active = False

# Chat display
st.subheader("Conversation")
for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.markdown(f"**Doctor:** {msg['content']}")
    else:
        st.markdown(f"**Patient / OSCE Feedback:** {msg['content']}")

# Input box for doctor questions
if st.session_state.session_active and st.session_state.case_selected:
    st.subheader("Ask your questions (Doctor)")
    user_input = st.text_input("Type your question and press Enter", key="input_box")

    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})

        response = model.generate_content(
            [
                {"role": "system", "content": OSCE_SYSTEM_PROMPT},
                *[
                    {"role": m["role"], "content": m["content"]}
                    for m in st.session_state.messages
                ]
            ]
        )
        ai_text = response.text.strip()
        st.session_state.messages.append({"role": "assistant", "content": ai_text})
        st.experimental_rerun()
else:
    st.info("Start a session and select a case to begin the OSCE simulation.")
