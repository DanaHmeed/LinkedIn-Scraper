import time
import logging
import requests
from bs4 import BeautifulSoup
from typing import Dict, List
import re
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def is_valid_linkedin_url(url: str) -> bool:
    """Validate LinkedIn URL format."""
    linkedin_pattern = r'^https?:\/\/(www\.)?linkedin\.com\/in\/[a-zA-Z0-9\-]+\/?$'
    return bool(re.match(linkedin_pattern, url))

def create_session() -> requests.Session:
    """Create a requests session with retry logic."""
    session = requests.Session()

    # Configure retry strategy
    retry_strategy = Retry(
        total=3,  # number of retries
        backoff_factor=2,  # exponential backoff
        status_forcelist=[429, 500, 502, 503, 504]
    )

    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    # Set headers to mimic a regular browser
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'cross-site',
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache'
    })

    return session

import random

def exponential_backoff(retries):
    for i in range(retries):
        time.sleep((2 ** i) + random.uniform(0, 1))
        # Retry logic

def extract_profile_data(url: str) -> Dict:
    """Extract profile data from LinkedIn public profile."""
    logger.info(f"Starting to extract profile data from: {url}")

    try:
        session = create_session()

        # Add referrer to appear more legitimate
        session.headers.update({
            'Referer': 'https://www.google.com/search?q=linkedin+profile'
        })

        # Get the profile page
        logger.info("Sending request to LinkedIn...")
        response = session.get(url, timeout=30)

        # Log response details for debugging
        logger.info(f"Response status code: {response.status_code}")
        logger.info(f"Response headers: {dict(response.headers)}")

        if response.status_code == 999:
            logger.info("LinkedIn's security system has blocked the request. Trying with Selenium...")
            return get_profile_data_with_selenium(url)

        response.raise_for_status()

        # Check response content
        content_length = len(response.text)
        logger.info(f"Response content length: {content_length}")

        if content_length < 1000:
            logger.error("Response too short, likely not a valid profile page")
            raise Exception("Invalid response content")

        # Parse HTML content
        soup = BeautifulSoup(response.text, 'html.parser')

        # Check for error pages
        error_indicators = ["captcha", "please verify", "interrupted", "unavailable"]
        page_text = soup.get_text().lower()
        for indicator in error_indicators:
            if indicator in page_text:
                logger.error(f"Found error indicator: {indicator}")
                raise Exception(f"Access restricted: {indicator} check required")

        profile_data = {}

        # Extract name (multiple selectors for different page versions)
        name_found = False
        for selector in ['h1.text-heading-xlarge', 'h1.top-card-layout__title', 'h1.basic-info__name']:
            if name_found:
                break
            name_elem = soup.select_one(selector)
            if name_elem and name_elem.text.strip():
                profile_data['name'] = name_elem.text.strip()
                name_found = True
                logger.info(f"Found name using selector: {selector}")

        # Extract headline
        headline_elem = soup.select_one('div.text-body-medium, h2.top-card-layout__headline, div.basic-info__headline')
        if headline_elem:
            profile_data['headline'] = headline_elem.text.strip()
            logger.info("Found headline")

        # Extract about section
        about_elem = soup.select_one('div.about-section, div.summary-section')
        if about_elem:
            profile_data['about'] = about_elem.text.strip()
            logger.info("Found about section")

        # Extract experience section
        experience_section = soup.find('section', {'id': 'experience-section'}) or \
                           soup.find('div', {'class': 'experience-section'})

        if experience_section:
            experiences = []
            exp_items = experience_section.find_all(['li', 'div'], class_=['experience-item', 'position-item'])

            for item in exp_items:
                role = item.find(['h3', 'span'], class_=['title', 't-bold'])
                company = item.find(['p', 'span'], class_=['company', 't-normal'])

                if role and company:
                    exp = f"{role.text.strip()} at {company.text.strip()}"
                    experiences.append(exp)
                    logger.info(f"Found experience: {exp}")

            if experiences:
                profile_data['experience'] = experiences

        if not profile_data:
            logger.error("No profile data could be extracted")
            raise Exception("Failed to extract any profile data")

        logger.info("Successfully extracted profile data")
        return profile_data

    except requests.exceptions.RequestException as e:
        logger.error(f"Request error: {str(e)}")
        raise Exception(f"Failed to access profile: {str(e)}")
    except Exception as e:
        logger.error(f"Error during extraction: {str(e)}")
        raise Exception(str(e))
    

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import logging

