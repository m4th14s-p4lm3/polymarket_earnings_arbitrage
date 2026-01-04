from ast import List, Tuple
from dataclasses import dataclass
from enum import Enum
import logging
import os
import shutil
import tempfile
from time import perf_counter
from edgar_api import EDGAR
from google import genai
import json

from edgar_api.edgar_api import EDGAR

class Resolution(Enum):
    YES = "yes"
    NO = "no"
    UNK = "unknown"


AGENT_RULES = """You are a block chain oracle for polymarket, and you will be provided with rules to resolve stock earnings prediction market and evident in a form of SEC 8-K or 10-K or 10-Q documents. Your task is to return in json format market resolution {"resolution" : "yes"/"no"/"unk", "reasoning" : "explanation for the result"}. You cannot connect to the internet, your decision must be made solely based on the provided documents. Return ONLY valid JSON. Do not include explanations, markdown, or code fences. Rules"""


class Oracle:
    """Oracle that uses Gemini API to resolve SEC filings based on provided rules."""
    def __init__(
            self,
            edgar_instance: EDGAR,
            model_version: str = "gemini-2.5-flash",
            prompt_prefix: str = AGENT_RULES,
            ):
        self.edgar = edgar_instance

        # Get API key from environment variable
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("Error: GEMINI_API_KEY environment variable not found.")
        try:
            self.client = genai.Client(api_key=api_key)
        except Exception as e:
            raise ValueError(f"Error initializing genai.Client: {e}")

        self.model_version = model_version
        self.prompt_prefix = prompt_prefix

    def resolve(self, sec_link: str, description: str = "") -> Resolution:
        logging.info(f"Resolving SEC link: {sec_link}")
        uploaded_files = []
        try:
            try:
                urls = self.edgar.extract_htm_urls(sec_link)
            except Exception as e:
                logging.warning(f"Failed to extract URLs from {sec_link}: {e}")
                return Resolution.UNK

            with tempfile.TemporaryDirectory() as tmp:
                paths = [
                    self.edgar.download_document(u, tmp, str(i))
                    for i, u in enumerate(urls)
                    if u
                ]

                if not paths:
                    logging.warning(f"No documents downloaded from {sec_link}")
                    return Resolution.UNK

                contents = [self.prompt_prefix, description]

                for path in paths:
                    try:
                        f = self.client.files.upload(file=path)
                        uploaded_files.append(f)
                        contents.append(f)
                    except Exception as e:
                        logging.warning(f"Failed to upload document {path}: {e}")

                if not uploaded_files:
                    logging.warning(f"No documents uploaded for {sec_link}")
                    return Resolution.UNK

            response = self.client.models.generate_content(
                model=self.model_version,
                contents=contents,
            )

            data = json.loads(response.text)
            res = data.get("resolution", "").lower()

            if res == "yes":
                return Resolution.YES
            if res == "no":
                return Resolution.NO

            logging.info(f"{sec_link} resolved into unknown resolution response: {response.text}")
            return Resolution.UNK

        except Exception as e:
            logging.exception(f"Error during resolution of {sec_link}: {e}")
            return Resolution.UNK

        finally:
            for f in uploaded_files:
                try:
                    name = getattr(f, "name", None) or getattr(f, "id", None)
                    if name:
                        self.client.files.delete(name=name)
                except Exception as e:
                    logging.warning(f"Error deleting file {name} from the model context: {e}")
                    pass


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    desc = """Rules
As of market creation, Carnival is estimated to release earnings on December 19, 2025. The Street consensus estimate for Carnival’s non-GAAP EPS for the relevant quarter is $0.25 as of market creation. This market will resolve to "Yes" if Carnival reports non-GAAP EPS greater than $0.25 for the relevant quarter in its next quarterly earnings release. Otherwise, it will resolve to "No." The resolution source will be the non-GAAP EPS listed in the company’s official earnings documents.

If Carnival releases earnings without non-GAAP EPS, then the market will resolve according to the non-GAAP EPS figure reported by SeekingAlpha. If no such figure is published within 96h of market close (4:00:00pm ET) on the day earnings are announced, the market will resolve according to the GAAP EPS listed in the company’s official earnings documents; or, if not published there, according to the GAAP EPS provided by SeekingAlpha. If no GAAP EPS number is available from either source at that time, the market will resolve to “No.” (For the purposes of this market, GAAP EPS refers to diluted GAAP EPS, unless it is not published, in which case it refers to basic GAAP EPS.)

If the company does not release earnings within 45 calendar days of the estimated earnings date, this market will resolve to “No.”

Note: Subsequent restatements, corrections, or revisions made to the initially announced non-GAAP EPS figure will not qualify for resolution, except in the case of obvious and immediate mistakes (e.g., fat finger errors, as with Lyft's (LYFT) earnings release in February 2024).
Note: The strike prices used in these markets are derived from SeekingAlpha estimates, and reflect the consensus of sell-side analyst estimates for non-GAAP EPS.
Note: All figures will be rounded to the nearest cent using standard rounding.
Note: For the purposes of this market, IFRS EPS will be treated as GAAP EPS.
Note: If multiple versions of non-GAAP EPS are published, the market will resolve according to the primary headline non-GAAP EPS number, which is typically presented on a diluted basis. If diluted is not published, then basic non-GAAP EPS will qualify.
Note: All figures are expressed in USD, unless otherwise indicated.
Note: For primarily internationally listed companies, this market refers specifically to the shares traded in the United States on U.S. stock exchanges such as the NYSE or Nasdaq. In cases where the company trades in the U.S. through an American Depositary Receipt (ADR) or American Depositary Share (ADS), this market will refer to the ADR/ADS.
Created At: Nov 25, 2025, 3:40 PM CET

"""
    edgar_instance = EDGAR()
    oracle = Oracle(edgar_instance)
    # 0,ccl-quarterly-earnings-nongaap-eps-12-19-2025-0pt25,-54,1766153767,1766153821,https://www.sec.gov/Archives/edgar/data/815097/000162828025058106,Yes
    test_sec_link = "https://www.sec.gov/Archives/edgar/data/815097/000162828025058106"
    print(oracle.resolve(test_sec_link, description=desc))