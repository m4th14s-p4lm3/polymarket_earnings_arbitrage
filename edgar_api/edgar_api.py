import requests
import json
import time
import re
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
import os
import pdfkit
import pytz

# 2 750 450
# 4 850 539
class EDGAR:
    SUBMISSIONS_URL =   "https://data.sec.gov/submissions/"
    DATA_URL =          "https://www.sec.gov/Archives/edgar/data/" # 1722684/000143774924032171/0001437749-24-032171.txt
    TICKERS_URL =       "https://www.sec.gov/files/company_tickers.json"

    COMPANY_TICKERS_AND_CIKS = None
    last_call_time = 0
    min_call_time = 1/9 # seconds
    
    @staticmethod
    def wait_for_it():
        while time.perf_counter() - EDGAR.last_call_time <=  EDGAR.min_call_time:
            # time.sleep(time.perf_counter() - last_call_time)
            pass
        EDGAR.last_call_time = time.perf_counter()

    def __init__(self):
        self.__SYSTEM_NAME__ = "CTU Prague TAB team"
        self.__email__ = "mathias.palme@seznam.cz"
        self.headers = {'User-Agent': f"{self.__SYSTEM_NAME__} {self.__email__}"}

        EDGAR.COMPANY_TICKERS_AND_CIKS = self.get_tickers()

    def ping(self):
        url = EDGAR.TICKERS_URL
        response = requests.get(url, headers = self.headers)
        return response

    def does_ticker_exit(self, ticker):
        for i in EDGAR.COMPANY_TICKERS_AND_CIKS:
            if EDGAR.COMPANY_TICKERS_AND_CIKS[i]["ticker"] == ticker:
                return True
        return False

    def get_tickers(self):
        response = requests.get(EDGAR.TICKERS_URL, headers = self.headers)
        return json.loads(response.text)
    
    def get_cik_by_ticker(self, ticker):
        for i in EDGAR.COMPANY_TICKERS_AND_CIKS:
            if EDGAR.COMPANY_TICKERS_AND_CIKS[i]["ticker"] == ticker:
                return EDGAR.COMPANY_TICKERS_AND_CIKS[i]["cik_str"]
        return None

    def get_ticker_by_cik(self, cik_str):
        for i in EDGAR.COMPANY_TICKERS_AND_CIKS:
            if str(EDGAR.COMPANY_TICKERS_AND_CIKS[i]["cik_str"]) == str(cik_str):
                return EDGAR.COMPANY_TICKERS_AND_CIKS[i]["ticker"]
        return None

    def get_company_name_by_ticker(self, ticker):
        for i in EDGAR.COMPANY_TICKERS_AND_CIKS:
            if EDGAR.COMPANY_TICKERS_AND_CIKS[i]["ticker"] == ticker:
                return EDGAR.COMPANY_TICKERS_AND_CIKS[i]["title"]
        return None

    def custom_request(self, url):
        response = requests.get(url, headers = self.headers)
        return response
    
    def get_submission_search_by_cik(self, cik, deep = False) -> dict:
        """
            To get all historical submitions you must use deep = True otherwise only aproximitly first 1000 will be returned
        """
        cik_str = "CIK" + (10 - len(str(cik))) * "0" + str(cik)
        url = EDGAR.SUBMISSIONS_URL + cik_str + ".json"
        result = requests.get(url, headers=self.headers)
        result_json = json.loads(result.text)
        # return url
        # print(url)
        # return result.text

        files = result_json["filings"]["files"]

        file_names = []
        # Extraced data:
        accessionNumber = result_json["filings"]["recent"]["accessionNumber"]
        core_type = result_json["filings"]["recent"]["core_type"]
        form = result_json["filings"]["recent"]["form"]
        acceptanceDateTime = result_json["filings"]["recent"]["acceptanceDateTime"]
        primaryDocument = result_json["filings"]["recent"]["primaryDocument"]

        if deep:
            for entry in files:
                file_name = entry["name"]
                file_names.append(file_name)

                result = requests.get(EDGAR.SUBMISSIONS_URL + file_name, headers=self.headers)
                result_json = json.loads(result.text)
                accessionNumber += result_json["accessionNumber"]
                core_type += result_json["core_type"]
                form += result_json["form"]
                acceptanceDateTime += result_json["acceptanceDateTime"]
                primaryDocument += result_json["primaryDocument"]

        acceptanceDateTime = [datetime.strptime(time_stamp, '%Y-%m-%dT%H:%M:%S.%fZ').replace(tzinfo=ZoneInfo("America/New_York")).astimezone(ZoneInfo("UTC")) for time_stamp in acceptanceDateTime]
        return accessionNumber, form, core_type, acceptanceDateTime, primaryDocument


    def get_legecy_submissions_by_cik(self, cik, add_dashes = True):
        request_url = EDGAR.DATA_URL + str(cik)

        result = requests.get(request_url, headers=self.headers, timeout=None)

        pattern = r'alt="folder icon">(.*?)</a>'
        accessionNumber = re.findall(pattern, result.text)

        if add_dashes:
            for i in range(len(accessionNumber)):
                accessionNumber[i] = accessionNumber[i][:10] + '-' + accessionNumber[i][10:12] + '-' + accessionNumber[i][12:]

        return accessionNumber

    def get_number_of_submissions_by_cik(self, cik):
        cik_str = "CIK" + (10 - len(str(cik))) * "0" + str(cik)
        result = requests.get(EDGAR.SUBMISSIONS_URL + cik_str + ".json", headers=self.headers)
        result_json = json.loads(result.text)

        return len(result_json["filings"]["recent"]["accessionNumber"])

    def get_submission_data(self, cik, accessionNumber):
        request_url = f"{EDGAR.DATA_URL}{str(cik)}/{str(accessionNumber).replace('-', '')}/{accessionNumber}.txt"

        result = requests.get(request_url, headers = self.headers, timeout=None)    

        return result.text
     
    def get_rss_feed(self):
        url = "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&CIK=&type=&company=&dateb=&owner=include&start=0&count=40&output=atom"
        r = requests.get(url, headers=self.headers, timeout=None)
        text = r.text

        pattern = re.compile(
            r'<entry>.*?'
            r'<title>(?P<title>.*?)</title>.*?'
            r'<link[^>]+?href="(?P<href>[^"]+)"[^>]*?>.*?'
            r'<updated>(?P<updated>.*?)</updated>.*?'
            r'</entry>',
            re.DOTALL | re.IGNORECASE
        )

        return [(m.group('title'), m.group('href'), m.group('updated'))
                for m in pattern.finditer(text)]

    def extract_htm_urls(self, url):
        """
        Excludes all R*.htm documents
        """
        res = self.custom_request(url)
        key_string = "Directory Listing"

        key_string_index = res.text.find(key_string)
        extracted_html_content = res.text[key_string_index + len(key_string):].split("\n")[0]
        
        urls = re.findall(r'href="([^"]*?/(?!(R\d+))[^/"]*?\.htm)"', extracted_html_content)
        cleaned_urls = [url[0] for url in urls]
        cleaned_urls = ["https://www.sec.gov" + u for u in cleaned_urls]

        return cleaned_urls

    def download_pdf_document(self, document_url, download_path, document_name):
        path = os.path.join(download_path, document_name + ".pdf")
        pdfkit.from_url(document_url, path)
        # HTML(document_url).write_pdf(path)

        return path

