"""
Darwin Enterprise Evolve Beta — Podcast Audio Service
Uses NotebookLM to generate actual audio podcasts from transcript text.
"""
import asyncio
import os
import uuid
import tempfile
from notebooklm import NotebookLMClient


async def generate_podcast_audio(transcript: str, title: str = "HMI Research") -> str:
    """
    Create a NotebookLM notebook, add transcript as source,
    generate audio overview, download MP3.
    Returns path to the MP3 file.
    """
    async with await NotebookLMClient.from_storage() as client:
        nb = await client.notebooks.create(f"Research Room - {title}")
        await client.sources.add_text(nb.id, "Research Room Podcast Transcript", transcript, wait=True)

        status = await client.artifacts.generate_audio(
            nb.id,
            instructions="Turn this into an engaging, conversational podcast between two hosts discussing automotive HMI research. Keep it natural and informative.",
        )
        await client.artifacts.wait_for_completion(nb.id, status.task_id)

        output_dir = os.path.join(tempfile.gettempdir(), "darwin_podcasts")
        os.makedirs(output_dir, exist_ok=True)
        filename = f"podcast_{uuid.uuid4().hex[:8]}.mp3"
        filepath = os.path.join(output_dir, filename)

        await client.artifacts.download_audio(nb.id, filepath)
        return filepath