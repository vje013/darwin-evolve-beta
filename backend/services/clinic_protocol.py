"""
Darwin Enterprise Evolve — Structured Usability Clinic Protocol
Multi-turn facilitated session with PROMPTER agent and persona respondent.
Cosmos-grounded, protocol-driven, transcript-producing.
"""
import os
import json
import httpx
import base64
import io
from datetime import datetime, timedelta
from PIL import Image
from services.personas import CustomerPersona
from services.cosmos_grounding import get_physical_context

OPENROUTER_API_KEY = None

def _get_key():
    global OPENROUTER_API_KEY
    if not OPENROUTER_API_KEY:
        OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
    return OPENROUTER_API_KEY


# Fixed ordered usability protocol
PROMPTER_SPINE = [
    {
        "id": "intro",
        "prompter": "Hi, thanks for coming in today. I'm going to show you a screen from a vehicle infotainment system. There are no right or wrong answers here — I just want your honest reactions. If something confuses you or you can't find something, that's useful information. Ready?",
        "instruction": "Respond naturally to the facilitator's introduction. Stay in character. Express your initial feelings about participating.",
    },
    {
        "id": "first_impression",
        "prompter": "Okay. Take a look at this screen. Don't touch anything yet. Just tell me your first impression — what do you notice first, what stands out, what's your gut reaction?",
        "instruction": "Give your honest first impression of the CID screen. What catches your eye? What's your gut feeling? Stay in character based on your age, tech comfort, and priorities.",
    },
    {
        "id": "free_explore",
        "prompter": "Now go ahead and imagine you're exploring this screen freely. Walk me through what you'd tap on first, what you'd try to do, what you'd look for.",
        "instruction": "Describe how you would explore this interface. What would you tap first? What are you looking for? Where do you get stuck or confused? Stay in character.",
    },
    {
        "id": "rate_clear",
        "prompter": "Okay. I'm going to ask you to rate a few things on a scale of 1 to 10. First — how CLEAR is this interface? Can you tell what everything does?",
        "instruction": "Rate clarity 1-10 and explain why. Be specific about what's clear and what isn't. Reference specific elements you can see in the image.",
    },
    {
        "id": "rate_simple",
        "prompter": "Got it. Next — how SIMPLE does it feel? Does it feel like there's too much going on, or is it manageable?",
        "instruction": "Rate simplicity 1-10 and explain. Is there too much on screen? Too little? Is the layout overwhelming or clean? Be specific.",
    },
    {
        "id": "rate_modern",
        "prompter": "Okay. How MODERN does this look to you? Does it feel current, outdated, or futuristic?",
        "instruction": "Rate modernity 1-10. Does it look like a 2026 product? Compare to interfaces you use daily — phone, apps, other cars. Be honest.",
    },
    {
        "id": "rate_seamless",
        "prompter": "Next — how SEAMLESS does the experience feel? Does everything seem connected, or does it feel like separate pieces bolted together?",
        "instruction": "Rate seamlessness 1-10. Does the UI feel cohesive? Do elements relate to each other? Would transitions feel smooth or jarring?",
    },
    {
        "id": "rate_personal",
        "prompter": "Last rating — how PERSONAL does it feel? Could you make this yours? Does it feel like it was designed for someone like you?",
        "instruction": "Rate personalization 1-10. Does this feel like it was designed for your demographic, your needs, your lifestyle? Or does it feel generic?",
    },
    {
        "id": "task_darkmode",
        "prompter": "Okay, thanks. Now I'm going to ask you to try a specific task. Imagine you want to switch this screen to dark mode. Where would you look? What would you tap?",
        "instruction": "Describe where you'd look and what you'd tap to find dark mode. If you can't find it, say so. Express any frustration or confusion honestly.",
    },
    {
        "id": "task_home",
        "prompter": "Got it. Now imagine you're deep in a submenu and you want to get back to the home screen. How would you do that?",
        "instruction": "Describe how you'd navigate back to home. Is it obvious? Would you use a button, swipe, or be lost? Be honest about confusion.",
    },
    {
        "id": "layout_opinion",
        "prompter": "Okay. Looking at the overall layout — the way things are arranged on screen — what do you think? Is anything in the wrong place? Anything you'd move?",
        "instruction": "Give your opinion on the layout. What's in the right place? What's in the wrong place? What would you rearrange? Think about what you need while driving.",
    },
    {
        "id": "dealbreakers",
        "prompter": "Almost done. Is there anything about this screen that would be a dealbreaker for you — something that would make you not want this car?",
        "instruction": "Be honest about dealbreakers. Given your priorities (safety, convenience, aesthetics, budget), is there anything here that would stop you from buying this car? Why?",
    },
    {
        "id": "likes",
        "prompter": "And on the flip side — what do you like most? What's the best thing about this screen?",
        "instruction": "Name your favorite things about the interface. What works well for someone like you? What would you brag about to friends?",
    },
    {
        "id": "closing",
        "prompter": "That's everything. Thanks for your time — this was really helpful. Any last thoughts before we wrap up?",
        "instruction": "Give any final thoughts. Summarize your overall feeling. Would you be happy with this in your car? Stay in character.",
    },
]