if __name__ == "__main__":
    edgar = EDGAR()
    # import time
    # from datetime import datetime, timezone, timedelta
    # from concurrent.futures import ThreadPoolExecutor, as_completed
    # import pdfkit
    # import os

    # ticker = "GS"

    # cik = edgar.get_cik_by_ticker(ticker)
    # print(edgar.get_submissions_by_cik(cik))
    # exit()

    # accessionNumber, form, core_type, acceptanceDateTime, primaryDocument = edgar.deep_submission_search(cik)
    # data_path = "data"
    # output_path = os.path.join(data_path, ticker)

    # if not os.path.isdir(data_path):
    #     os.mkdir(data_path)

    # # print(ticker)
    # if not os.path.isdir(output_path):
    #     os.mkdir(output_path)

    # cnt = 0
    # years_back = 5
    # dt_5ya = datetime.now(timezone.utc) - timedelta(days=years_back*365)
    # for i in range(len(core_type)):
    #     dt = acceptanceDateTime[i] 
    #     if dt > dt_5ya and form[i] in {"10-Q", "10-K", "8-K", "6-K"}:
    #         document_url = f"{EDGAR.DATA_URL}{cik}/{"".join(accessionNumber[i].split("-"))}/"
    #         print(acceptanceDateTime[i],",", document_url)
    #         cnt+=1
    # print(cnt)




    # ----- VERIFY ------
    # accessionNumber_str_list = [str(dt) for dt in accessionNumber] 
    # accessionNumber_str_set = set(accessionNumber_str_list)
    # legecy = edgar.get_legecy_submissions_by_cik(cik)
    # print(len(legecy), len(accessionNumber_str_list))
    # print(len(accessionNumber_str_set) == len(accessionNumber_str_list))

