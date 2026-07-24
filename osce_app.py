import streamlit as st
import time
import tempfile
import io

import speech_recognition as sr
from gtts import gTTS
from pydub import AudioSegment, effects

import google.generativeai as genai
import os

# ============================================================
# CONFIGURATION
# ============================================================

st.set_page_config(page_title="OSCE Voice Simulator", layout="wide")

# Set your API key (Streamlit Cloud → Secrets)
GENAI_API_KEY = os.getenv("GEMINI_API_KEY", "")
if GENAI_API_KEY:
    genai.configure(api_key=GENAI_API_KEY)

MODEL_NAME = "gemini-1.5-flash"

# ============================================================
# SESSION STATE INITIALIZATION
# ============================================================

if "messages" not in st.session_state:
    st.session_state.messages = []

if "timer_start" not in st.session_state:
    st.session_state.timer_start = None

if "current_case" not in st.session_state:
    st.session_state.current_case = ""

if "profile" not in st.session_state:
    st.session_state.profile = {
        "gender": "neutral",
        "age_group": "adult",
        "emotion": "neutral",
        "pain": False,
        "breathless": False,
    }

# ============================================================
# TIMER
# ============================================================

def start_timer():
    st.session_state.timer_start = time.time()

def get_time_left():
    if st.session_state.timer_start is None:
        return 15 * 60
    elapsed = time.time() - st.session_state.timer_start
    return max(0, (15 * 60) - elapsed)

# ============================================================
# PRESET CASES (MAX 2 SYMPTOMS EACH)
# ============================================================

PRESET_CASES = {
    "Chest Pain": "I have chest pain since morning.",
    "Breathlessness": "I feel breathless when I walk.",
    "Abdominal Pain": "My stomach hurts since yesterday.",
    "Headache": "I've had a headache since last night.",
    "Fever": "I've been having fever since yesterday.",
    "Fatigue": "I feel tired all the time.",
    "Dizziness": "I feel dizzy when I stand up.",
    "Palpitations": "My heart feels like it's beating fast.",
    "Hypertension follow-up": "I came for my blood pressure check.",
    "Chronic cough": "I've been coughing for weeks.",
    "Asthma": "I'm wheezing and it's hard to breathe.",
    "Vomiting": "I've been vomiting since last night.",
    "Diarrhoea": "I've had diarrhoea since yesterday.",
    "Jaundice": "My eyes look yellow.",
    "Weakness": "My left arm feels weak.",
    "Numbness": "I can't feel my fingers.",
    "Seizure follow-up": "I had a fit last week.",
    "Anxiety": "I feel very anxious lately.",
    "Depression": "I don't feel like doing anything.",
    "Angry patient": "I'm not happy with the treatment.",
    "Insomnia": "I can't sleep at night.",
    "Fever in child": "My child has fever since yesterday.",
    "Vomiting in child": "My child keeps vomiting.",
    "Cough in child": "My child has been coughing.",
    "Early pregnancy bleeding": "I'm having bleeding in early pregnancy.",
    "Pelvic pain": "I have pain down here.",
    "Antenatal follow-up": "I came for my pregnancy check.",
    "Post-operative pain": "I have pain after my surgery.",
    "Wound infection": "My wound looks red and painful.",
    "Trauma": "I fell and hurt my leg.",
    "Shock": "I feel faint and cold.",
    "Allergic reaction": "I'm having swelling after eating.",
}

# ============================================================
# PROFILE DETECTION
# ============================================================

def detect_profile_from_text(text: str):
    t = text.lower()
    profile = {
        "gender": "neutral",
        "age_group": "adult",
        "emotion": "neutral",
        "pain": False,
        "breathless": False,
    }

    # Gender
    if any(x in t for x in ["mr ", "encik ", "pakcik ", "man", "boy"]):
        profile["gender"] = "male"
    if any(x in t for x in ["mrs ", "ms ", "puan ", "cik ", "woman", "girl"]):
        profile["gender"] = "female"

    # Age group
    if any(x in t for x in ["child", "boy", "girl", "my child"]):
        profile["age_group"] = "child"
    elif any(x in t for x in ["elderly", "old", "70-year-old", "80-year-old"]):
        profile["age_group"] = "elderly"
    elif any(x in t for x in ["middle-aged", "45", "50", "55"]):
        profile["age_group"] = "middle-aged"
    else:
        profile["age_group"] = "adult"

    # Emotion
    if any(x in t for x in ["anxious", "worried", "scared"]):
        profile["emotion"] = "anxious"
    if any(x in t for x in ["angry", "frustrated", "not happy"]):
        profile["emotion"] = "angry"
    if any(x in t for x in ["crying", "tearful", "sad"]):
        profile["emotion"] = "crying"

    # Breathless / pain
    if any(x in t for x in ["breathless", "short of breath", "wheezing"]):
        profile["breathless"] = True
    if "pain" in t or "hurt" in t:
        profile["pain"] = True

    return profile

# ============================================================
# VOICE FILTERS
# ============================================================