logger = logging.getLogger(__name__)

def get_profile_data_with_selenium(url):
    """Extract LinkedIn profile data using Selenium for better reliability."""
    logger.info("Using Selenium for profile extraction")
    
    # Define user agents directly in the function to avoid dependency
    user_agents_list = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0'
    ]
    
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    # Add user agent to appear more like a real browser
    chrome_options.add_argument(f"user-agent={random.choice(user_agents_list)}")
    
    try:
        service = Service('./chromedriver.exe')
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Add a random delay to avoid detection
        time.sleep(random.uniform(3, 7))
        
        driver.get(url)
        
        # Wait for page to fully load
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # Additional random delay after page load
        time.sleep(random.uniform(2, 5))
        
        profile_data = {}
        
        # Extract name (updated selectors)
        try:
            name_elem = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((
                    By.CSS_SELECTOR, 
                    'h1.text-heading-xlarge, h1.top-card-layout__title, h1.pv-text-details__left-panel--title'
                ))
            )
            profile_data['name'] = name_elem.text.strip()
            logger.info(f"Found name: {profile_data['name']}")
        except Exception as e:
            logger.warning(f"Could not extract name: {e}")
            profile_data['name'] = "Not found"
        
        # Extract headline (updated selectors)
        try:
            headline_elem = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((
                    By.CSS_SELECTOR, 
                    'div.text-body-medium, div.pv-text-details__left-panel--subtitle, div.ph5'
                ))
            )
            profile_data['headline'] = headline_elem.text.strip()
            logger.info(f"Found headline: {profile_data['headline']}")
        except Exception as e:
            logger.warning(f"Could not extract headline: {e}")
            profile_data['headline'] = "Not found"
        
        # Extract about section
        try:
            # First try to find and click "Show more" if it exists
            try:
                show_more = driver.find_element(By.CSS_SELECTOR, 'button.inline-show-more-text__button')
                driver.execute_script("arguments[0].click();", show_more)
                time.sleep(1)
            except:
                pass  # No "Show more" button found, continue
                
            about_elem = driver.find_element(
                By.CSS_SELECTOR, 
                'div.pv-about-section, div.pv-shared-text-with-see-more'
            )
            profile_data['about'] = about_elem.text.strip()
            logger.info("Found about section")
        except Exception as e:
            logger.warning(f"Could not extract about section: {e}")
            profile_data['about'] = "Not found"
        
        # Extract experience
        try:
            # Scroll to experience section
            experience_section = driver.find_element(
                By.CSS_SELECTOR, 
                'section#experience-section, section.experience-section, div#experience'
            )
            driver.execute_script("arguments[0].scrollIntoView();", experience_section)
            time.sleep(2)
            
            experiences = []
            exp_items = experience_section.find_elements(
                By.CSS_SELECTOR, 
                'li.experience-item, div.pvs-entity--padded'
            )
            
            for item in exp_items:
                try:
                    role = item.find_element(
                        By.CSS_SELECTOR, 
                        'h3.t-16, span.t-bold, span.mr1'
                    ).text.strip()
                    
                    company = item.find_element(
                        By.CSS_SELECTOR, 
                        'p.pv-entity__secondary-title, span.t-14'
                    ).text.strip()
                    
                    exp = f"{role} at {company}"
                    experiences.append(exp)
                    logger.info(f"Found experience: {exp}")
                except Exception as e:
                    logger.warning(f"Could not extract an experience item: {e}")
            
            if experiences:
                profile_data['experience'] = experiences
            else:
                profile_data['experience'] = ["No experience information found"]
                
        except Exception as e:
            logger.warning(f"Could not extract experience section: {e}")
            profile_data['experience'] = ["No experience information found"]
        
        # Extract education
        try:
            education_section = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'section#education-section, section.education-section'))
            )
            educations = []
            edu_items = education_section.find_elements(By.CSS_SELECTOR, 'li.education-item, div.pvs-entity--padded')
            
            for item in edu_items:
                try:
                    school = item.find_element(By.CSS_SELECTOR, 'h3.pv-entity__school-name, span.t-bold').text.strip()
                    degree = item.find_element(By.CSS_SELECTOR, 'p.pv-entity__secondary-title, span.t-14').text.strip()
                    educations.append(f"{school} - {degree}")
                    logger.info(f"Found education: {school} - {degree}")
                except Exception as e:
                    logger.warning(f"Could not extract an education item: {e}")
            
            profile_data['education'] = educations if educations else ["No education information found"]
        except Exception as e:
            logger.warning(f"Could not extract education section: {e}")
            profile_data['education'] = ["No education information found"]
        
        # Extract skills
        try:
            # Try to find and click "Show more skills" if it exists
            try:
                show_more = driver.find_element(By.CSS_SELECTOR, 'button.pv-skills-section__additional-skills')
                driver.execute_script("arguments[0].click();", show_more)
                time.sleep(2)
            except:
                pass  # No "Show more" button found, continue
            
            # Now extract all skills
            skills_section = driver.find_element(
                By.CSS_SELECTOR, 
                'section.pv-skill-categories-section, div#skills'
            )
            driver.execute_script("arguments[0].scrollIntoView();", skills_section)
            time.sleep(2)
            
            skills = []
            skill_items = skills_section.find_elements(
                By.CSS_SELECTOR, 
                'span.pv-skill-category-entity__name-text, div.pv-skill-card'
            )
            
            for item in skill_items:
                try:
                    skill = item.text.strip()
                    if skill:
                        skills.append(skill)
                        logger.info(f"Found skill: {skill}")
                except Exception as e:
                    logger.warning(f"Could not extract a skill: {e}")
            
            if skills:
                profile_data['skills'] = skills
            else:
                profile_data['skills'] = ["No skills information found"]
                
        except Exception as e:
            logger.warning(f"Could not extract skills section: {e}")
            profile_data['skills'] = ["No skills information found"]
        
        # Extract languages (if available)
        try:
            languages_section = driver.find_element(
                By.CSS_SELECTOR, 
                'section#languages-section, div.languages-section'
            )
            driver.execute_script("arguments[0].scrollIntoView();", languages_section)
            time.sleep(1)
            
            languages = []
            lang_items = languages_section.find_elements(
                By.CSS_SELECTOR, 
                'li.language-entity, div.pvs-entity--padded'
            )
            
            for item in lang_items:
                try:
                    language = item.find_element(By.CSS_SELECTOR, 'h3, span.t-bold').text.strip()
                    proficiency = "Proficiency not specified"
                    try:
                        proficiency_elem = item.find_element(By.CSS_SELECTOR, 'p.pv-entity__secondary-title, span.t-14')
                        proficiency = proficiency_elem.text.strip()
                    except:
                        pass
                    
                    lang = f"{language} - {proficiency}"
                    languages.append(lang)
                    logger.info(f"Found language: {lang}")
                except Exception as e:
                    logger.warning(f"Could not extract a language: {e}")
            
            if languages:
                profile_data['languages'] = languages
                
        except Exception as e:
            logger.warning(f"Could not extract languages section: {e}")
            # Don't set default value for languages as it's optional
        
        # Take a screenshot for debugging (optional)
        driver.save_screenshot('linkedin_profile_screenshot.png')
        logger.info("Profile extraction complete")
        
        return profile_data
        
    except Exception as e:
        logger.error(f"Error in Selenium extraction: {e}")
        return {
            'name': 'Error retrieving profile',
            'headline': f'Error: {str(e)}',
            'experience': ["Unable to retrieve experience information"],
            'education': ["Unable to retrieve education information"],
            'skills': ["Unable to retrieve skills information"]
        }
    finally:
        try:
            driver.quit()
        except:
            pass

