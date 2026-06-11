"""
Darwin Enterprise Evolve Beta — Clinic Agent Routes
POST image + feature + question → full 20-persona CID analysis.
Auto-stores results in MongoDB Atlas with vector embeddings.
"""
import base64
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from auth import get_current_user
from services.clinic_agent import run_full_clinic
from services.personas import CUSTOMERS

router = APIRouter(prefix="/vendr/clinic", tags=["vendr"])


@router.get("/personas")
async def list_personas(user: dict = Depends(get_current_user)):
    return [p.to_dict() for p in CUSTOMERS]


@router.post("/analyze")
async def analyze_feature(
    image: UploadFile = File(...),
    feature_focus: str = Form(...),
    specific_question: str = Form(...),
    user: dict = Depends(get_current_user),
):
    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(400, "Please upload an image file")

    image_bytes = await image.read()
    if len(image_bytes) > 10 * 1024 * 1024:
        raise HTTPException(400, "Image must be under 10MB")

    try:
        results = run_full_clinic(image_bytes, feature_focus, specific_question)

        # Auto-store in MongoDB Atlas with vector embedding
        try:
            from services.mongo_store import store_clinic_session
            store_clinic_session(results)
        except Exception as e:
            print(f"MongoDB store error: {e}")

        return results
    except Exception as e:
        raise HTTPException(500, f"Analysis failed: {str(e)}")


@router.post("/protocol")
async def run_protocol_session(
    image: UploadFile = File(...),
    feature_focus: str = Form(""),
    specific_question: str = Form(""),
    personas: str = Form(""),
    user: dict = Depends(get_current_user),
):
    """
    Run a full structured usability clinic protocol.
    Cosmos-grounded, multi-turn facilitated session per persona.
    """
    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(400, "Please upload an image file")

    image_bytes = await image.read()
    if len(image_bytes) > 10 * 1024 * 1024:
        raise HTTPException(400, "Image must be under 10MB")

    persona_list = [p.strip() for p in personas.split(",") if p.strip()] if personas else None

    try:
        from services.clinic_protocol import run_full_protocol_clinic
        results = run_full_protocol_clinic(image_bytes, feature_focus, specific_question, persona_list)

        # Auto-store in MongoDB
        try:
            from services.mongo_store import store_clinic_session
            store_clinic_session(results)
        except Exception as e:
            print(f"MongoDB store error: {e}")

        return results
    except Exception as e:
        raise HTTPException(500, f"Protocol session failed: {str(e)}")
