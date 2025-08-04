import streamlit as st
import requests
from newspaper import Article
from urllib.parse import urlparse

# ---------------- Step 1: Validate Full URL Format ----------------
def is_valid_url(url):
    try:
        parsed = urlparse(url)
        return (
            parsed.scheme in ["http", "https"] and
            parsed.netloc and
            "." in parsed.netloc and
            len(parsed.netloc) > 4  # Avoid "https://d" or similar
        )
    except:
        return False

# ---------------- Step 2: Check if URL is Reachable ----------------
def is_url_reachable(url):
    try:
        response = requests.head(url, allow_redirects=True, timeout=5)
        return response.status_code < 400
    except:
        return False

# ---------------- Step 3: Trust Check via Google Safe Browsing ----------------
def is_site_trustworthy(url, api_key):
    endpoint = f"https://safebrowsing.googleapis.com/v4/threatMatches:find?key={api_key}"
    body = {
        "client": {
            "clientId": "job-form-analyzer",
            "clientVersion": "1.0"
        },
        "threatInfo": {
            "threatTypes": [
                "MALWARE", "SOCIAL_ENGINEERING", "UNWANTED_SOFTWARE", "POTENTIALLY_HARMFUL_APPLICATION"
            ],
            "platformTypes": ["ANY_PLATFORM"],
            "threatEntryTypes": ["URL"],
            "threatEntries": [{"url": url}]
        }
    }
    try:
        response = requests.post(endpoint, json=body)
        response.raise_for_status()
        result = response.json()
        return not bool(result.get("matches"))
    except Exception as e:
        st.warning(f"⚠ Trust check failed: {e}")
        return False

# ---------------- Step 4: Check if Page is Job-Related ----------------
def is_job_related(text):
    job_keywords = ["job", "career", "hiring", "opening", "vacancy", "recruitment", "apply now","fresher"]
    return any(kw in text.lower() for kw in job_keywords)

# ---------------- Step 5: Extract Page Text ----------------
def extract_text_from_url(url):
    try:
        article = Article(url)
        article.download()
        article.parse()
        return article.text
    except Exception as e:
        return f"❌ Failed to extract text: {e}"

# ---------------- Step 6: Analyze Form Fields ----------------
def analyze_form_content(text):
    text = text.lower()

    short_keywords = ["name", "email", "mobile", "upload resume", "upload cv"]
    medium_keywords = ["address", "education", "experience", "linkedin", "photo"]
    long_keywords = ["references", "essay", "why should", "motivation", "detailed"]

    score = sum(1 for kw in short_keywords if kw in text)
    score += sum(2 for kw in medium_keywords if kw in text)
    score += sum(3 for kw in long_keywords if kw in text)

    if score <= 5:
        time_category = "🟢 Short (2–5 mins)"
    elif score <= 10:
        time_category = "🟠 Medium (5–10 mins)"
    else:
        time_category = "🔴 Long (10+ mins)"

    # Documents
    doc_keywords = ["resume", "cv", "photo", "pan card", "aadhaar", "id proof", "passport", "cover letter"]
    required_docs = [doc.title() for doc in doc_keywords if doc in text]

    # UPI or QR code detection
    has_qr_or_upi = any(keyword in text for keyword in ["upi", "qr code", "scan to pay", "gpay", "paytm"])

    return time_category, required_docs, has_qr_or_upi

# ---------------- Streamlit App ----------------
st.set_page_config(page_title="Job Portal Analyzer", layout="centered")
st.title("🔍 Job Portal Analyzer")

st.markdown("### What This App Does:")
st.markdown("- ✅ Validates job portal URL")
st.markdown("- 🔐 Checks if the site is **trustworthy**")
st.markdown("- 🔗 Ensures the link is reachable")
st.markdown("- ⏱ Estimates time to fill the form")
st.markdown("- 📄 Lists required documents")
st.markdown("- 👀 Verifies job-related keywords")

url = st.text_input("🔗 Enter Job Portal URL")

GOOGLE_API_KEY = "AIzaSyBHQqDgO3lfBW4bN5vVIcHuYGpsiLJN6T4"  # Replace with your real API key

if url:
    if not is_valid_url(url):
        st.error("❌ Invalid URL. Make sure it starts with http:// or https:// and has a valid domain.")
    elif not is_url_reachable(url):
        st.error("❌ This site is unreachable. Please check the link.")
    else:
        st.info("🔐 Checking site trustworthiness...")
        is_trusted = is_site_trustworthy(url, GOOGLE_API_KEY)

        if not is_trusted:
            st.error("⚠️ This site may be unsafe. Proceed with caution.")
        else:
            st.success("✅ Site appears to be safe.")

            st.info("📄 Extracting job content...")
            text = extract_text_from_url(url)

            if text.startswith("❌"):
                st.error(text)
            else:
                if is_job_related(text):
                    st.success("💼 Page appears job-related.")

                    time_needed, required_docs, found_upi = analyze_form_content(text)

                    st.subheader("⏱ Estimated Time to Fill Form")
                    st.write(time_needed)

                    st.subheader("📎 Documents Required")
                    if required_docs:
                        st.write(", ".join(required_docs))
                    else:
                        st.write("Not clearly mentioned")
                else:
                    st.warning("⚠️ This page may not be job-related. Time estimation skipped.")

                with st.expander("📜 View Extracted Page Text"):
                    st.text(text)
