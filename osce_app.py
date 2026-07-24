import os
import streamlit as st
import google.generativeai as genai

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
