import base64
import os
import tempfile
import json
import concurrent.futures

from typing import Optional, List
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

from edgar_api import EDGAR
import logging
import json
import time

# LOG_DIR = "logs"
# if not os.path.isdir(LOG_DIR):
#     os.mkdir(LOG_DIR)

# logging.basicConfig(
#     level=logging.INFO,
#     format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
#     filename=f'logs/oracle.log',
#     filemode='a'
# )
logger = logging.getLogger(__name__)


edgar = EDGAR()
# prompt_prefix = """You are a block chain oracle for polymarket, and you will be provided with rules to resolve stock earnings prediction market and evident in a form of SEC 8-K or 10-K or 10-Q documents. Your task is to return in json format market resolution {"resolution" : "yes"/"no"/"not enough informations"}. Return ONLY valid JSON. Do not include explanations, markdown, or code fences. Rules"""
prompt_prefix = """You are a block chain oracle for polymarket, and you will be provided with rules to resolve stock earnings prediction market and evident in a form of SEC 8-K or 10-K or 10-Q documents. Your task is to return in json format market resolution {"resolution" : "yes"/"no"/"not enough informations", "reasoning" : "explanation for the result"}. Return ONLY valid JSON. Do not include explanations, markdown, or code fences. Rules"""


def send_prompt_with_pdfs(prompt: str, file_paths: Optional[List[str]] = None) -> str:
    """
    Generates content using the Gemini 2.5 Flash model, including one or more files.

    Args:
        prompt: The text prompt (e.g., "Compare the key findings in these documents.").
        file_paths: An optional list of paths to the files (PDFs, images, etc.) to upload.

    Returns:
        The generated text content as a string, or an error message.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return "Error: GEMINI_API_KEY environment variable not found."

    try:
        client = genai.Client(api_key=api_key)
    except Exception as e:
        return f"Error initializing genai.Client: {e}"

    model = "gemini-2.5-flash"
    uploaded_files: List[genai.types.File] = []

    try:
        # 1. Start the content list with the text prompt
        contents: List[genai.types.Part] = [prompt]

        # 2. Upload all files if paths are provided
        if file_paths:
            # print("Starting file uploads...")
            for path in file_paths:
                if not os.path.exists(path):
                    # print(f"Warning: File not found at path: {path}. Skipping.")
                    continue

                # print(f"Uploading: {os.path.basename(path)}...")
                uploaded_file = client.files.upload(file=path)
                uploaded_files.append(uploaded_file)
                contents.append(uploaded_file)  # Add file object to contents

            if not uploaded_files:
                return "Error: No valid files were uploaded."
            # print("All files uploaded successfully.")

        # 3. Call the API with combined content (files + prompt)
        response = client.models.generate_content(
            model=model,
            contents=contents,
        )
        return response.text

    except Exception as e:
        return f"Error during content generation: {e}"

    finally:
        # 4. Clean up: Delete all uploaded files from the API service
        if uploaded_files:
            # print(f"\nCleaning up and deleting {len(uploaded_files)} file(s)...")
            for f in uploaded_files:
                try:
                    client.files.delete(name=f.name)
                except Exception as del_e:
                    print(f"Error deleting file {f.name}: {del_e}")
            # print("Cleanup complete.")


# def get_resolution(desc: str, sec_url: str):
#     urls = edgar.extract_htm_urls(sec_url)

#     with tempfile.TemporaryDirectory() as tmp:

#         def download_one(i_url):
#             i, url = i_url
#             out_path = os.path.join(tmp, f"{i}.pdf")
#             edgar.download_pdf_document(url, tmp, f"{i}")
#             logger.info(f"Downloaded file - {url}")
#             return out_path

#         # Parallel download
#         with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
#             tmp_files = list(ex.map(download_one, enumerate(urls)))

#         # Process
#         res = send_prompt_with_pdfs(prompt_prefix + desc, tmp_files)

#         logger.info(f"Source = {sec_url}")
#         logger.info(f"Num files = {len(tmp_files)}")
#         logger.info(res)

#     return res


def get_resolution(desc: str, sec_url: str):
    urls = edgar.extract_htm_urls(sec_url)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_files = []
        start_time = time.perf_counter()
        for i, u in enumerate(urls):
            # print(u)
            edgar.download_pdf_document(u, tmp, f"{i}")
            logger.info(f"Downloading file - {u}")
            tmp_files.append(os.path.join(tmp, f"{i}.pdf"))
        logger.info(f"files download time: {time.perf_counter() - start_time} ")

        res = send_prompt_with_pdfs(prompt_prefix + desc, tmp_files)
        # res = json.loads(res)
        logger.info(f"Source = {sec_url}")
        logger.info(f"Num files = {len(tmp_files)}")
        logger.info(res)
        # print(res["resolution"])
        # res = json.loads(res)
    return res


if __name__ == "__main__":
    desc = """Churchill Downs is estimated to release earnings on October 22, 2025. The Street consensus estimate for Churchill Downs's GAAP EPS for the relevant quarter is $1.00. This market will resolve to "Yes" if Churchill Downs reports GAAP EPS greater than $1.00 for the relevant quarter in its next quarterly earnings release. Otherwise, it will resolve to "No." The resolution source will be the GAAP EPS listed in the company’s official earnings documents.

If Churchill Downs releases earnings without GAAP EPS, then the market will resolve according to the GAAP EPS figure reported by SeekingAlpha. If no such figure is published within 96h of market close (4:00:00pm ET) on the day earnings are announced, the market will resolve to “No”.

If the company does not release earnings within 45 calendar days of the estimated earnings date, this market will resolve to “No.”

Note: Subsequent restatements, corrections, or revisions made to the initially announced GAAP EPS figure will not qualify for resolution, except in the case of obvious and immediate mistakes (e.g., fat finger errors, as with Lyft's (LYFT) earnings release in February 2024).
Note: The strike prices used in these markets are derived from SeekingAlpha estimates, and reflect the consensus of sell-side analyst estimates for GAAP EPS.
Note: All figures will be rounded to the nearest cent using standard rounding.
Note: For the purposes of this market, IFRS EPS will be treated as GAAP EPS.
Note: For the purposes of this market, GAAP EPS refers to diluted GAAP EPS, unless this is not published, in which case it refers to basic GAAP EPS.
Note: All figures are expressed in USD, unless otherwise indicated.
"""

    from edgar_api import EDGAR

    edgar = EDGAR()

    # urls = edgar.extract_htm_urls("http://sec.gov/Archives/edgar/data/315189/000110465925116130")
    # for i, u in enumerate(urls):
    #     print(u)
    #     edgar.download_pdf_document(u, "data",f"{i}")

    # res = send_prompt_with_pdfs(prompt_prefix + desc, ["data/0.pdf", "data/1.pdf", "data/2.pdf"])
    res = get_resolution(
        desc, "http://sec.gov/Archives/edgar/data/20212/000002021225000134"
    )
    # print(res["resolution"])
    print(res)

    # print(urls)
    # edgar.download_pdf_document()
