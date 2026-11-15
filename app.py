import base64
import os
import streamlit as st
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from pydantic import BaseModel, Field
from xml.etree import ElementTree
from pydantic_ai import Agent
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.anthropic import AnthropicProvider
from pydantic_ai.providers.google import GoogleProvider
from pydantic_ai.providers.openai import OpenAIProvider
from dotenv import load_dotenv

# Load variables from .env file
load_dotenv()
market_background = base64.b64encode(
    (Path(__file__).resolve().parent / "assets" / "big-bull-bombay-market-rising.png").read_bytes()
).decode("ascii")

# Page Configuration
st.set_page_config(page_title="The Market Shop", page_icon="📻", layout="wide")
st.markdown(
    """
    <style>
    :root {
        --market-ink: #202b2a;
        --market-paper: #f4f6f2;
        --market-green: #2d7158;
        --market-gold: #c99a35;
        --market-red: #bd4941;
        --market-blue: #456873;
        --market-line: #d8e0db;
    }
    .stApp {
        min-height: 100vh;
        color: #fff;
        background-color: #111;
        background-image:
            linear-gradient(90deg, rgba(9, 15, 17, 0.65) 0%, rgba(9, 15, 17, 0.24) 58%, rgba(9, 15, 17, 0.12) 100%),
            linear-gradient(0deg, rgba(9, 15, 17, 0.78) 0%, rgba(9, 15, 17, 0.08) 68%),
            url("data:image/png;base64,__MARKET_BACKGROUND__");
        background-size: cover;
        background-position: center center;
        background-repeat: no-repeat;
        background-attachment: fixed;
    }
    [data-testid="stHeader"] { background: transparent; }
    .block-container { width: 100%; max-width: none; padding: 0 !important; margin: 0 !important; }
    [data-testid="stSidebar"] {
        background: #e9eeea;
        border-right: 1px solid var(--market-line);
    }
    [data-testid="stSidebar"] * { color: var(--market-ink); }
    h1, h2, h3 { font-family: Georgia, "Times New Roman", serif !important; }
    h1 { color: var(--market-ink) !important; }
    .st-key-market_hero {
        position: relative;
        min-height: 100vh;
        box-sizing: border-box;
        padding: 0;
        color: #fff;
    }
    .st-key-market_hero [data-testid="stElementContainer"]:has([data-testid="stButton"]) {
        position: absolute;
        top: 70%;
        left: 50%;
        width: max-content;
        transform: translateX(-50%);
        z-index: 2;
    }
    .st-key-market_hero div[data-testid="stButton"] {
        position: relative;
        top: auto;
        left: auto;
        width: max-content;
        transform: none;
    }
    .st-key-market_hero div[data-testid="stButton"] > button {
        width: auto;
        min-height: 3.2rem;
        padding: 0.25rem 1.8rem;
        background: rgba(248, 248, 242, 0.22);
        backdrop-filter: blur(14px) saturate(140%);
        -webkit-backdrop-filter: blur(14px) saturate(140%);
        border: 1px solid rgba(255, 255, 255, 0.78);
        border-radius: 999px;
        color: #fff;
        font-weight: 800;
        text-shadow: 0 1px 2px rgba(0, 0, 0, 0.65);
        box-shadow: 0 8px 26px rgba(0, 0, 0, 0.28), inset 0 1px 0 rgba(255, 255, 255, 0.55);
    }
    .st-key-market_hero div[data-testid="stButton"] > button:hover {
        background: rgba(255, 255, 255, 0.38);
        border-color: #fff;
        color: #fff;
        transform: translateY(-1px);
    }
    @media (max-width: 640px) {
        .st-key-market_hero [data-testid="stElementContainer"]:has([data-testid="stButton"]) { top: 72%; }
        .st-key-market_hero div[data-testid="stButton"] > button {
            min-height: 2.9rem;
            padding: 0.2rem 1.1rem;
            font-size: 0.9rem;
        }
    }
    .market-kicker {
        color: var(--market-green);
        font: 700 0.76rem "Courier New", monospace;
        letter-spacing: 0.08em;
        text-transform: uppercase;
    }
    .barber-pole {
        width: 18px;
        height: 46px;
        border: 1px solid #c8d0ca;
        background: repeating-linear-gradient(135deg, var(--market-red) 0 7px, white 7px 14px, var(--market-blue) 14px 21px);
    }
    .station-stamp {
        color: var(--market-red);
        font: 700 0.75rem "Courier New", monospace;
        text-align: right;
    }
    .track-index { color: var(--market-red); font: 700 0.9rem "Courier New", monospace; }
    .on-air-label { color: var(--market-red); font: 700 0.76rem "Courier New", monospace; text-transform: uppercase; }
    .stButton > button[kind="primary"] {
        background: var(--market-green);
        border: 1px solid var(--market-green);
        color: white;
        font-weight: 700;
    }
    .stButton > button[kind="primary"]:hover { background: var(--market-ink); border-color: var(--market-ink); }
    </style>
    """.replace("__MARKET_BACKGROUND__", market_background),
    unsafe_allow_html=True,
)