def _call_persona(persona: CustomerPersona, physical_context: str,
                  step: dict, transcript_so_far: str, image_b64: str) -> str:
    """Call Gemini as the persona for one turn."""

    system = f"""You are roleplaying as a specific customer in a usability study for a vehicle infotainment screen.

YOUR CHARACTER:
- Name: {persona.name}
- Age: {persona.age}
- Tech Comfort: {persona.tech_comfort}/10
- Vehicle Type: {persona.vehicle_type}
- Primary Use: {persona.primary_use}
- Safety Priority: {persona.safety_priority}/10
- Convenience Priority: {persona.convenience_priority}/10
- Aesthetics Priority: {persona.aesthetics_priority}/10
- Budget Sensitivity: {persona.budget_sensitivity}
- Description: {persona.description}

PHYSICAL CONSTRAINTS OF THIS SCREEN (from engineering analysis):
{physical_context}

RULES:
- Stay in character at all times. Speak the way this person would actually speak.
- Reference the physical constraints when relevant — e.g., if touch targets are small and you're elderly, say your fingers are too big.
- Be specific. Point to things you see in the image.
- Don't be artificially positive or negative. Be honest for who you are.
- Keep responses to 2-4 sentences. This is a conversation, not an essay.
- When rating 1-10, give the number first, then explain.

INSTRUCTION FOR THIS TURN:
{step['instruction']}"""

    messages = [{"role": "system", "content": system}]

    if transcript_so_far:
        messages.append({"role": "user", "content": f"Here is the conversation so far:\n\n{transcript_so_far}\n\nThe facilitator just said: \"{step['prompter']}\"\n\nRespond in character."})
    else:
        messages.append({"role": "user", "content": [
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}"}},
            {"type": "text", "text": f"The facilitator says: \"{step['prompter']}\"\n\nRespond in character."},
        ]})

    try:
        resp = httpx.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {_get_key()}",
                "Content-Type": "application/json",
            },
            json={
                "model": "google/gemini-2.5-flash",
                "messages": messages,
                "max_tokens": 300,
                "temperature": 0.8,
            },
            timeout=60.0,
        )

        if resp.status_code != 200:
            return f"[Error: {resp.status_code}]"

        return resp.json()["choices"][0]["message"]["content"]

    except Exception as e:
        return f"[Error: {str(e)}]"


def run_clinic_session(image: Image.Image, persona: CustomerPersona,
                       feature_focus: str = "", specific_question: str = "") -> dict:
    """
    Run a full structured clinic session with one persona.
    Returns transcript + extracted scores.
    """
    # Step 1: Cosmos Reason physical grounding
    physical_context = get_physical_context(image)

    # Convert image to base64
    buf = io.BytesIO()
    image.save(buf, format='PNG')
    image_b64 = base64.b64encode(buf.getvalue()).decode('utf-8')

    # Step 2: Run protocol
    transcript = []
    session_start = datetime.now()
    scores = {}

    for i, step in enumerate(PROMPTER_SPINE):
        # Synthetic timestamp
        timestamp = session_start + timedelta(seconds=i * 45 + 10)
        ts_str = timestamp.strftime("%H:%M:%S")

        # Build transcript so far
        transcript_text = ""
        for entry in transcript:
            transcript_text += f"[{entry['timestamp']}] {entry['speaker']}: {entry['text']}\n"

        # Add prompter line
        transcript.append({
            "timestamp": ts_str,
            "speaker": "Facilitator",
            "text": step["prompter"],
            "step_id": step["id"],
        })

        # Get persona response
        persona_response = _call_persona(
            persona, physical_context, step,
            transcript_text + f"[{ts_str}] Facilitator: {step['prompter']}",
            image_b64,
        )

        response_ts = (timestamp + timedelta(seconds=20)).strftime("%H:%M:%S")
        transcript.append({
            "timestamp": response_ts,
            "speaker": persona.name,
            "text": persona_response,
            "step_id": step["id"],
        })

        # Extract scores from rating steps
        if step["id"].startswith("rate_"):
            attr = step["id"].replace("rate_", "")
            try:
                import re
                nums = re.findall(r'\b(\d+)\b', persona_response[:50])
                if nums:
                    score = int(nums[0])
                    if 1 <= score <= 10:
                        scores[attr] = score
            except:
                pass

    # Step 3: Compile results
    return {
        "persona": persona.to_dict(),
        "physical_context": physical_context,
        "feature_focus": feature_focus,
        "specific_question": specific_question,
        "transcript": transcript,
        "scores": scores,
        "avg_score": round(sum(scores.values()) / len(scores), 1) if scores else 0,
        "turn_count": len(transcript),
        "session_duration_estimate": f"{len(PROMPTER_SPINE) * 45}s",
    }


def run_full_protocol_clinic(image_bytes: bytes, feature_focus: str,
                             specific_question: str, persona_names: list = None) -> dict:
    """
    Run the full protocol across selected personas (or all 20).
    Returns all transcripts + summary.
    """
    from services.personas import CUSTOMERS

    image = Image.open(io.BytesIO(image_bytes))

    if persona_names:
        personas = [p for p in CUSTOMERS if p.name in persona_names]
    else:
        personas = CUSTOMERS

    sessions = {}
    for persona in personas:
        session = run_clinic_session(image, persona, feature_focus, specific_question)
        sessions[persona.name] = session

    # Summary
    all_scores = {}
    for name, session in sessions.items():
        for attr, score in session.get("scores", {}).items():
            if attr not in all_scores:
                all_scores[attr] = []
            all_scores[attr].append(score)

    avg_scores = {attr: round(sum(s) / len(s), 1) for attr, s in all_scores.items()}

    return {
        "feature_focus": feature_focus,
        "specific_question": specific_question,
        "persona_count": len(sessions),
        "sessions": sessions,
        "avg_scores": avg_scores,
        "overall_avg": round(sum(avg_scores.values()) / len(avg_scores), 1) if avg_scores else 0,
    }
