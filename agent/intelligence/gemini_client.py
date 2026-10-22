import json
import logging
import os
from typing import Dict, Any, Optional
from google import genai
from google.genai import types
from ..core.config import settings

logger = logging.getLogger("ai_seo.intelligence.gemini")

class GeminiSEOClient:
    """
    Wrapper for Google GenAI SDK (Gemini 2.5 / Flash / Pro)
    Provides structured SEO reasoning, keyword clustering, and content optimization.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.gemini_api_key or os.getenv("GEMINI_API_KEY", "")
        self.model_name = settings.gemini_model or "gemini-2.5-flash"
        self._client: Optional[genai.Client] = None

    def _get_client(self) -> Optional[genai.Client]:
        if not self._client and self.api_key:
            try:
                self._client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.error(f"Failed to initialize Gemini GenAI client: {e}")
        return self._client

    async def generate_json(self, prompt: str, system_instruction: str = "") -> Optional[Dict[str, Any]]:
        """
        Sends prompt to Gemini and expects a structured JSON object response.
        """
        client = self._get_client()
        if not client:
            logger.info("Gemini API key not configured. Using deterministic SEO heuristics.")
            return None

        try:
            config = types.GenerateContentConfig(
                response_mime_type="application/json",
                system_instruction=system_instruction or "You are an expert Autonomous Technical SEO Specialist."
            )
            response = client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=config
            )
            if response and response.text:
                return json.loads(response.text)
        except Exception as e:
            logger.warning(f"Gemini API call failed: {e}")
        return None

    async def rewrite_meta_tags(self, page_title: str, current_desc: str, page_content: str, target_keyword: str) -> Dict[str, str]:
        """
        Generates high-CTR, SEO-optimized title tag and meta description.
        """
        prompt = f"""
        Optimize the meta tags for the following web page:
        Target Keyword: {target_keyword}
        Current Title: {page_title}
        Current Description: {current_desc}
        Page Content Snippet: {page_content[:1500]}

        Return JSON format:
        {{
            "optimized_title": "Descriptive title between 45 and 60 characters with primary keyword near front",
            "optimized_description": "Compelling call-to-action meta description between 130 and 155 characters",
            "h1_suggestion": "Impactful H1 heading",
            "rationale": "Brief reasoning for the changes"
        }}
        """
        result = await self.generate_json(prompt)
        if result and "optimized_title" in result:
            return result
        
        # Fallback heuristic if API key is not yet set
        kw_title = f"{target_keyword.title()} - {page_title}".strip(" - ")[:60]
        kw_desc = f"Discover everything about {target_keyword}. Explore our expert insights, tips, and comprehensive solutions today."[:155]
        return {
            "optimized_title": kw_title,
            "optimized_description": kw_desc,
            "h1_suggestion": target_keyword.title(),
            "rationale": "Heuristic fallback: Primary keyword inserted into title and meta description."
        }