with st.container(key="market_hero"):
    generate_clicked = st.button("Generate Stock Recommendation", type="primary")

# Sidebar Configuration loading defaults from environment variables securely
st.sidebar.header("Station Controls")
st.sidebar.caption("Choose a model and recipient when you generate a stock pick.")

sender_email = os.getenv("SENDER_EMAIL", "").strip()
sender_pwd = "".join(os.getenv("SENDER_PASSWORD", "").split())

# Web Scraping Helper
class StockRecommendation(BaseModel):
    stock_name: str = Field(description="The Indian-listed company or stock to watch")
    description: str = Field(description="A concise explanation based only on the supplied news headlines")


def scrape_indian_financial_news() -> str:
    headers = {
        "User-Agent": "MarketShop/1.0 (financial headline reader)",
    }
    feeds = (
        ("Mint", "https://www.livemint.com/rss/markets"),
        ("Economic Times", "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms"),
        ("Business Standard", "https://www.business-standard.com/rss/markets-106.rss"),
        ("Hindu BusinessLine", "https://www.thehindubusinessline.com/markets/feeder/default.rss"),
        ("CNBC-TV18", "https://www.cnbctv18.com/commonfeeds/v1/cne/rss/market.xml"),
        ("NDTV Profit", "https://feeds.feedburner.com/ndtvprofit-latest"),
        ("Times of India", "https://timesofindia.indiatimes.com/rssfeeds/1898055.cms"),
        ("News18", "https://www.news18.com/commonfeeds/v1/eng/rss/business.xml"),
    )
    market_terms = (
        "market", "stock", "share", "sensex", "nifty", "ipo", "equity",
        "invest", "finance", "rupee", "earnings", "bank", "gold", "bond",
    )

    def is_relevant(source: str, title: str, link: str) -> bool:
        if source in {"NDTV Profit", "News18"} and "/markets/" in link.lower():
            return True
        searchable = f"{title} {link}".casefold()
        return any(term in searchable for term in market_terms)

    def fetch_feed(feed: tuple[str, str]) -> list[str]:
        source, url = feed
        try:
            response = requests.get(url, headers=headers, timeout=8)
            response.raise_for_status()
            root = ElementTree.fromstring(response.content)
        except (requests.RequestException, ElementTree.ParseError):
            return []

        items = root.findall("./channel/item")
        source_headlines = []
        for item in items:
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            if title and is_relevant(source, title, link):
                source_headlines.append(f"[{source}] {title}")
                if len(source_headlines) == 2:
                    break
        return source_headlines

    headlines = []
    seen_titles = set()
    with ThreadPoolExecutor(max_workers=len(feeds)) as executor:
        for source_headlines in executor.map(fetch_feed, feeds):
            for headline in source_headlines:
                title_key = " ".join(headline.split("] ", 1)[-1].casefold().split())
                if title_key not in seen_titles:
                    seen_titles.add(title_key)
                    headlines.append(headline)

    if headlines:
        return "\n".join(headlines)

    try:
        response = requests.get(
            "https://www.livemint.com/market/stock-market-news",
            headers=headers,
            timeout=8,
        )
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        fallback_headlines = [
            heading.get_text(" ", strip=True)
            for heading in soup.find_all(["h1", "h2", "h3"])
            if len(heading.get_text(strip=True)) > 15
        ][:3]
        return "\n".join(f"[Mint] {headline}" for headline in fallback_headlines) or "No news available."
    except requests.RequestException:
        return "No news available."

