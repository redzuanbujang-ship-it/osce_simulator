import streamlit as st
import time
import os
import importlib

# ============================================================
# Page config (must be before other Streamlit UI calls)
# ============================================================
st.set_page_config(page_title="OSCE Simulator", layout="wide")

# ============================================================
# Lazy GenAI initialization (non-blocking)
# ============================================================
GENAI_API_KEY = os.getenv("GEMINI_API_KEY", "")
genai = None
genai_client = None
MODEL_NAME = "gemini-1.5-flash"

def init_genai_once():
    """
    Lazy initialize genai module and a client object.
    This runs only when called (not at import time), and it never raises.
    """
    global genai, genai_client
    if genai is not None or genai_client is not None:
        return

    try:
        # Try common package names without failing the app
        for pkg in ("google.genai", "google.generativeai"):
            try:
                mod = importlib.import_module(pkg)
                genai = mod
                break
            except Exception:
                continue

        if genai is None:
            # library not installed or incompatible; leave genai None
            return

        # Try safe ways to create a client without assuming configure exists
        try:
            if hasattr(genai, "Client"):
                try:
                    genai_client = genai.Client(api_key=GENAI_API_KEY)
                except Exception:
                    genai_client = None
        except Exception:
            genai_client = None

        try:
            if genai_client is None and hasattr(genai, "GenerativeModel"):
                try:
                    genai_client = genai.GenerativeModel(MODEL_NAME)
                except Exception:
                    genai_client = None
        except Exception:
            genai_client = None

        # If module has a top-level configure function, call it but ignore errors
        try:
            if hasattr(genai, "configure"):
                try:
                    genai.configure(api_key=GENAI_API_KEY)
                except Exception:
                    pass
        except Exception:
            pass

    except Exception:
        genai = None
        genai_client = None

# ============================================================
# Session state initialization
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
# Timer helpers
# ============================================================
def start_timer():
    st.session_state.timer_start = time.time()

def get_time_left():
    if st.session_state.timer_start is None:
        return 15 * 60
    elapsed = time.time() - st.session_state.timer_start
    return max(0, (15 * 60) - elapsed)

# ============================================================
# Preset cases
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
    "Fever in child": "My child has
