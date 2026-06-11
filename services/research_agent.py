"""
Darwin Enterprise Evolve Beta — Research Agent Service
arXiv paper search, relevance scoring, newsletter + podcast generation via Claude.
"""
import os
import re
import time
import random
import datetime
import arxiv
import anthropic
from typing import List, Tuple

AUTOMOTIVE_KEYWORDS = ['automotive', 'vehicle', 'car', 'driving', 'driver', 'cockpit']
HMI_KEYWORDS = ['hmi', 'human-machine interface', 'user interface', 'voice', 'display']

QUERY_EXPANSIONS = {
    'hmi': 'HMI OR "human machine interface" OR "human-machine interface"',
    'voice interface': '"voice interface" OR "speech recognition" OR "voice control"',
    'automotive ai': 'automotive AND ("artificial intelligence" OR "machine learning")',
}


def _get_anthropic_client():
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    return anthropic.Anthropic(api_key=api_key)


def _score_paper(paper) -> int:
    score = 0
    combined = (paper.title + " " + paper.summary).lower()
    for kw in AUTOMOTIVE_KEYWORDS:
        if kw in combined:
            score += 10
    for kw in HMI_KEYWORDS:
        if kw in combined:
            score += 8
    return score


def _expand_query(natural_query: str) -> str:
    topics = [t.strip().lower() for t in natural_query.split(',')]
    expanded = []
    for topic in topics:
        if topic in QUERY_EXPANSIONS:
            expanded.append(f"({QUERY_EXPANSIONS[topic]})")
        else:
            expanded.append(f'"{topic}"')
    return ' OR '.join(expanded)


def _fetch_papers(query: str, max_results: int = 50) -> List:
    client = arxiv.Client()
    search = arxiv.Search(query=query, max_results=max_results, sort_by=arxiv.SortCriterion.Relevance)
    for attempt in range(3):
        try:
            results = list(client.results(search))
            return results
        except Exception:
            if attempt < 2:
                time.sleep((attempt + 1) * 5 + random.uniform(1, 3))
    return []


def _generate_newsletter(top_papers: List[Tuple[int, object]], anthropic_client) -> str:
    date = datetime.date.today()
    lines = [
        "🚗 RESEARCH ROOM NEWSLETTER",
        "=" * 60,
        f"📅 {date}",
        "=" * 60,
    ]
    for i, (score, paper) in enumerate(top_papers, 1):
        lines.append(f"\n📄 PAPER {i}/5 — RELEVANCE SCORE: {score}")
        lines.append("─" * 50)
        lines.append(f"🏷️ Title: {paper.title}")
        lines.append(f"📅 Published: {paper.published.strftime('%Y-%m-%d')}")
        authors = ', '.join(a.name for a in paper.authors)
        lines.append(f"👥 Authors: {authors}")
        try:
            msg = anthropic_client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4000,
                messages=[{"role": "user", "content": f"""Provide a concise newsletter-style summary of this research paper.
Focus on how it could help an automotive R&D team working on HMI systems.

Title: {paper.title}
Abstract: {paper.summary}

Provide:
1. Brief summary (2-3 sentences)
2. Key takeaways for automotive teams (bullet points)"""}]
            )
            summary = msg.content[0].text
            summary = re.sub(r'#+\s*', '', summary)
            summary = re.sub(r'\*\*(.*?)\*\*', r'\1', summary)
            summary = re.sub(r'\*(.*?)\*', r'\1', summary)
            lines.append(f"\n💡 Summary & Insights:\n{summary}")
        except Exception as e:
            lines.append(f"\n📄 Abstract: {paper.summary[:500]}...")
        lines.append(f"\n🔗 arXiv Link: {paper.entry_id}")
        lines.append("=" * 60)
    return "\n".join(lines)


def _generate_podcast(top_papers: List[Tuple[int, object]], anthropic_client) -> str:
    date = datetime.date.today()
    papers_summary = []
    for i, (score, paper) in enumerate(top_papers, 1):
        authors = ', '.join(a.name for a in paper.authors)
        papers_summary.append(f"Paper {i}: {paper.title} by {authors}")
    prompt = f"""Create a 10-minute podcast transcript for "The Research Room" covering latest research relevant to automotive HMI and AI teams.

Today's date: {date}

This week's top 5 research papers:
{chr(10).join(papers_summary)}

Format as a natural but humorous podcast conversation between Host1 and Host2 with detailed discussion of each paper. Focus on actionable insights for automotive R&D teams."""
    try:
        msg = anthropic_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=3000,
            messages=[{"role": "user", "content": prompt}]
        )
        transcript = msg.content[0].text
        return f"""🎙️ THE RESEARCH ROOM PODCAST TRANSCRIPT
📅 Episode Date: {date}
{"=" * 80}

{transcript}

{"=" * 80}
🎙️ END OF TRANSCRIPT"""
    except Exception as e:
        return f"Error generating podcast: {e}"


def generate_research(query_text: str, max_papers: int = 50) -> dict:
    expanded = _expand_query(query_text)
    papers = _fetch_papers(expanded, max_papers)
    scored = [(_score_paper(p), p) for p in papers]
    scored.sort(key=lambda x: x[0], reverse=True)
    top5 = scored[:5]
    anthropic_client = _get_anthropic_client()
    newsletter = _generate_newsletter(top5, anthropic_client)
    podcast = _generate_podcast(top5, anthropic_client)
    paper_metadata = []
    for score, paper in top5:
        pdf_url = paper.entry_id.replace("/abs/", "/pdf/") + ".pdf"
        paper_metadata.append({
            "title": paper.title,
            "authors": [a.name for a in paper.authors],
            "published": paper.published.strftime('%Y-%m-%d'),
            "score": score,
            "url": paper.entry_id,
            "pdf_url": pdf_url,
            "summary": paper.summary[:300],
        })
    return {
        "query": query_text,
        "expanded_query": expanded,
        "papers_searched": len(papers),
        "top_papers": paper_metadata,
        "newsletter": newsletter,
        "podcast": podcast,
    }