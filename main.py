import streamlit as st
import pandas as pd
import time
import logging
from utils import scrape_linkedin_profile, is_valid_linkedin_url

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="LinkedIn Profile Scraper",
    page_icon="📊",
    layout="wide"
)

# Load custom CSS
with open('styles.css') as f:
    st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

# App title and description
st.title("LinkedIn Profile Scraper")
st.markdown("""
    Extract professional information from LinkedIn profiles.
    Simply paste a LinkedIn profile URL below to get started.

    **Note:** This tool works best with public LinkedIn profiles.
    Some profiles may be inaccessible due to privacy settings.
""")

# URL input
url = st.text_input(
    "Enter LinkedIn Profile URL",
    placeholder="https://www.linkedin.com/in/username"
)

if url:
    if not is_valid_linkedin_url(url):
        st.error("Please enter a valid LinkedIn profile URL (e.g., https://www.linkedin.com/in/username)")
        st.info("Make sure the URL follows the correct format and points to a LinkedIn profile.")
    else:
        try:
            with st.spinner("Fetching profile data... Please wait while we process your request."):
                logger.info(f"Starting profile extraction for URL: {url}")

                # Progress bar
                progress_bar = st.progress(0)
                progress_text = st.empty()

                # Simulation of progress for better UX
                progress_text.text("Initializing scraper...")
                progress_bar.progress(10)
                time.sleep(0.5)

                progress_text.text("Requesting profile data...")
                progress_bar.progress(30)
                time.sleep(0.5)

                # Actual scraping
                profile_data = scrape_linkedin_profile(url)

                progress_text.text("Processing extracted data...")
                progress_bar.progress(70)
                time.sleep(0.5)

                progress_text.text("Finalizing results...")
                progress_bar.progress(100)
                time.sleep(0.5)

                # Clear progress indicators
                progress_bar.empty()
                progress_text.empty()

            if profile_data:
                st.success("✅ Profile data retrieved successfully!")

                # Create expandable sections for different parts
                with st.expander("📋 Basic Information", expanded=True):
                    col1, col2 = st.columns(2)

                    with col1:
                        if 'name' in profile_data:
                            st.markdown(f"### {profile_data['name']}")
                        if 'headline' in profile_data:
                            st.markdown(f"**{profile_data['headline']}**")
                        if 'about' in profile_data:
                            st.markdown("### About")
                            st.markdown(profile_data['about'])

                    with col2:
                        if 'languages' in profile_data:
                            st.markdown("### Languages")
                            for lang in profile_data['languages']:
                                st.markdown(f"• {lang}")

                with st.expander("💼 Professional Experience", expanded=True):
                    if 'experience' in profile_data:
                        for exp in profile_data['experience']:
                            st.markdown(f"• {exp}")
                    else:
                        st.info("No experience information found")

                with st.expander("🎓 Education", expanded=True):
                    if 'education' in profile_data:
                        for edu in profile_data['education']:
                            st.markdown(f"• {edu}")
                    else:
                        st.info("No education information found")

                with st.expander("🔧 Skills", expanded=True):
                    if 'skills' in profile_data:
                        for skill in profile_data['skills']:
                            st.markdown(f"• {skill}")
                    else:
                        st.info("No skills information found")

                # Export options
                st.markdown("---")
                st.subheader("📥 Export Options")

                df = pd.DataFrame([profile_data])
                col1, col2 = st.columns(2)

                with col1:
                    csv = df.to_csv(index=False)
                    st.download_button(
                        label="Download as CSV",
                        data=csv,
                        file_name="linkedin_profile.csv",
                        mime="text/csv",
                        help="Download the profile data in CSV format"
                    )

                with col2:
                    json_str = df.to_json(orient='records')
                    st.download_button(
                        label="Download as JSON",
                        data=json_str,
                        file_name="linkedin_profile.json",
                        mime="application/json",
                        help="Download the profile data in JSON format"
                    )

        except Exception as e:
            logger.error(f"Error occurred: {str(e)}")
            error_message = str(e).lower()

            if "rate limit" in error_message:
                st.error("⚠️ LinkedIn is temporarily blocking requests. Please try again in a few minutes.")
            elif "private" in error_message:
                st.error("🔒 This profile appears to be private or requires authentication.")
            elif "not found" in error_message:
                st.error("❌ Profile not found. Please check if the URL is correct.")
            elif "access denied" in error_message:
                st.error("🚫 Unable to access the profile. LinkedIn may be blocking automated access.")
            else:
                st.error(f"❌ An error occurred: {str(e)}")

            st.info("""
            **Troubleshooting Tips:**
            - Verify that the profile is public and accessible
            - Double-check the URL format
            - Try again in a few minutes
            - If the issue persists, try a different profile
            """)

# Footer
st.markdown("""
---
**Note:** Please use this tool responsibly and in accordance with LinkedIn's terms of service.
""")