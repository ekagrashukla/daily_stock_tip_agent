import os
import streamlit as st
import requests
from bs4 import BeautifulSoup
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from dotenv import load_dotenv

# Load variables from .env file
load_dotenv()

# Page Configuration
st.set_page_config(page_title="Indian Stock Advisor", page_icon="📈", layout="centered")
st.title("📈 Indian Stock Market Analyst & Advisor")
st.write("Scrape the latest financial headlines, analyze them using AI, and email the recommendations!")

# Sidebar Configuration loading defaults from environment variables securely
st.sidebar.header("Configuration")
sarvam_api_key = os.getenv("SARVAM_API_KEY", "").strip()

st.sidebar.subheader("Email Dispatch Configuration")
def_recipient = os.getenv("RECIPIENT_EMAIL", "")

sender_email = os.getenv("SENDER_EMAIL", "").strip()
sender_pwd = "".join(os.getenv("SENDER_PASSWORD", "").split())
recipient_email = st.sidebar.text_input("Recipient Email", value=def_recipient).strip()

# Web Scraping Helper
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
if sarvam_api_key:
    model = OpenAIChatModel(
        "sarvam-105b",
        provider=OpenAIProvider(
            base_url="https://api.sarvam.ai/v1",
            api_key=sarvam_api_key,
        ),
    )
    stock_agent = Agent(
        model,
        tools=[scrape_indian_financial_news],
        instructions=(
            "You are an Indian Stock Analyst. Call scrape_indian_financial_news once. "
            "Provide a one-sentence recommendation of one stock to watch based ONLY on the headings found."
        )
    )
else:
    st.warning("Configure SARVAM_API_KEY in the server environment or Streamlit Secrets.")
    stock_agent = None

# Trigger Execution
if st.button("Generate Stock Recommendation", type="primary"):
    if not stock_agent:
        st.error("Agent is not initialized due to missing API Key.")
    else:
        with st.spinner("Scraping news and running analysis..."):
            try:
                result = stock_agent.run_sync(
                    "Find news and recommend a stock in a single short sentence.",
                    model_settings={"max_tokens": 2048}
                )
                st.session_state['recommendation'] = result.output
                st.success("Recommendation Generated!")
            except Exception as e:
                st.error(f"Error generating recommendation: {e}")

# Show recommendation if exists
if 'recommendation' in st.session_state:
    st.info("### AI Stock Recommendation")
    st.markdown(st.session_state['recommendation'])

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

{st.session_state['recommendation']}

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
