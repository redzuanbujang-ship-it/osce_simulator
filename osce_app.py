import streamlit as st
import time
import io
import re

import google.generativeai as genai
from gtts import gTTS
from pydub import AudioSegment, effects

# ============================================================
# CONFIG
# ============================================================

st.set_page_config(page_title="OSCE Voice Simulator", layout="wide")

# Configure Gemini (adjust to your setup)
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    MODEL_NAME = "gemini-1.5-flash"
except Exception:
    MODEL_NAME = None

# ============================================================
# SESSION STATE
# ============================================================

if "messages" not in st.session_state:
    st.session_state.messages = []

if "timer_start" not in st.session_state:
    st.session_state.timer_start = None

if "profile" not in st.session_state:
    st.session_state.profile = {
        "gender": "neutral",
        "age_group": "adult",
        "emotion": "neutral",
        "pain": False,
        "breathless": False,
    }

# ============================================================
# PRESET CASES (MAX 2 SYMPTOMS EACH)
# ============================================================

PRESET_CASES = {
    "Chest Pain": "I have chest pain since morning.",
    "Breathlessness": "I feel breathless when I walk.",
    "Abdominal Pain": "My stomach hurts since yesterday.",
    "Headache": "I’ve had a headache since last night.",
    "Fever": "I’ve been having fever since yesterday.",
    "Fatigue": "I feel tired all the time.",
    "Dizziness```python
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

# Set your API key (you can also use Streamlit secrets)
GENAI_API_KEY = os.getenv("GENAI_API_KEY", "")
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
# HELPER: TIMER
# ============================================================

def start_timer():
    st.session_state.timer_start = time.time()

def get_time_left():
    if st.session_state.timer_start is None:
        return 15 * 60  # 15 minutes
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
# PROFILE DETECTION (GENDER, AGE, EMOTION)
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
    elif any(x in t for x in ["teen", "teenage", "adolescent"]):
        profile["age_group"] = "teen"
    elif any(x in t for x in ["elderly", "old", "70-year-old", "80-year-old", "72", "68", "65"]):
        profile["age_group"] = "elderly"
    elif any(x in t for x in ["40-year-old", "50-year-old", "middle-aged", "45", "52", "55"]):
        profile["age_group"] = "middle-aged"
    else:
        profile["age_group"] = "adult"

    # Emotion
    if any(x in t for x in ["anxious", "worried", "scared", "nervous"]):
        profile["emotion"] = "anxious"
    if any(x in t for x in ["angry", "frustrated", "not happy"]):
        profile["emotion"] = "angry"
    if any(x in t for x in ["crying", "tearful", "sad", "upset"]):
        profile["emotion"] = "crying"
    if any(x in t for x in ["can't sleep", "insomnia"]):
        profile["emotion"] = "neutral"  # insomnia but neutral tone
    # Breathless / pain flags
    if any(x in t for x in ["breathless", "short of breath", "wheezing", "hard to breathe"]):
        profile["breathless"] = True
    if any(x in t for x in ["pain", "hurt", "painful"]):
        profile["pain"] = True

    return profile

# ============================================================
# VOICE FILTERS (SUBTLE EMOTIONAL EFFECTS)
# ============================================================

def apply_voice_profile(audio: AudioSegment, profile: dict) -> AudioSegment:
    # Base: normalize volume
    audio = effects.normalize(audio)

    # Gender pitch simulation (subtle)
    if profile["gender"] == "male":
        audio = audio._spawn(audio.raw_data, overrides={"frame_rate": int(audio.frame_rate * 0.9)})
        audio = audio.set_frame_rate(44100)
    elif profile["gender"] == "female":
        audio = audio._spawn(audio.raw_data, overrides={"frame_rate": int(audio.frame_rate * 1.05)})
        audio = audio.set_frame_rate(44100)

    # Age group pacing (subtle)
    if profile["age_group"] == "elderly":
        audio = audio.speedup(playback_speed=0.95)
        audio = audio - 2  # slightly softer
    elif profile["age_group"] == "child":
        audio = audio.speedup(playback_speed=1.05)
    elif profile["age_group"] == "teen":
        audio = audio.speedup(playback_speed=1.03)
    elif profile["age_group"] == "middle-aged":
        audio = audio.speedup(playback_speed=0.98)
    else:  # adult
        audio = audio.speedup(playback_speed=1.0)

    # Emotion (subtle)
    emotion = profile["emotion"]
    if emotion == "anxious":
        audio = audio.speedup(playback_speed=1.03)
    elif emotion == "angry":
        audio = audio.speedup(playback_speed=1.05)
        audio = audio + 2  # slightly louder
    elif emotion == "crying":
        audio = audio - 2  # softer

    # Breathless / pain pacing (subtle)
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
        return "I am a simulated patient, but the AI key is not configured."

    system_prompt = (
        "You are an OSCE standardized patient in a Malaysian clinical setting. "
        "Respond as the patient, in short, natural sentences, based on the case description. "
        "Keep answers concise, like a real OSCE station. Use simple English with occasional Malaysian flavour."
    )

    history_text = ""
    for msg in conversation:
        role = msg["role"]
        content = msg["content"]
        if role == "user":
            history_text += f"Doctor: {content}\n"
        else:
            history_text += f"Patient: {content}\n"

    prompt = (
        f"{system_prompt}\n\n"
        f"Case description:\n{case_text}\n\n"
        f"Conversation so far:\n{history_text}\n\n"
        f"Doctor just said:\n{doctor_input}\n\n"
        f"Respond as the patient."
    )

    model = genai.GenerativeModel(MODEL_NAME)
    resp = model.generate_content(prompt)
    try:
        return resp.text.strip()
    except Exception:
        return "I am having some difficulty responding right now."

# ============================================================
# TEXT-TO-SPEECH (gTTS + PROFILE FILTERS)
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
# SPEECH-TO-TEXT (MIC INPUT)
# ============================================================

def transcribe_speech_from_mic() -> str:
    r = sr.Recognizer()
    with sr.Microphone() as source:
        st.info("Listening... please speak now.")
        audio = r.listen(source, timeout=5, phrase_time_limit=10)
    try:
        text = r.recognize_google(audio)
        return text
    except sr.UnknownValueError:
        return ""
    except sr.RequestError:
        return ""

# ============================================================
# UI LAYOUT
# ============================================================

st.title("OSCE Voice Simulator (Preset + Custom, No MP3 Files)")

col_left, col_right = st.columns([2, 1])

# -----------------------------
# LEFT: CASE SELECTION + CHAT
# -----------------------------
with col_left:
    st.subheader("🩺 Case selection")

    preset_name = st.selectbox(
        "Select preset case",
        ["(None)"] + list(PRESET_CASES.keys()),
        index=0,
    )

    custom_case = st.text_area(
        "Or enter custom case (overrides preset if not empty)",
        height=100,
        placeholder="Example: Mr. Ahmad, a 54-year-old man, has chest pain since morning and feels anxious."
    )

    # Decide which case text to use
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
        st.warning("Please select a preset case or enter a custom case.")

    st.subheader("💬 Consultation")

    # Doctor input (text)
    doctor_input = st.text_input(
        "Doctor: type your question or statement",
        placeholder="Can you tell me more about your chest pain?"
    )

    # Doctor input (voice)
    if st.button("🎙️ Use microphone instead"):
        spoken = transcribe_speech_from_mic()
        if spoken:
            doctor_input = spoken
            st.success(f"You said: {spoken}")
        else:
            st.error("Could not understand your speech. Please try again or type instead.")

    # Send message
    if st.button("Send to patient") and case_text and doctor_input.strip():
        st.session_state.messages.append({"role": "user", "content": doctor_input.strip()})
        patient_reply = get_patient_response(case_text, st.session_state.messages, doctor_input.strip())
        st.session_state.messages.append({"role": "assistant", "content": patient_reply})

        # Synthesize voice
        audio_bytes = synthesize_patient_voice(patient_reply, st.session_state.profile)
        st.audio(audio_bytes, format="audio/mp3")

    # Conversation log
    st.subheader("📜 Conversation log")
    for msg in st.session_state.messages:
        if msg["role"] == "user":
            st.markdown(f"**Doctor:** {msg['content']}")
        else:
            st.markdown(f"**Patient:** {msg['content']}")

    # Reset
    if st.button("Reset station"):
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
# RIGHT: TIMER + PROFILE VIEW
# -----------------------------
with col_right:
    st.subheader("⏱️ OSCE Timer (15 minutes)")

    if st.button("Start OSCE Station"):
        start_timer()

    time_left = get_time_left()
    minutes = int(time_left // 60)
    seconds = int(time_left % 60)
    st.markdown(f"**Time Left:** {minutes:02d}:{seconds:02d}")

    st.subheader("🧬 Detected patient profile")

    profile = st.session_state.profile
    st.markdown(f"**Gender:** {profile['gender'].capitalize()}")
    st.markdown(f"**Age group:** {profile['age_group'].replace('-', ' ').capitalize()}")
    st.markdown(f"**Emotion:** {profile['emotion'].capitalize()}")
    st.markdown(f"**Pain baseline:** {'Yes' if profile['pain'] else 'No'}")
    st.markdown(f"**Breathless baseline:** {'Yes' if profile['breathless'] else 'No'}")

    st.caption("Voice effects are subtle and OSCE-style: small changes in speed, volume, and pitch only.")
