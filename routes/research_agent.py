"""
Darwin Enterprise Evolve Beta — Research Agent + Data Analyst Routes
"""
import os
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from pydantic import BaseModel
from auth import get_current_user
from services.research_agent import generate_research
from services.data_analyst import load_csv_to_db, query_data

router = APIRouter(prefix="/vendr/research", tags=["vendr"])


class ResearchRequest(BaseModel):
    query: str
    max_papers: int = 50


class DataQueryRequest(BaseModel):
    db_id: str
    query: str


class PodcastAudioRequest(BaseModel):
    transcript: str
    title: str = "HMI Research"


@router.post("/generate")
async def generate_research_content(
    req: ResearchRequest,
    user: dict = Depends(get_current_user),
):
    """Generate newsletter + podcast from arXiv research papers."""
    if not req.query.strip():
        raise HTTPException(400, "Please provide research topics")

    try:
        results = generate_research(req.query, req.max_papers)
        return results
    except Exception as e:
        raise HTTPException(500, f"Research generation failed: {str(e)}")


# --- Podcast Audio ---

@router.post("/podcast/generate-audio")
async def generate_podcast_audio_endpoint(
    req: PodcastAudioRequest,
    user: dict = Depends(get_current_user),
):
    """Generate actual audio podcast from transcript via NotebookLM."""
    if not req.transcript.strip():
        raise HTTPException(400, "Transcript is empty")

    try:
        from services.podcast_audio import generate_podcast_audio
        filepath = await generate_podcast_audio(req.transcript, req.title)
        return {"audio_path": filepath, "status": "complete"}
    except Exception as e:
        raise HTTPException(500, f"Audio generation failed: {str(e)}")


@router.get("/podcast/download/{filename}")
async def download_podcast(filename: str, user: dict = Depends(get_current_user)):
    """Download a generated podcast MP3."""
    import tempfile
    filepath = os.path.join(tempfile.gettempdir(), "darwin_podcasts", filename)
    if not os.path.exists(filepath):
        raise HTTPException(404, "Podcast file not found")
    return FileResponse(filepath, media_type="audio/mpeg", filename=filename)


# --- Data Analyst Sub-routes ---

@router.post("/data/upload")
async def upload_dataset(
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
):
    """Upload a CSV file for data analysis."""
    if not file.filename or not file.filename.endswith('.csv'):
        raise HTTPException(400, "Please upload a CSV file")

    csv_bytes = await file.read()
    if len(csv_bytes) > 50 * 1024 * 1024:
        raise HTTPException(400, "File must be under 50MB")

    try:
        result = load_csv_to_db(csv_bytes, file.filename)
        return result
    except Exception as e:
        raise HTTPException(500, f"Failed to load dataset: {str(e)}")


@router.post("/data/query")
async def query_dataset_endpoint(
    req: DataQueryRequest,
    user: dict = Depends(get_current_user),
):
    """Query an uploaded dataset with natural language."""
    if not req.query.strip():
        raise HTTPException(400, "Please provide a question")

    result = query_data(req.db_id, req.query)
    if "error" in result:
        raise HTTPException(400, result["error"])

    return result