def apply_voice_profile(audio: AudioSegment, profile: dict) -> AudioSegment:
    audio = effects.normalize(audio)

    # Gender pitch
    if profile["gender"] == "male":
        audio = audio._spawn(audio.raw_data, overrides={"frame_rate": int(audio.frame_rate * 0.9)})
        audio = audio.set_frame_rate(44100)
    elif profile["gender"] == "female":
        audio = audio._spawn(audio.raw_data, overrides={"frame_rate": int(audio.frame_rate * 1.05)})
        audio = audio.set_frame_rate(44100)

    # Age pacing
    if profile["age_group"] == "elderly":
        audio = audio.speedup(playback_speed=0.95)
    elif profile["age_group"] == "child":
        audio = audio.speedup(playback_speed=1.05)

    # Emotion
    if profile["emotion"] == "anxious":
        audio = audio.speedup(playback_speed=1.03)
    elif profile["emotion"] == "angry":
        audio = audio.speedup(playback_speed=1.05)
        audio = audio + 2
    elif profile["emotion"] == "crying":
        audio = audio - 2

    # Pain / breathless
    if profile["breathless"]:
        audio = audio.speedup(playback_speed=0.97)
    if profile["pain"]:
        audio = audio.speedup(playback_speed=0.97)

    return audio

# ============================================================
# GEMINI PATIENT RESPONSE
# ============================================================

def get_patient_response(case_text: str, conversation: list, doctor_input: str) -> str:
    if not GENAI_API_KEY:
        return "AI key missing."

    system_prompt = (
        "You are an OSCE standardized patient in Malaysia. "
        "Respond naturally, briefly, and consistently with the case description."
    )

    history = ""
    for msg in conversation:
        if msg["role"] == "user":
            history += f"Doctor: {msg['content']}\n"
        else:
            history += f"Patient: {msg['content']}\n"

    prompt = (
        f"{system_prompt}\n\n"
        f"Case: {case_text}\n\n"
        f"Conversation:\n{history}\n"
        f"Doctor: {doctor_input}\n"
        f"Patient:"
    )

    model = genai.GenerativeModel(MODEL_NAME)
    resp = model.generate_content(prompt)

    try:
        return resp.text.strip()
    except:
        return "I am having difficulty responding."

# ============================================================
# TEXT-TO-SPEECH
# ============================================================

def synthesize_patient_voice(text: str, profile: dict) -> bytes:
    tts = gTTS(text=text, lang="en")
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
        tts.save(tmp.name)
        audio = AudioSegment.from_mp3(tmp.name)

    audio = apply_voice_profile(audio, profile)

    buf = io.BytesIO()
    audio.export(buf, format="mp3")
    return buf.getvalue()

# ============================================================
# SPEECH-TO-TEXT
# ============================================================

def transcribe_speech_from_mic() -> str:
    r = sr.Recognizer()
    with sr.Microphone() as source:
        st.info("Listening...")
        audio = r.listen(source, timeout=5, phrase_time_limit=10)
    try:
        return r.recognize_google(audio)
    except:
        return ""

# ============================================================
# UI LAYOUT
# ============================================================

st.title("OSCE Voice Simulator (Preset + Custom)")

col_left, col_right = st.columns([2, 1])

# -----------------------------
# LEFT SIDE
# -----------------------------
with col_left:
    st.subheader("Case Selection")

    preset_name = st.selectbox(
        "Select preset case",
        ["(None)"] + list(PRESET_CASES.keys())
    )

    custom_case = st.text_area(
        "Or enter custom case",
        placeholder="Example: Encik Razak, 55, has chest pain since morning."
    )

    if custom_case.strip():
        case_text = custom_case.strip()
    elif preset_name != "(None)":
        case_text = PRESET_CASES[preset_name]
    else:
        case_text = ""

    st.session_state.current_case = case_text

    if case_text:
        st.info(f"Active case: {case_text}")
        st.session_state.profile = detect_profile_from_text(case_text)
    else:
        st.warning("Please select a case.")

    st.subheader("Consultation")

    doctor_input = st.text_input("Doctor:", placeholder="Tell me more about your pain.")

    if st.button("🎙️ Use microphone"):
        spoken = transcribe_speech_from_mic()
        if spoken:
            doctor_input = spoken
            st.success(f"You said: {spoken}")
        else:
            st.error("Could not understand speech.")

    if st.button("Send") and case_text and doctor_input.strip():
        st.session_state.messages.append({"role": "user", "content": doctor_input.strip()})
        reply = get_patient_response(case_text, st.session_state.messages, doctor_input.strip())
        st.session_state.messages.append({"role": "assistant", "content": reply})

        audio_bytes = synthesize_patient_voice(reply, st.session_state.profile)
        st.audio(audio_bytes, format="audio/mp3")

    st.subheader("Conversation Log")
    for msg in st.session_state.messages:
        if msg["role"] == "user":
            st.markdown(f"**Doctor:** {msg['content']}")
        else:
            st.markdown(f"**Patient:** {msg['content']}")

    if st.button("Reset"):
        st.session_state.messages = []
        st.session_state.timer_start = None
        st.session_state.current_case = ""
        st.session_state.profile = {
            "gender": "neutral",
            "age_group": "adult",
            "emotion": "neutral",
            "pain": False,
            "breathless": False,
        }
        st.success("Station reset.")

# -----------------------------
# RIGHT SIDE
# -----------------------------
with col_right:
    st.subheader("OSCE Timer (15 minutes)")

    if st.button("Start Timer"):
        start_timer()

    time_left = get_time_left()
    minutes = int(time_left // 60)
    seconds = int(time_left % 60)
    st.markdown(f"**Time Left:** {minutes:02d}:{seconds:02d}")

    st.subheader("Detected Profile")
    profile = st.session_state.profile

    st.markdown(f"**Gender:** {profile['gender']}")
    st.markdown(f"**Age Group:** {profile['age_group']}")
    st.markdown(f"**Emotion:** {profile['emotion']}")
    st.markdown(f"**Pain:** {'Yes' if profile['pain'] else 'No'}")
    st.markdown(f"**Breathless:** {'Yes' if profile['breathless'] else 'No'}")

    st.caption("Voice effects are subtle and OSCE-style.")
