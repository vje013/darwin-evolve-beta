"""
Darwin Enterprise Evolve — Cosmos Reason Physical Grounding
Calls nvidia/Cosmos-Reason2-2B running on Google Colab GPU via Cloudflare tunnel.
"""
import os
import io
import base64
import httpx
from PIL import Image

COSMOS_API_URL = None

def _get_url():
    global COSMOS_API_URL
    if not COSMOS_API_URL:
        COSMOS_API_URL = os.getenv("COSMOS_API_URL", "")
    return COSMOS_API_URL

PHYSICS_PROMPT = """Analyze this vehicle Center Information Display (CID) image for physical-world ergonomic constraints.

<think>
Your reasoning.
</think>

Provide a structured physical assessment:
1. VIEWING GEOMETRY - screen size, viewing distance from driver H-point, off-axis angle, visual arc of touch targets
2. REACHABILITY - reach distance from steering wheel to screen, comfortable reach envelope
3. VISUAL HIERARCHY - contrast ratios, font sizes, information density
4. MOTION READABILITY - elements readable in <2sec glance vs >2sec fixation (safety concern)
5. TOUCH TARGET SIZING - sizes in mm, targets below ISO 15008 10mm minimum, mis-tap risk
6. ENVIRONMENTAL FACTORS - glare susceptibility, night mode adequacy

Be quantitative. Reference ISO 15008, ISO 15005, SAE J2365."""


def get_physical_context(image: Image.Image) -> str:
    """Run CID image through Cosmos Reason on Google Cloud GPU."""
    url = _get_url()
    if not url:
        return "[Cosmos Reason: No COSMOS_API_URL configured]"

    buf = io.BytesIO()
    image.save(buf, format='PNG')
    img_b64 = base64.b64encode(buf.getvalue()).decode('utf-8')

    try:
        resp = httpx.post(
            f"{url}/analyze",
            json={"image": img_b64, "prompt": PHYSICS_PROMPT},
            timeout=120.0,
        )

        if resp.status_code != 200:
            print(f"Cosmos error {resp.status_code}: {resp.text[:300]}")
            return f"[Cosmos Reason: HTTP {resp.status_code}]"

        return resp.json()["analysis"]

    except Exception as e:
        print(f"Cosmos error: {e}")
        return f"[Cosmos Reason: {str(e)}]"
