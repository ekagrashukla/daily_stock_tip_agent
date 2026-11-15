import base64
import os
import streamlit as st
import requests
from bs4 import BeautifulSoup
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from pydantic import BaseModel, Field
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
    .stApp { background: var(--market-paper); color: var(--market-ink); }
    [data-testid="stHeader"] { background: transparent; }
    .block-container { max-width: 1240px; padding: 0 1.2rem 3rem; }
    [data-testid="stSidebar"] {
        background: #e9eeea;
        border-right: 1px solid var(--market-line);
    }
    [data-testid="stSidebar"] * { color: var(--market-ink); }
    h1, h2, h3 { font-family: Georgia, "Times New Roman", serif !important; }
    h1 { color: var(--market-ink) !important; }
    .st-key-market_hero {
        position: relative;
        min-height: clamp(440px, 68vh, 760px);
        box-sizing: border-box;
        padding: 0;
        color: #fff;
        background-image:
            linear-gradient(90deg, rgba(9, 15, 17, 0.65) 0%, rgba(9, 15, 17, 0.24) 58%, rgba(9, 15, 17, 0.12) 100%),
            linear-gradient(0deg, rgba(9, 15, 17, 0.78) 0%, rgba(9, 15, 17, 0.08) 68%),
            url("data:image/png;base64,__MARKET_BACKGROUND__");
        background-size: cover;
        background-position: center center;
        background-repeat: no-repeat;
        border-bottom: 4px solid var(--market-gold);
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
        color: var(--market-ink);
        font-weight: 800;
        box-shadow: 0 8px 26px rgba(0, 0, 0, 0.28), inset 0 1px 0 rgba(255, 255, 255, 0.55);
    }
    .st-key-market_hero div[data-testid="stButton"] > button:hover {
        background: rgba(255, 255, 255, 0.38);
        border-color: #fff;
        color: var(--market-ink);
        transform: translateY(-1px);
    }
    @media (max-width: 640px) {
        .st-key-market_hero { min-height: 62vh; }
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
    .market-rule { border-top: 2px solid var(--market-green); margin: 0.6rem 0 1.2rem; }
    .market-note { color: #53675f; font-size: 0.96rem; }
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
st.markdown('<div class="market-rule"></div>', unsafe_allow_html=True)
st.markdown('<div class="market-note">Today\'s financial headlines, tuned into one stock to watch.</div>', unsafe_allow_html=True)

# Sidebar Configuration loading defaults from environment variables securely
st.sidebar.header("Station Controls")
selected_provider = st.sidebar.selectbox("AI Provider", ("Sarvam", "Claude", "Groq", "Gemini"))

st.sidebar.subheader("Email Dispatch Configuration")
def_recipient = os.getenv("RECIPIENT_EMAIL", "")

sender_email = os.getenv("SENDER_EMAIL", "").strip()
sender_pwd = "".join(os.getenv("SENDER_PASSWORD", "").split())
recipient_email = st.sidebar.text_input("Recipient Email", value=def_recipient).strip()

# Web Scraping Helper
class StockRecommendation(BaseModel):
    stock_name: str = Field(description="The Indian-listed company or stock to watch")
    description: str = Field(description="A concise explanation based only on the supplied news headlines")


def scrape_indian_financial_news() -> str:
    url = "https://www.livemint.com/market/stock-market-news"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            headings = [h.get_text().strip() for h in soup.find_all(['h1', 'h2', 'h3']) if len(h.get_text().strip()) > 15][:3]
            return "\n".join(headings)
    except Exception as e:
        return f"Error scraping: {str(e)}"
    return "No news available."

# Initialize AI Agent
if selected_provider == "Sarvam":
    provider_api_key = os.getenv("SARVAM_API_KEY", "").strip()
    if provider_api_key:
        model = OpenAIChatModel(
            "sarvam-105b",
            provider=OpenAIProvider(
                base_url="https://api.sarvam.ai/v1",
                api_key=provider_api_key,
            ),
        )
    else:
        model = None
        st.warning("Configure SARVAM_API_KEY in the server environment or Streamlit Secrets.")
elif selected_provider == "Claude":
    provider_api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if provider_api_key:
        claude_model_name = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5-5").strip()
        model = AnthropicModel(
            claude_model_name,
            provider=AnthropicProvider(api_key=provider_api_key),
        )
    else:
        model = None
        st.warning("Configure ANTHROPIC_API_KEY in the server environment or Streamlit Secrets.")
elif selected_provider == "Groq":
    provider_api_key = os.getenv("GROQ_API_KEY", "").strip()
    if provider_api_key:
        groq_model_name = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b").strip()
        model = OpenAIChatModel(
            groq_model_name,
            provider=OpenAIProvider(
                base_url="https://api.groq.com/openai/v1",
                api_key=provider_api_key,
            ),
        )
    else:
        model = None
        st.warning("Configure GROQ_API_KEY in the server environment or Streamlit Secrets.")
else:
    provider_api_key = os.getenv("GOOGLE_API_KEY", "").strip()
    if provider_api_key:
        gemini_model_name = os.getenv("GEMINI_MODEL", "gemini-3.8-flash").strip()
        model = GoogleModel(
            gemini_model_name,
            provider=GoogleProvider(api_key=provider_api_key),
        )
    else:
        model = None
        st.warning("Configure GOOGLE_API_KEY in the server environment or Streamlit Secrets.")

if model:
    stock_agent = Agent(
        model,
        output_type=StockRecommendation,
        instructions=(
            "You are an Indian stock analyst. Return one Indian-listed stock to watch and a concise "
            "description based only on the supplied financial-news headlines. Do not invent supporting news. "
            "If the headlines are insufficient, say so in the description."
        )
    )
else:
    stock_agent = None

# Trigger Execution
if generate_clicked:
    if not stock_agent:
        st.error("Agent is not initialized due to missing API Key.")
    else:
        with st.spinner("Fetching financial headlines..."):
            headlines = scrape_indian_financial_news()

        if headlines == "No news available." or headlines.startswith("Error scraping:"):
            st.error(f"Could not fetch financial headlines: {headlines}")
        else:
            st.session_state['headlines'] = [line.strip() for line in headlines.splitlines() if line.strip()]
            try:
                with st.spinner(f"Analyzing headlines with {selected_provider}..."):
                    result = stock_agent.run_sync(
                        f"Recommend one stock to watch based only on these headlines:\n{headlines}",
                        model_settings={
                            "max_tokens": 512,
                            "timeout": 45,
                            "request_timeout": 45,
                        },
                        timeout=60,
                    )
                    st.session_state['recommendation'] = result.output
                st.success("Recommendation Generated!")
            except Exception as e:
                st.error(f"Error generating recommendation: {e}")

# Show recommendation if exists
if 'headlines' in st.session_state:
    st.markdown('<div class="market-kicker">Today\'s rotation / headlines</div>', unsafe_allow_html=True)
    for index, headline in enumerate(st.session_state['headlines'], start=1):
        with st.container(border=True):
            number_column, headline_column = st.columns([0.35, 5])
            with number_column:
                st.markdown(f'<div class="track-index">{index:02d}</div>', unsafe_allow_html=True)
            with headline_column:
                st.write(headline)

if (
    'recommendation' in st.session_state
    and not isinstance(st.session_state['recommendation'], StockRecommendation)
):
    del st.session_state['recommendation']

if 'recommendation' in st.session_state:
    recommendation = st.session_state['recommendation']
    with st.container(border=True):
        st.markdown('<div class="on-air-label">Now playing / stock pick</div>', unsafe_allow_html=True)
        st.subheader(recommendation.stock_name)
        st.markdown("**Why it made the rotation**")
        st.write(recommendation.description)

    # Send Email Option
    if st.button("Send Email Report"):
        if not sender_email or not sender_pwd or not recipient_email:
            st.error("Please configure sender/recipient details in the sidebar.")
        else:
            with st.spinner("Sending Email..."):
                # Construct the email content
                msg = MIMEMultipart()
                msg['From'] = sender_email
                msg['To'] = recipient_email
                msg['Subject'] = "Daily Stock Advisory Recommendation"

                body = f"""\
Hello,

Here is your requested stock recommendation based on the latest Indian financial news:

Stock: {recommendation.stock_name}
Why it is on the watchlist: {recommendation.description}

Best regards,
Your Financial Assistant Agent
"""
                msg.attach(MIMEText(body, 'plain'))

                try:
                    context = ssl.create_default_context()
                    with smtplib.SMTP("smtp.gmail.com", 587, timeout=15) as server:
                        server.ehlo()
                        server.starttls(context=context)
                        server.ehlo()
                        server.login(sender_email, sender_pwd)
                        server.sendmail(sender_email, recipient_email, msg.as_string())
                    st.success(
                        f"Gmail accepted the email for delivery to {recipient_email}. "
                        "Check Spam or Promotions if it is not in the inbox."
                    )
                except Exception as e:
                    st.error(f"Failed to send email. Error: {e}")
