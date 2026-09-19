from langchain.tools import tool 
import requests
from dotenv import load_dotenv
import os
from tavily import TavilyClient
from bs4 import BeautifulSoup
import re 

load_dotenv()

# Optional extraction libraries
try:
    import trafilatura
except ImportError:
    trafilatura = None

try:
    from readability import Document
except ImportError:
    Document = None

tavily_api_key = os.getenv("TAVILY_API_KEY")
tavily = TavilyClient(api_key=tavily_api_key) if tavily_api_key else None

@tool
def web_search(query: str) -> str:
    """Search the web for recent and reliable information on a topic. Returns Titles, URLs and snippets."""
    if not tavily:
        return "Tavily API key is not set. Please provide a valid TAVILY_API_KEY in .env."
    
    results = tavily.search(query=query, max_results=5)

    out = []
    for r in results.get('results', []):
        out.append(
            f"Title: {r.get('title', '')}\nURL: {r.get('url', '')}\nSnippet: {r.get('content', '')[:300]}\n"
        )
    
    return "\n----\n".join(out) if out else "No search results found."

@tool
def scrape_url(url: str) -> str:
    """
    Scrape and extract clean readable content from a URL.
    Uses multiple extraction strategies for better reliability.
    """

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.google.com/",
    }

    try:
        # ── Fetch page ─────────────────────────────────────
        response = requests.get(
            url,
            headers=headers,
            timeout=15
        )

        response.raise_for_status()
        html = response.text

        # ──────────────────────────────────────────────────
        # Strategy 1 → trafilatura (if available)
        # ──────────────────────────────────────────────────
        if trafilatura is not None:
            extracted = trafilatura.extract(
                html,
                include_comments=False,
                include_tables=False
            )
            if extracted and len(extracted.strip()) > 200:
                cleaned = re.sub(r'\s+', ' ', extracted)
                return cleaned[:5000]

        # ──────────────────────────────────────────────────
        # Strategy 2 → readability (if available)
        # ──────────────────────────────────────────────────
        if Document is not None:
            doc = Document(html)
            clean_html = doc.summary()
            soup = BeautifulSoup(clean_html, "html.parser")

            for tag in soup([
                "script", "style", "nav", "footer", "header", "aside", "form"
            ]):
                tag.decompose()

            text = soup.get_text(separator=" ", strip=True)
            if text and len(text.strip()) > 200:
                cleaned = re.sub(r'\s+', ' ', text)
                return cleaned[:5000]

        # ──────────────────────────────────────────────────
        # Strategy 3 → BeautifulSoup fallback
        # ──────────────────────────────────────────────────
        soup = BeautifulSoup(html, "html.parser")

        for tag in soup([
            "script", "style", "nav", "footer", "header", "aside", "form"
        ]):
            tag.decompose()

        text = soup.get_text(separator=" ", strip=True)
        cleaned = re.sub(r'\s+', ' ', text)

        if cleaned and len(cleaned.strip()) > 50:
            return cleaned[:5000]

        return "Could not extract meaningful content from the page."

    except requests.exceptions.Timeout:
        return "Request timed out while scraping the URL."

    except requests.exceptions.HTTPError as e:
        return f"HTTP error occurred: {str(e)}"

    except Exception as e:
        return f"Could not scrape URL: {str(e)}"