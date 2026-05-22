"""
ai_service.py
  - Text generation: Google Gemini 1.5 Flash (free tier)
  - Image generation: Pollinations.ai (completely free, no API key)
"""

import asyncio
import logging
import urllib.parse
from io import BytesIO

import aiohttp

from config import GEMINI_API_KEY

logger = logging.getLogger(__name__)

GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-1.5-flash:generateContent?key={key}"
)


# ── Text generation (Gemini) ──────────────────────────────────────────────────

async def generate_post_text(examples: list[dict]) -> str:
    """
    Takes stored example posts and asks Gemini to write a new post
    in the same style, tone, and format.
    """
    if not GEMINI_API_KEY:
        return "⚠️ GEMINI_API_KEY not set. Add it to your .env file."

    # Build context from examples
    examples_block = "\n\n---\n\n".join(
        f"Example {i+1}:\n{ex['text']}" for i, ex in enumerate(examples[:5])
    )

    prompt = f"""You are a social media content writer. Study these example posts carefully:

{examples_block}

Now write ONE new post that:
- Matches the exact tone, voice, and style of the examples
- Is engaging, authentic, and feels natural (not AI-generated)
- Has similar length and formatting to the examples
- Does NOT start with "Here is" or any meta-commentary
- Includes relevant emojis if the examples do

Write only the post text. Nothing else."""

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.9,
            "maxOutputTokens": 1024,
        },
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                GEMINI_URL.format(key=GEMINI_API_KEY),
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                data = await resp.json()
                return data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception as e:
        logger.error(f"Gemini error: {e}")
        return f"⚠️ AI text generation failed: {e}"


# ── Image generation (Pollinations.ai) ───────────────────────────────────────

async def generate_post_image(post_text: str) -> bytes | None:
    """
    Generates an image for the post using Pollinations.ai.
    Completely free — no API key required.
    Returns image bytes or None on failure.
    """
    # Create a concise visual prompt from the post text
    image_prompt = await _make_image_prompt(post_text)
    encoded = urllib.parse.quote(image_prompt)
    url = f"https://image.pollinations.ai/prompt/{encoded}?width=1024&height=1024&nologo=true&enhance=true"

    logger.info(f"Generating image with prompt: {image_prompt[:80]}...")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                timeout=aiohttp.ClientTimeout(total=60),
            ) as resp:
                if resp.status == 200:
                    return await resp.read()
                logger.warning(f"Pollinations returned {resp.status}")
                return None
    except Exception as e:
        logger.error(f"Image generation error: {e}")
        return None


async def _make_image_prompt(post_text: str) -> str:
    """Ask Gemini to create a good image prompt for the post."""
    if not GEMINI_API_KEY:
        # Fallback: use first 100 chars of post as prompt
        return f"high quality photo, {post_text[:100]}, professional photography"

    payload = {
        "contents": [{
            "parts": [{
                "text": (
                    f"Write a short image generation prompt (max 20 words) for this post:\n\n{post_text}\n\n"
                    "The prompt should describe a visual scene that represents the post. "
                    "Make it vivid and specific. Return ONLY the prompt, nothing else."
                )
            }]
        }],
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 100},
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                GEMINI_URL.format(key=GEMINI_API_KEY),
                json=payload,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                data = await resp.json()
                prompt = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                return f"{prompt}, high quality, professional"
    except Exception:
        return f"high quality photo, {post_text[:80]}, professional photography"
