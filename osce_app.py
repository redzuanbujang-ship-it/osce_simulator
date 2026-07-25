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
st.write("DEBUG: GEMINI_API_KEY present:", bool(GENAI_API_KEY))
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
# Preset cases (fixed unterminated string)
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
# Profile detection
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

    if any(x in t for x in ["mr ", "encik ", "pakcik ", "man", "boy"]):
        profile["gender"] = "male"
    if any(x in t for x in ["mrs ", "ms ", "puan ", "cik ", "woman", "girl"]):
        profile["gender"] = "female"

    if any(x in t for x in ["child", "boy", "girl", "my child"]):
        profile["age_group"] = "child"
    elif any(x in t for x in ["elderly", "old", "70-year-old", "80-year-old"]):
        profile["age_group"] = "elderly"
    elif any(x in t for x in ["middle-aged", "45", "50", "55"]):
        profile["age_group"] = "middle-aged"
    else:
        profile["age_group"] = "adult"

    if any(x in t for x in ["anxious", "worried", "scared"]):
        profile["emotion"] = "anxious"
    if any(x in t for x in ["angry", "frustrated", "not happy"]):
        profile["emotion"] = "angry"
    if any(x in t for x in ["crying", "tearful", "sad"]):
        profile["emotion"] = "crying"

    if any(x in t for x in ["breathless", "short of breath", "wheezing"]):
        profile["breathless"] = True
    if "pain" in t or "hurt" in t:
        profile["pain"] = True

    return profile

# ============================================================
# GenAI patient response (robust)
# ============================================================
def get_patient_response(case_text: str, conversation: list, doctor_input: str) -> str:
    # Ensure genai is initialized lazily
    init_genai_once()

    if not GENAI_API_KEY:
        return "AI key missing."

    # If we didn't create a client/module, try to create a Client now (based on detected attributes)
    global genai_client, genai
    if genai_client is None and genai is not None and hasattr(genai, "Client"):
        try:
            genai_client = genai.Client(api_key=GENAI_API_KEY)
        except Exception:
            genai_client = None

    if genai is None and genai_client is None:
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

    # Build a simple chat-style message list for chat APIs
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Case: {case_text}\n\nConversation:\n{history}\nDoctor: {doctor_input}\nPatient:"}
    ]

    prompt_text = (
        f"{system_prompt}\n\n"
        f"Case: {case_text}\n\n"
        f"Conversation:\n{history}\n"
        f"Doctor: {doctor_input}\n"
        f"Patient:"
    )

    try:
        # 1) If we have a client object, prefer chat or models APIs
        if genai_client is not None:
            # Try chat API first (client.chat.create)
            if hasattr(genai_client, "chat") and hasattr(genai_client.chat, "create"):
                resp = genai_client.chat.create(model=MODEL_NAME, messages=messages)
                # response shapes vary: try common fields
                if hasattr(resp, "content"):
                    return str(resp.content).strip()
                if hasattr(resp, "message"):
                    return getattr(resp.message, "content", str(resp.message)).strip()
                # fallback to dict-like
                try:
                    return str(resp["choices"][0]["message"]["content"]).strip()
                except Exception:
                    pass

            # Try models.generate (client.models.generate)
            if hasattr(genai_client, "models") and hasattr(genai_client.models, "generate"):
                # many versions accept model and prompt or input
                try:
                    resp = genai_client.models.generate(model=MODEL_NAME, prompt=prompt_text)
                except TypeError:
                    # alternate param name
                    resp = genai_client.models.generate(model=MODEL_NAME, input=prompt_text)
                # common response shapes
                if hasattr(resp, "text"):
                    return str(resp.text).strip()
                try:
                    return str(resp["output"][0]["content"][0]["text"]).strip()
                except Exception:
                    pass

        # 2) If module-level functions exist, try them
        if genai is not None:
            # module-level chat
            if hasattr(genai, "chat") and hasattr(genai.chat, "create"):
                resp = genai.chat.create(model=MODEL_NAME, messages=messages)
                if hasattr(resp, "content"):
                    return str(resp.content).strip()
                try:
                    return str(resp["choices"][0]["message"]["content"]).strip()
                except Exception:
                    pass

            # module-level models.generate
            if hasattr(genai, "models") and hasattr(genai.models, "generate"):
                try:
                    resp = genai.models.generate(model=MODEL_NAME, prompt=prompt_text)
                except TypeError:
                    resp = genai.models.generate(model=MODEL_NAME, input=prompt_text)
                if hasattr(resp, "text"):
                    return str(resp.text).strip()
                try:
                    return str(resp["output"][0]["content"][0]["text"]).strip()
                except Exception:
                    pass

    except Exception as e:
        st.error("GenAI request failed.")
        st.write(f"GenAI error: {e}")
        return "I am having difficulty responding."

    return "AI key missing."



# ============================================================
# UI layout
# ============================================================
st.title("OSCE Simulator (Preset + Custom)")

col_left, col_right = st.columns([2, 1])

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
        st.error("Microphone is disabled.")

    if st.button("Send") and case_text and doctor_input.strip():
        st.session_state.messages.append({"role": "user", "content": doctor_input.strip()})
        reply = get_patient_response(case_text, st.session_state.messages, doctor_input.strip())
        st.session_state.messages.append({"role": "assistant", "content": reply})

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

    st.caption("OSCE-style text-only simulator.")
