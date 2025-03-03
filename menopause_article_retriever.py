# Import necessary modules
import logging
import gridfs
from pymongo import MongoClient
from bson import ObjectId
import os

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger()

# MongoDB setup
client = MongoClient("mongodb://localhost:27017/")
db = client['menopause']
fs = gridfs.GridFS(db)

# Retrieve a PDF from MongoDB by its ID and save it with its original filename
def retrieve_pdf(pdf_id, output_dir="downloads"):
    try:
        logger.info(f"Attempting to retrieve PDF with ID: {pdf_id}")

        pdf_file = fs.get(ObjectId(pdf_id))
        filename = pdf_file.filename

        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        output_path = os.path.join(output_dir, filename)

        with open(output_path, 'wb') as f:
            f.write(pdf_file.read())

        logger.info(f"PDF retrieved and saved as: {output_path}")

    except Exception as e:
        logger.error(f"Error retrieving PDF: {e}", exc_info=True)

def main():
    # Example
    pdf_id = "67c3421643af0005a53dd677"
    retrieve_pdf(pdf_id)

if __name__ == '__main__':
    main()
