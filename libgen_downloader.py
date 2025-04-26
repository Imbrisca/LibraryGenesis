import os
import time
import json
import logging
import datetime
import hashlib
import sys
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from bs4 import BeautifulSoup

try:
    import humanize
    from tqdm import tqdm
    import questionary
    from questionary import Style
except ImportError:
    import subprocess
    print("Installing required packages...")
    subprocess.call(['pip', 'install', 'humanize', 'tqdm', 'questionary'])
    import humanize
    from tqdm import tqdm
    import questionary
    from questionary import Style

# Configuration
class Config:
    SAVE_PATH = "/home/ame/Desktop/3/Books/"
    LANGUAGES = ["romanian", "italian"]
    EXTENSIONS = ["pdf", "epub"]
    DOMAINS = [
        "https://libgen.rs",
        "https://libgen.is",
        "https://libgen.st",
        "http://libgen.li",
        "http://gen.lib.rus.ec"
    ]
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }
    MAX_RETRIES = 3
    REQUEST_DELAY = 2
    DOWNLOAD_TIMEOUT = 60
    MAX_WORKERS = 2
    DOWNLOAD_LOG = "downloaded_books.json"
    TEMP_DOWNLOAD_SUFFIX = ".downloading"

os.makedirs(Config.SAVE_PATH, exist_ok=True)

# Logging setup
class ColorizedFormatter(logging.Formatter):
    COLORS = {
        'DEBUG': '\033[94m',
        'INFO': '\033[92m',
        'WARNING': '\033[93m',
        'ERROR': '\033[91m',
        'CRITICAL': '\033[41m',
        'ENDC': '\033[0m',
    }

    def format(self, record):
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = f"{self.COLORS[levelname]}{levelname}{self.COLORS['ENDC']}"
        return super().format(record)

