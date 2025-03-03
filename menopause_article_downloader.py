# Import necessary modules
import time
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from pymongo import MongoClient
import gridfs
import requests
from io import BytesIO

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()

# MongoDB setup
client = MongoClient('mongodb://localhost:27017/')
db = client['menopause']
collection = db['articles']
fs = gridfs.GridFS(db)  # GridFS to store large (PDFs)

# Initializes the Chrome WebDriver with specified options
def initialize_driver():
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')  # Run in headless mode
    driver = webdriver.Chrome(options=options)
    driver.maximize_window()
    return driver

# Extracts article URLs from the search result pages of the website
def get_article_urls(base_url, start_page=1):
    article_urls = []
    article_titles = []
    page_number = start_page

    logger.info(f'Navigated to page {page_number}...')
    while True:
        try:
            driver.get(f'{base_url}{page_number}')
            WebDriverWait(driver, 10).until(  # Wait until the page loads completely
                EC.presence_of_element_located((By.CSS_SELECTOR, 'dt.search-results-title a'))
            )

            # Find all article title elements on the page
            title_elements = driver.find_elements(By.CSS_SELECTOR, 'dt.search-results-title a')
            if not title_elements:
                logger.info(f'No articles found on page {page_number}. Stopping...')
                break

            # Collect the URLs and titles of all articles on the current page
            for title_element in title_elements:
                article_urls.append(title_element.get_attribute('href'))
                article_titles.append(title_element.text)

            page_number += 1
            logger.info(f'Navigated to page {page_number}...')

        except Exception as e:
            logger.error(f"Error occurred while extracting URLs from page {page_number}: {e}")
            break

    return article_urls, article_titles

# Downloads the PDF from the article page
def download_pdf(url):
    try:
        driver.get(url)
        WebDriverWait(driver, 10).until(  # Wait until the download button is present
            EC.presence_of_element_located((By.ID, 'downloadPdf'))
        )

        # Find the PDF download link and extract its URL
        pdf_link = driver.find_element(By.ID, 'downloadPdf').get_attribute('href')
        logger.info(f"Found PDF link: {pdf_link}")

        # Send an HTTP GET request to download the PDF
        response = requests.get(pdf_link)
        response.raise_for_status()

        return BytesIO(response.content)  # Return the PDF content as a BytesIO object

    except Exception as e:
        logger.error(f'Failed to download PDF from {url}: {e}')
        return None

# Stores the PDF in MongoDB using GridFS
def store_article_pdf(url, pdf_data, title):
    try:
        # Store the PDF in GridFS and retrieve the file ID
        file_id = fs.put(pdf_data, filename=title + '.pdf', content_type='application/pdf', url=url)
        logger.info(f"Stored PDF for article: {title} (ID: {file_id})")

        # Store the article metadata in the 'articles' collection
        article_data = {
            'url': url,
            'title': title,
            'pdf_id': file_id,
            'timestamp': time.time()
        }
        collection.insert_one(article_data)
        logger.info(f"Stored metadata for article: {title}")

    except Exception as e:
        logger.error(f'Failed to store PDF for article: {title} - {e}')

def main():
    global driver
    driver = initialize_driver()

    # Define the base URL
    base_url = 'https://journals.plos.org/plosone/search?filterArticleTypes=Research%20Article&filterSections=Title&q=menopause&sortOrder=RELEVANCE&page='

    # Get article URLs and titles
    logger.info("Starting to collect article URLs...")
    article_urls, article_titles = get_article_urls(base_url)

    # Download PDFs and store them in MongoDB
    for url, title in zip(article_urls, article_titles):
        # Download the PDF content
        pdf_data = download_pdf(url)

        if pdf_data:
            # Store the PDF and its metadata in MongoDB
            store_article_pdf(url, pdf_data, title)

    driver.quit()

if __name__ == "__main__":
    main()