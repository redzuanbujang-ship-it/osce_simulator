import streamlit as st
import time
import os
import google.genai as genai   # Updated Gemini API

# ============================================================
# CONFIGURATION
# ============================================================

st.set_page_config(page_title="OSCE Simulator", layout="wide")

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
# PRESET CASES
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