logger = logging.getLogger("LibGenDownloader")
logger.setLevel(logging.DEBUG)
file_handler = logging.FileHandler('libgen_downloader.log')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(ColorizedFormatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(console_handler)

class LibGenDownloader:
    def __init__(self, config: Config):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update(config.HEADERS)
        self.active_domain = self.config.DOMAINS[0]
        self.total_books_found = 0
        self.total_books_downloaded = 0
        self.total_bytes_downloaded = 0
        self.start_time = time.time()
        self.downloaded_books = self.load_download_log()
        self.process_incomplete_downloads()

    def load_download_log(self) -> Dict:
        if os.path.exists(self.config.DOWNLOAD_LOG):
            try:
                with open(self.config.DOWNLOAD_LOG, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading download log: {e}")
                return {}
        return {}

    def save_download_log(self):
        try:
            with open(self.config.DOWNLOAD_LOG, 'w') as f:
                json.dump(self.downloaded_books, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving download log: {e}")

    def process_incomplete_downloads(self):
        for filename in os.listdir(self.config.SAVE_PATH):
            if filename.endswith(self.config.TEMP_DOWNLOAD_SUFFIX):
                try:
                    path = os.path.join(self.config.SAVE_PATH, filename)
                    os.remove(path)
                    real_filename = filename[:-len(self.config.TEMP_DOWNLOAD_SUFFIX)]
                    for key in list(self.downloaded_books.keys()):
                        if self.downloaded_books[key].get('filename') == real_filename:
                            del self.downloaded_books[key]
                    logger.info(f"Removed incomplete download: {filename}")
                except Exception as e:
                    logger.error(f"Error removing incomplete download: {e}")
        self.save_download_log()

    def log_statistics(self):
        elapsed = max(1, time.time() - self.start_time)
        logger.info("=== Statistics ===")
        logger.info(f"Runtime: {datetime.timedelta(seconds=int(elapsed))}")
        logger.info(f"Books found: {self.total_books_found}")
        logger.info(f"Books downloaded: {self.total_books_downloaded}")
        logger.info(f"Data downloaded: {humanize.naturalsize(self.total_bytes_downloaded)}")
        logger.info(f"Avg speed: {humanize.naturalsize(self.total_bytes_downloaded / elapsed)}/s")
        logger.info(f"Logged downloads: {len(self.downloaded_books)}")

    def fetch_html(self, url: str) -> Optional[str]:
        for retry in range(self.config.MAX_RETRIES):
            try:
                r = self.session.get(url, timeout=self.config.DOWNLOAD_TIMEOUT)
                r.raise_for_status()
                return r.text
            except requests.exceptions.RequestException:
                time.sleep(self.config.REQUEST_DELAY * (retry + 1))
        return None

    def try_domains(self, page: int, search_url: str = None) -> Optional[str]:
        if search_url:
            url = f"{self.active_domain}{search_url}&page={page}"
        else:
            url = f"{self.active_domain}/search.php?mode=last&page={page}"
            
        html = self.fetch_html(url)
        if html:
            return html
            
        for domain in self.config.DOMAINS:
            if domain == self.active_domain:
                continue
                
            if search_url:
                url = f"{domain}{search_url}&page={page}"
            else:
                url = f"{domain}/search.php?mode=last&page={page}"
                
            html = self.fetch_html(url)
            if html:
                self.active_domain = domain
                logger.info(f"Switching to domain: {domain}")
                return html
        return None

    def parse_books(self, html: str, target_language: Optional[str] = None) -> List[Dict]:
        soup = BeautifulSoup(html, "html.parser")
        table = soup.find("table", {"class": "c"})
        if not table:
            return []

        books = []
        for row in table.find_all("tr")[1:]:
            cells = row.find_all("td")
            if len(cells) < 10:
                continue
            try:
                lang = cells[6].text.strip().lower()
                
                # Filter by target language if specified, otherwise use the config languages
                if target_language:
                    if target_language not in lang:
                        continue
                elif not any(l in lang for l in self.config.LANGUAGES):
                    continue
                    
                ext = cells[8].text.strip().lower()
                if ext not in self.config.EXTENSIONS:
                    continue
                    
                mirrors = [a.get("href") for a in cells[9].find_all("a")]
                book = {
                    "id": cells[0].text.strip(),
                    "title": cells[2].text.strip(),
                    "author": cells[1].text.strip(),
                    "publisher": cells[3].text.strip() or "unknown",
                    "year": cells[4].text.strip(),
                    "language": lang,
                    "size": cells[7].text.strip(),
                    "extension": ext,
                    "mirrors": mirrors
                }
                book["key"] = self.generate_book_key(book)
                books.append(book)
            except Exception:
                continue
        return books

    def generate_book_key(self, book: Dict) -> str:
        text = f"{book['title']}-{book['author']}-{book['year']}-{book['extension']}"
        return hashlib.md5(text.encode()).hexdigest()

    def fetch_latest_books(self, page: int = 1, target_language: Optional[str] = None) -> List[Dict]:
        html = self.try_domains(page)
        if not html:
            return []
            
        books = self.parse_books(html, target_language)
        
        if target_language:
            filtered_books = [b for b in books if target_language in b["language"]]
        else:
            filtered_books = [b for b in books if any(lang in b["language"] for lang in self.config.LANGUAGES)]
            
        self.total_books_found += len(filtered_books)
        return [b for b in filtered_books if b["key"] not in self.downloaded_books]

    def fetch_search_books(self, page: int, search_url: str, target_language: str) -> List[Dict]:
        html = self.try_domains(page, search_url)
        if not html:
            return []
            
        books = self.parse_books(html, target_language)
        self.total_books_found += len(books)
        return [b for b in books if b["key"] not in self.downloaded_books]

    def download_file(self, url: str, dest_path: str) -> bool:
        temp_path = dest_path + self.config.TEMP_DOWNLOAD_SUFFIX
        try:
            with self.session.get(url, stream=True, timeout=self.config.DOWNLOAD_TIMEOUT) as r:
                r.raise_for_status()
                total_size = int(r.headers.get('content-length', 0))
                with tqdm(total=total_size, unit='B', unit_scale=True, desc=os.path.basename(dest_path)) as bar:
                    with open(temp_path, 'wb') as f:
                        for chunk in r.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                                bar.update(len(chunk))
            os.rename(temp_path, dest_path)
            self.total_books_downloaded += 1
            self.total_bytes_downloaded += total_size
            return True
        except Exception as e:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            logger.debug(f"Download failed: {e}")
            return False

    def process_book(self, book: Dict) -> Optional[str]:
        if not book["mirrors"]:
            return None
        safe_title = "".join(c for c in book["title"] if c.isalnum() or c in " _-").strip() or "Unknown_Title"
        safe_author = "".join(c for c in book["author"] if c.isalnum() or c in " _-").strip() or "Unknown_Author"
        filename = f"{safe_title} - {safe_author} ({book['year']}).{book['extension']}"
        filepath = os.path.join(self.config.SAVE_PATH, filename)
        for mirror in book["mirrors"]:
            html = self.fetch_html(mirror)
            if not html:
                continue
            soup = BeautifulSoup(html, "html.parser")
            get_link = soup.find("a", string="GET")
            if not get_link:
                continue
            download_url = get_link["href"]
            if self.download_file(download_url, filepath):
                self.downloaded_books[book["key"]] = {
                    "id": book["id"],
                    "title": book["title"],
                    "author": book["author"],
                    "language": book["language"],
                    "filename": os.path.basename(filepath),
                    "size": book["size"],
                    "downloaded": datetime.datetime.now().isoformat()
                }
                self.save_download_log()
                return filepath
            time.sleep(self.config.REQUEST_DELAY)
        return None

    def check_end_of_content(self, html: str) -> bool:
        soup = BeautifulSoup(html, "html.parser")
        table = soup.find("table", {"class": "c"})
        if not table:
            return True
        rows = table.find_all("tr")
        return len(rows) <= 1

    def run_latest(self):
        logger.info("Starting LibGen Downloader - Latest Books")
        try:
            page = 1
            while True:
                logger.info(f"Processing page {page}")
                html = self.try_domains(page)
                if not html:
                    logger.warning(f"Could not fetch page {page}, skipping")
                    page += 1
                    continue
                if self.check_end_of_content(html):
                    logger.info("Reached end of content.")
                    break
                books = self.fetch_latest_books(page=page)
                if books:
                    with ThreadPoolExecutor(max_workers=self.config.MAX_WORKERS) as executor:
                        futures = [executor.submit(self.process_book, book) for book in books]
                        for future in as_completed(futures):
                            future.result()
                    self.log_statistics()
                else:
                    logger.info(f"No Romanian/Italian books found on page {page}")
                page += 1
                time.sleep(self.config.REQUEST_DELAY)
            logger.info("Download completed.")
            self.log_statistics()
        except KeyboardInterrupt:
            logger.info("Interrupted by user.")
            self.save_download_log()
            
    def run_search(self, search_url: str, target_language: str):
        logger.info(f"Starting LibGen Downloader - {target_language.capitalize()} Books Search")
        try:
            page = 1
            while True:
                logger.info(f"Processing page {page}")
                html = self.try_domains(page, search_url)
                if not html:
                    logger.warning(f"Could not fetch page {page}, skipping")
                    page += 1
                    continue
                if self.check_end_of_content(html):
                    logger.info("Reached end of content.")
                    break
                books = self.fetch_search_books(page, search_url, target_language)
                if books:
                    with ThreadPoolExecutor(max_workers=self.config.MAX_WORKERS) as executor:
                        futures = [executor.submit(self.process_book, book) for book in books]
                        for future in as_completed(futures):
                            future.result()
                    self.log_statistics()
                else:
                    logger.info(f"No {target_language} books found on page {page}")
                page += 1
                time.sleep(self.config.REQUEST_DELAY)
            logger.info("Download completed.")
            self.log_statistics()
        except KeyboardInterrupt:
            logger.info("Interrupted by user.")
            self.save_download_log()

def print_header():
    header = """
    ╭───────────────────────────────────────────────╮
    │                                               │
    │             LibGen Downloader                 │
    │                                               │
    ╰───────────────────────────────────────────────╯
    """
    print(header)

def run_cli():
    print_header()
    
    # Define the questionary style
    custom_style = Style([
        ('qmark', 'fg:cyan bold'),
        ('question', 'fg:white bold'),
        ('answer', 'fg:green bold'),
        ('pointer', 'fg:cyan bold'),
        ('highlighted', 'fg:cyan bold'),
        ('selected', 'fg:cyan bold'),
        ('separator', 'fg:cyan'),
        ('instruction', 'fg:white'),
        ('text', 'fg:white'),
    ])
    
    # Main menu options
    choices = [
        {
            'name': '1. Check latest files for Romanian and Italian books',
            'value': 'latest'
        },
        {
            'name': '2. Download only Romanian books',
            'value': 'romanian'
        },
        {
            'name': '3. Download only Italian books',
            'value': 'italian'
        },
        {
            'name': '4. Exit',
            'value': 'exit'
        }
    ]
    
    # Create the downloader instance
    downloader = LibGenDownloader(Config())
    
    while True:
        answer = questionary.select(
            'Select an option:',
            choices=choices,
            style=custom_style
        ).ask()
        
        if answer == 'latest':
            downloader.run_latest()
        elif answer == 'romanian':
            search_url = "/search.php?req=romanian&lg_topic=libgen&open=0&view=simple&res=25&phrase=1&column=language"
            downloader.run_search(search_url, "romanian")
        elif answer == 'italian':
            search_url = "/search.php?req=italian&open=0&res=25&view=simple&phrase=1&column=language"
            downloader.run_search(search_url, "italian")
        elif answer == 'exit':
            print("Exiting...")
            break
        
        # After completing an operation, ask if user wants to continue
        if questionary.confirm('Do you want to perform another operation?', style=custom_style).ask():
            continue
        else:
            print("Exiting...")
            break

if __name__ == "__main__":
    try:
        run_cli()
    except KeyboardInterrupt:
        print("\nProgram interrupted by user. Exiting...")
        sys.exit(0)