def build_stock_agent(provider_name: str):
    if provider_name == "Sarvam":
        provider_api_key = os.getenv("SARVAM_API_KEY", "").strip()
        if not provider_api_key:
            return None, "SARVAM_API_KEY"
        model = OpenAIChatModel(
            "sarvam-105b",
            provider=OpenAIProvider(
                base_url="https://api.sarvam.ai/v1",
                api_key=provider_api_key,
            ),
        )
    elif provider_name == "Claude":
        provider_api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
        if not provider_api_key:
            return None, "ANTHROPIC_API_KEY"
        claude_model_name = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5-5").strip()
        model = AnthropicModel(
            claude_model_name,
            provider=AnthropicProvider(api_key=provider_api_key),
        )
    elif provider_name == "Groq":
        provider_api_key = os.getenv("GROQ_API_KEY", "").strip()
        if not provider_api_key:
            return None, "GROQ_API_KEY"
        groq_model_name = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b").strip()
        model = OpenAIChatModel(
            groq_model_name,
            provider=OpenAIProvider(
                base_url="https://api.groq.com/openai/v1",
                api_key=provider_api_key,
            ),
        )
    else:
        provider_api_key = os.getenv("GOOGLE_API_KEY", "").strip()
        if not provider_api_key:
            return None, "GOOGLE_API_KEY"
        gemini_model_name = os.getenv("GEMINI_MODEL", "gemini-3.8-flash").strip()
        model = GoogleModel(
            gemini_model_name,
            provider=GoogleProvider(api_key=provider_api_key),
        )

    return Agent(
        model,
        output_type=StockRecommendation,
        instructions=(
            "You are an Indian stock analyst. Return one Indian-listed stock to watch and a concise "
            "description based only on the supplied financial-news headlines. Do not invent supporting news. "
            "If the headlines are insufficient, say so in the description."
        ),
    ), None


@st.dialog("Generate a stock pick", width="small")
def generation_dialog():
    with st.form("generation_options"):
        selected_provider = st.selectbox("AI model", ("Sarvam", "Claude", "Groq", "Gemini"))
        recipient_email = st.text_input(
            "Recipient email",
            value=st.session_state.get("recipient_email", os.getenv("RECIPIENT_EMAIL", "")),
        ).strip()
        submitted = st.form_submit_button("Generate recommendation", type="primary")

    if submitted:
        if not recipient_email:
            st.error("Enter a recipient email to continue.")
        else:
            stock_agent, missing_key = build_stock_agent(selected_provider)
            if stock_agent is None:
                st.error(f"Configure {missing_key} in the server environment or Streamlit Secrets.")
            else:
                with st.spinner("Fetching financial headlines..."):
                    headlines = scrape_indian_financial_news()

                if headlines == "No news available." or headlines.startswith("Error scraping:"):
                    st.error(f"Could not fetch financial headlines: {headlines}")
                else:
                    try:
                        with st.spinner(f"Analyzing headlines with {selected_provider}..."):
                            result = stock_agent.run_sync(
                                f"Recommend one stock to watch based only on these headlines:\n{headlines}",
                                model_settings={
                                    "max_tokens": 4096 if selected_provider == "Gemini" else 2048,
                                    "timeout": 45,
                                    "request_timeout": 45,
                                },
                                timeout=60,
                            )
                        st.session_state["recommendation"] = result.output.model_dump()
                        st.session_state["recipient_email"] = recipient_email
                        st.session_state["selected_provider"] = selected_provider
                    except Exception as e:
                        st.error(f"Error generating recommendation: {e}")

    recommendation = st.session_state.get("recommendation")
    if (
        isinstance(recommendation, dict)
        and isinstance(recommendation.get("stock_name"), str)
        and isinstance(recommendation.get("description"), str)
    ):
        st.divider()
        st.markdown('<div class="on-air-label">Stock pick</div>', unsafe_allow_html=True)
        st.subheader(recommendation["stock_name"])
        st.markdown("**Why it made the rotation**")
        st.write(recommendation["description"])

        if st.button("Send Email Report", key="send_email_report_dialog"):
            current_recipient = st.session_state.get("recipient_email", "")
            if not sender_email or not sender_pwd or not current_recipient:
                st.error("Email delivery is not fully configured.")
            else:
                with st.spinner("Sending Email Report..."):
                    message = MIMEMultipart()
                    message["From"] = sender_email
                    message["To"] = current_recipient
                    message["Subject"] = "Daily Stock Advisory Recommendation"
                    body = f"""\
Hello,

Stock: {recommendation['stock_name']}
Why it is on the watchlist: {recommendation['description']}

Best regards,
Your Financial Assistant Agent
"""
                    message.attach(MIMEText(body, "plain"))
                    try:
                        context = ssl.create_default_context()
                        with smtplib.SMTP("smtp.gmail.com", 587, timeout=15) as server:
                            server.ehlo()
                            server.starttls(context=context)
                            server.ehlo()
                            server.login(sender_email, sender_pwd)
                            server.sendmail(sender_email, current_recipient, message.as_string())
                        st.success(f"Gmail accepted the email for delivery to {current_recipient}.")
                    except Exception as e:
                        st.error(f"Failed to send email. Error: {e}")


if generate_clicked:
    generation_dialog()