def extract_profile_data(url: str) -> Dict:
    logger.info(f"Starting to extract profile data from: {url}")

    try:
        time.sleep(5)  # Add a 5-second delay
        session = create_session()

        # Add referrer to appear more legitimate
        session.headers.update({
            'Referer': 'https://www.google.com/search?q=linkedin+profile'
        })

        # Get the profile page
        logger.info("Sending request to LinkedIn...")
        response = session.get(url, timeout=30)

        # Log response details for debugging
        logger.info(f"Response status code: {response.status_code}")
        logger.info(f"Response headers: {dict(response.headers)}")

        if response.status_code == 999:
            logger.info("LinkedIn's security system has blocked the request. Trying with Selenium...")
            return get_profile_data_with_selenium(url)

        response.raise_for_status()

        # Check response content
        content_length = len(response.text)
        logger.info(f"Response content length: {content_length}")

        if content_length < 1000:
            logger.error("Response too short, likely not a valid profile page")
            raise Exception("Invalid response content")

        # Parse HTML content
        soup = BeautifulSoup(response.text, 'html.parser')

        # Check for error pages
        error_indicators = ["captcha", "please verify", "interrupted", "unavailable"]
        page_text = soup.get_text().lower()
        for indicator in error_indicators:
            if indicator in page_text:
                logger.error(f"Found error indicator: {indicator}")
                raise Exception(f"Access restricted: {indicator} check required")

        profile_data = {}

        # Extract name (multiple selectors for different page versions)
        name_found = False
        for selector in ['h1.text-heading-xlarge', 'h1.top-card-layout__title', 'h1.basic-info__name']:
            if name_found:
                break
            name_elem = soup.select_one(selector)
            if name_elem and name_elem.text.strip():
                profile_data['name'] = name_elem.text.strip()
                name_found = True
                logger.info(f"Found name using selector: {selector}")

        # Extract headline
        headline_elem = soup.select_one('div.text-body-medium, h2.top-card-layout__headline, div.basic-info__headline')
        if headline_elem:
            profile_data['headline'] = headline_elem.text.strip()
            logger.info("Found headline")

        # Extract about section
        about_elem = soup.select_one('div.about-section, div.summary-section')
        if about_elem:
            profile_data['about'] = about_elem.text.strip()
            logger.info("Found about section")

        # Extract experience section

        if not profile_data:
            logger.error("No profile data could be extracted")
            raise Exception("Failed to extract any profile data")

        logger.info("Successfully extracted profile data")
        return profile_data

    except requests.exceptions.RequestException as e:
        logger.error(f"Request error: {str(e)}")
        raise Exception(f"Failed to access profile: {str(e)}")
    except Exception as e:
        logger.error(f"Error during extraction: {str(e)}")
        raise Exception(str(e))
    
def scrape_linkedin_profile(url: str) -> Dict:
    """Main function to scrape LinkedIn profile data."""
    if not is_valid_linkedin_url(url):
        raise Exception("Invalid LinkedIn profile URL")

    try:
        # Try with Selenium first (more reliable)
        logger.info("Starting LinkedIn profile extraction with Selenium")
        return get_profile_data_with_selenium(url)
    except Exception as e:
        logger.error(f"Selenium extraction failed: {str(e)}")
        # Fallback to requests-based method
        logger.info("Falling back to requests-based extraction")
        try:
            return extract_profile_data(url)
        except Exception as fallback_error:
            logger.error(f"Fallback extraction failed: {str(fallback_error)}")
            raise Exception(f"Failed to extract profile data: {str(e)}")

