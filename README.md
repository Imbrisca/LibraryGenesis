### **Guide: Understanding and Using the Code**

This Python script is a **LibGen Downloader** designed to automate downloading books from the Library Genesis (LibGen) repository, tailored to target Romanian and Italian books in specific formats (e.g., PDF, EPUB). Below is a detailed guide on its functionality and usage.

---

### **What the Code Does**
1. **Configuration:**
   - Specifies directories, languages, file formats, and domains to work with.
   - Allows retry and timeout settings for improved stability during network requests.

2. **Dependencies:**
   - Uses Python libraries such as `requests`, `BeautifulSoup`, `tqdm`, and `questionary` for web scraping, downloading, and creating a user-friendly CLI.

3. **Features:**
   - **Search and Filter Books:**
     - Fetches books by language (Romanian/Italian) and file format (PDF/EPUB).
   - **Download Manager:**
     - Supports parallel downloading using threads for improved performance.
   - **Error Handling:**
     - Handles incomplete downloads, retries failed downloads, and switches between alternative LibGen domains upon failure.
   - **Logging:**
     - Tracks download statistics, including runtime, books downloaded, and total data size.
   - **CLI Interface:**
     - Offers an interactive menu for selecting operations (e.g., fetching latest books, searching by language).

4. **Core Functionalities:**
   - **`fetch_latest_books`:** Fetches the latest books from LibGen based on the configured languages and formats.
   - **`run_latest`:** Automates downloading the latest books in Romanian or Italian.
   - **`run_search`:** Searches and downloads books based on a specific language or custom query.
   - **`process_book`:** Downloads a single book, handling incomplete download recovery.
   - **Statistics and Logging:** Provides detailed runtime metrics and logs downloads to a JSON file.

---

### **How to Use the Code**

#### **1. Prerequisites**
- Install Python 3.
- Ensure required libraries are installed (e.g., `requests`, `bs4`, `tqdm`, `humanize`, `questionary`). The script installs missing dependencies automatically.

#### **2. Running the Script**
- Save the script as `libgen_downloader.py`.
- Run it using:
  ```bash
  python libgen_downloader.py
  ```

#### **3. Main Menu Options**
Upon running the script, you'll see a menu with the following options:
- **1. Check latest files for Romanian and Italian books:**
  - Fetches and downloads books in Romanian and Italian languages.
- **2. Download only Romanian books:**
  - Focuses on Romanian books.
- **3. Download only Italian books:**
  - Focuses on Italian books.
- **4. Exit:**
  - Terminates the program.

Select an option using the keyboard, and the script will guide you through the process.

#### **4. Downloaded Files**
- Books are saved in the directory specified in `Config.SAVE_PATH` (default: `/home/ame/Desktop/3/Books/`).
- Incomplete downloads are cleaned up automatically to avoid corruption.

---

### **Key Components**

#### **1. Logging**
- Two loggers:
  - Console: Displays real-time progress with colorized output.
  - File: Logs detailed events in `libgen_downloader.log`.

#### **2. Error Handling**
- If a domain fails, the script switches to an alternative domain.
- Automatically retries failed requests up to three times.

#### **3. Download Statistics**
- Tracks total books found, downloaded, and data size.
- Provides average download speed and runtime.

#### **4. Threaded Downloads**
- Uses `ThreadPoolExecutor` to download multiple books concurrently, improving efficiency.


To easily change the language and path in the script, follow these steps:

### **1. Change the Language**
- Go to the `Config` class in the script.
- Modify the `LANGUAGES` list to include the desired languages. For example:
  ```python
  LANGUAGES = ["english", "spanish"]  # Replace with the languages you want
  ```

### **2. Change the Save Path**
- Update the `SAVE_PATH` variable in the `Config` class to your desired directory. For example:
  ```python
  SAVE_PATH = "/path/to/your/directory/"  # Replace with your preferred path
  ```
- Ensure the specified directory exists or the script will create it automatically.

### **3. Run the Script**
- Save the changes and run the script as usual. The updated languages and path will be used for downloading books.

These changes allow you to customize the script for your preferred language and file storage location.
