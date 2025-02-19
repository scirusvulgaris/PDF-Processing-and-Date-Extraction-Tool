import os
import re
import shutil
from datetime import datetime
import sys
import random
import string
from concurrent.futures import ThreadPoolExecutor, as_completed
import zipfile
import fitz
import easyocr
import io
from PIL import Image
import numpy as np
import traceback

# ANSI escape codes for colors
BLACK = '\033[30m'
RED = '\033[31m'
GREEN = '\033[32m'
YELLOW = '\033[33m'
BLUE = '\033[34m'
MAGENTA = '\033[35m'
CYAN = '\033[36m'
WHITE = '\033[37m'
BOLD_BLACK = '\033[1;30m'
BOLD_RED = '\033[1;31m'
BOLD_GREEN = '\033[1;32m'
BOLD_YELLOW = '\033[1;33m'
BOLD_BLUE = '\033[1;34m'
BOLD_MAGENTA = '\033[1;35m'
BOLD_CYAN = '\033[1;36m'
BOLD_WHITE = '\033[1;37m'
UNDERLINE_BLACK = '\033[4;30m'
UNDERLINE_RED = '\033[4;31m'
UNDERLINE_GREEN = '\033[4;32m'
UNDERLINE_YELLOW = '\033[4;33m'


RESET = '\033[0m'  # Reset to default color


def extract_month_from_french(text):
    months_french = {
        'janvier': 1, 'février': 2, 'f´evrier':2 , 'mars': 3, 'avril': 4,
        'mai': 5, 'juin': 6, 'juillet': 7, 'août': 8,'aoˆut': 8, 
        'septembre': 9, 'octobre': 10, 'novembre': 11, 'décembre': 12, 'd´ecembre': 12
    }
    for month, number in months_french.items():
        if month in text.lower():
            words = text.split()
            year = next((int(word) for word in words if word.isdigit() and len(word) == 4), None)
            if year:
                return f"01/{number:02d}/{year}"
    return None


import re
from datetime import datetime

# French month dictionary for day-month-year patterns and fallback detection
FRENCH_MONTHS = {
    # Normalize them to handle accent combos in real texts
    # (suggesting you standardize text by removing weird accent marks)
    'janvier': 1, 'février': 2, 'f´evrier': 2, 'fevrier': 2,
    'mars': 3, 'avril': 4, 'mai': 5, 'juin': 6,
    'juillet': 7,
    'août': 8, 'aoˆut': 8, 'aout': 8,
    'septembre': 9, 'octobre': 10, 'novembre': 11,
    'décembre': 12, 'decembre': 12, 'd´ecembre': 12
}


def extract_date_from_text(text):

    current_year = datetime.now().year
    min_year = 1900
    max_year = current_year + 1

    # ========== 1) Numeric Patterns ==========
    numeric_patterns = [
        # dd/mm/yyyy
        r'\b([0-3]\d)/([0-1]\d)/(20[0-9]{2})\b',
        # dd-mm-yyyy
        r'\b([0-3]\d)-([0-1]\d)-(20[0-9]{2})\b',
        # dd.mm.yyyy
        r'\b([0-3]\d)\.([0-1]\d)\.(20[0-9]{2})\b',
        # yyyy-mm-dd
        r'\b(20[0-9]{2})-([0-1]\d)-([0-3]\d)\b',
        # dd/mm/yy (two digits for year)
        r'\b([0-3]\d)/([0-1]\d)/([0-9]{2})\b',
    ]

    for pattern in numeric_patterns:
        m = re.search(pattern, text)
        if m:
            # We expect exactly 3 capturing groups from each pattern
            groups = m.groups()
            date_obj = try_parse_numeric(groups, min_year, max_year)
            if date_obj:
                return date_obj.month, date_obj.year

    english_patterns = [
        # Pattern A: Month day, year  (e.g. "October 6, 2024" or "Oct 6, 2024")
        r'\b((January|February|March|April|May|June|July|August|September|October|November|December)|'
        r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sept|Sep|Oct|Nov|Dec))\s+(\d{1,2}),\s*(20[0-9]{2})\b',

        # Pattern B: day Month year  (e.g. "6 October 2024" or "13 Jul 2024")
        r'\b(\d{1,2})\s+((January|February|March|April|May|June|July|August|September|October|November|December)|'
        r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sept|Sep|Oct|Nov|Dec))\s+(20[0-9]{2})\b'
    ]

    for pattern in english_patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            date_obj = try_parse_english(m, min_year, max_year)
            if date_obj:
                return date_obj.month, date_obj.year

    french_pattern = (
        r'\b(\d{1,2})\s+('
        r'jan(?:vier)?|f[ée]v(?:rier)?|f´ev(?:rier)?|mars|avr(?:il)?|mai|juin|juil(?:let)?|ao[ûˆu]t|sept(?:embre)?|oct(?:obre)?|'
        r'nov(?:embre)?|d[ée]c(?:embre)?|d´ec(?:embre)?'
        r')\s+(20\d{2})\b'
    )
    match_fr = re.search(french_pattern, text, re.IGNORECASE)
    if match_fr:
        date_obj = try_parse_french(match_fr, min_year, max_year)
        if date_obj:
            return date_obj.month, date_obj.year

    # ========== 4) Fallback: Only French month + year (no day) ==========

    fallback_str = extract_month_from_french(text)
    if fallback_str:
        try:
            date_obj = datetime.strptime(fallback_str, "%d/%m/%Y")
            if min_year <= date_obj.year <= max_year:
                print(f"here is date found via fallback: {date_obj.month}, {date_obj.year}")
                return date_obj.month, date_obj.year
        except ValueError:
            pass

    # If no date recognized at all
    return None, None


def try_parse_numeric(groups, min_year, max_year):
    """
    Decide if it is 'dd/mm/yyyy' or 'yyyy-mm-dd' based on which group starts with '20'.
    Return datetime object or None.
    """
    try:
        if groups[0].startswith('20'):
            # pattern is likely yyyy-mm-dd
            yyyy = int(groups[0])
            mm = int(groups[1])
            dd = int(groups[2])
        elif groups[-1].startswith('20'):
            # pattern is dd/mm/yyyy
            dd = int(groups[0])
            mm = int(groups[1])
            yyyy = int(groups[2])
        else:
            # 2-digit year => e.g. dd / mm / yy
            dd = int(groups[0])
            mm = int(groups[1])
            yy = int(groups[2])
            yyyy = 2000 + int(yy)  # assume 20xx for 2-digit year

        candidate = datetime(yyyy, mm, dd)
        if min_year <= yyyy <= max_year:
            print(f"Parsed numeric date => {candidate}")
            return candidate
    except ValueError:
        pass  # e.g. invalid date (32nd day, etc.)
    return None


def try_parse_english(match_obj, min_year, max_year):
    matched_text = match_obj.group(0)
    for fmt in ('%B %d, %Y', '%b %d, %Y', '%d %B %Y', '%d %b %Y'):
        try:
            candidate = datetime.strptime(matched_text, fmt)
            yyyy = candidate.year
            if min_year <= yyyy <= max_year:
                print(f"Parsed English date => {candidate}")
                return candidate
        except ValueError:
            continue
    return None


def try_parse_french(match_obj, min_year, max_year):

    day_str = match_obj.group(1)
    month_word = match_obj.group(2).lower().replace('´', '').replace('ˆ', '')  # normalize
    year_str = match_obj.group(3)

    try:
        day = int(day_str)
        year = int(year_str)

        # map to numeric month:
        month_num = None
        for k, v in FRENCH_MONTHS.items():
            if month_word.startswith(k):
                month_num = v
                break

        if month_num is None:
            return None  # Unrecognized month

        candidate = datetime(year, month_num, day)
        if min_year <= year <= max_year:
            print(f"Parsed French date => {candidate}")
            return candidate
    except ValueError:
        pass
    return None


def extract_month_from_french(text):

    months_french = {
        'janvier': 1, 'février': 2, 'f´evrier': 2, 'mars': 3, 'avril': 4,
        'mai': 5, 'juin': 6, 'juillet': 7, 'août': 8, 'aoˆut': 8,
        'septembre': 9, 'octobre': 10, 'novembre': 11, 'décembre': 12, 'd´ecembre': 12
    }
    # Normalize
    lower_text = text.lower().replace('´', '').replace('ˆ', '')

    for month_word, number in months_french.items():
        if month_word in lower_text:
            words = lower_text.split()
            year = next((int(word) for word in words if word.isdigit() and len(word) == 4), None)
            if year:
                return f"01/{number:02d}/{year}"
    return None


def generate_random_suffix(size=3, chars=string.ascii_letters + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))


def contains_undesired_keywords(text, specific_keywords=["ceci n'est pas une facture"]):
    return any(keyword.lower() in text for keyword in specific_keywords)


def contains_desired_keywords(text, specific_keywords=["facture", "Invoice", "rechnung", "facturation", "repas"]):
    return any(keyword.lower() in text for keyword in specific_keywords)

def process_pdf_file(filepath, year, keywords, unsorted_files):
    # Skip if file doesn't exist
    if not os.path.exists(filepath):
        print(f"Skipping non-existent file: {filepath}")
        return

    reader = easyocr.Reader(['en'])
    text = ""
    try:
        with fitz.open(filepath) as pdf:
            for page_number, page in enumerate(pdf):
                page_text = page.get_text()
                if page_text:
                    text += page_text.replace('\n', ' ').lower()
                else:
                    print(f"[*] Will process PDF {CYAN}{filepath}{RESET}")
                    image_list = page.get_images(full=True)
                    for image_index, img in enumerate(image_list):
                        print(f"[*] OCRing")
                        xref = img[0]
                        base_image = pdf.extract_image(xref)
                        image_bytes = base_image["image"]
                        image = Image.open(io.BytesIO(image_bytes))
                        image = image.resize((image.width // 2, image.height // 2), Image.Resampling.LANCZOS)
                        image_np = np.array(image)
                        ocr_result = reader.readtext(image_np, detail=0, paragraph=True)
                        text += ' '.join(ocr_result).replace('\n', ' ').lower()
                        month, year = extract_date_from_text(text)
                        if month and (any(keyword.lower() in text for keyword in keywords) or contains_desired_keywords(text)):
                            break

            if contains_undesired_keywords(text):
                target_folder_path = os.path.join(os.getcwd(), "commande")
                os.makedirs(target_folder_path, exist_ok=True)
                target_file_path = construct_target_file_path(target_folder_path, filepath)
                try:
                    shutil.move(filepath, target_file_path)
                    print(f"Moved {YELLOW}'{os.path.basename(filepath)}'{RESET} to {BLUE}'commande'.{RESET}")
                except:
                    print(f"Failed to move {filepath} to commande folder")
            elif any(keyword.lower() in text for keyword in keywords) or contains_desired_keywords(text):
                month, year_extracted = extract_date_from_text(text)
                if not month:
                    unsorted_files.append(filepath)
                    return
                target_folder_path = os.path.join(os.getcwd(), str(year_extracted), "Facture fournisseur", f"{month:02d}")
                os.makedirs(target_folder_path, exist_ok=True)
                target_file_path = construct_target_file_path(target_folder_path, filepath)
                try:
                    shutil.move(filepath, target_file_path)
                    print(f"Moved '{GREEN}{os.path.basename(filepath)}'{RESET} to {BLUE}'{month} {year_extracted}'.{RESET}")
                except:
                    print(f"Failed to move {filepath}")
    except Exception as e:
        print(f"Error processing file '{filepath}': {e}")
        traceback.print_exc()
        unsorted_files.append(filepath)


def construct_target_file_path(target_folder_path, filepath):
    target_file_path = os.path.join(target_folder_path, os.path.basename(filepath))
    if os.path.exists(target_file_path):
        base, extension = os.path.splitext(os.path.basename(filepath))
        new_filename = f"{base}_{generate_random_suffix()}{extension}"
        target_file_path = os.path.join(target_folder_path, new_filename)
    return target_file_path


def find_pdf_files(directory, max_depth=2):
    pdf_files = []
    year_pattern = re.compile(r'^20\d{2}$')
    for root, dirs, files in os.walk(directory):
        current_level = root.count(os.path.sep)
        start_level = directory.rstrip(os.path.sep).count(os.path.sep)
        if current_level - start_level > max_depth:
            dirs[:] = []
        else:
            dirs[:] = [d for d in dirs if d.lower() != "commande" and not year_pattern.fullmatch(d)]
            for file in files:
                if file.lower().endswith('.pdf'):
                    pdf_files.append(os.path.join(root, file))
    return pdf_files


def unzip_files_in_directory(directory):
    for filename in os.listdir(directory):
        if filename.endswith('.zip'):
            zip_path = os.path.join(directory, filename)
            print(f"Unzipping '{filename}'...")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(directory)
            print(f"Finished unzipping '{filename}'.")


def delete_empty_folders(directory, max_depth=2):
    for root, dirs, files in os.walk(directory, topdown=False):
        if root != directory and (not os.listdir(root)):
            # print(f"{RED}Deleting empty folder: {root}{RESET}")
            os.rmdir(root)

def count_pdf_files(directory, max_depth=2):
    pdf_count = 0
    total_size = 0
    pdf_files = []
    year_pattern = re.compile(r'^20\d{2}$')

    print(f"\n{BOLD_CYAN}Scanning directory for PDF files...{RESET}")

    for root, dirs, files in os.walk(directory):
        current_level = root.count(os.path.sep)
        start_level = directory.rstrip(os.path.sep).count(os.path.sep)

        if current_level - start_level > max_depth:
            dirs[:] = []
        else:
            dirs[:] = [d for d in dirs if d.lower() != "commande" and not year_pattern.fullmatch(d)]
            for file in files:
                if file.lower().endswith('.pdf'):
                    full_path = os.path.join(root, file)
                    if os.path.exists(full_path):
                        pdf_count += 1
                        file_size = os.path.getsize(full_path)
                        total_size += file_size
                        pdf_files.append((full_path, file_size))

    print(f"{BOLD_GREEN}Found{RESET} {BOLD_CYAN}{pdf_count}{RESET} {BOLD_GREEN}PDF files{RESET}")

    return pdf_count, pdf_files

if __name__ == "__main__":
    keywords = ["facture", "invoice", "fechnung"]
    year = None
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        year = int(sys.argv[1])
        keywords += [keyword.lower() for keyword in sys.argv[2:]]
    else:
        keywords += [keyword.lower() for keyword in sys.argv[1:]]

    # Count files first
    total_files, pdf_files = count_pdf_files(os.getcwd())

    if total_files == 0:
        print(f"{RED}No PDF files found in the directory.{RESET}")
        sys.exit(1)

    print(f"\n{BOLD_GREEN}Starting processing...{RESET}")

    unzip_files_in_directory(os.getcwd())
    unsorted_files = []

    # Create progress counter
    processed_files = 0

    with ThreadPoolExecutor(max_workers=(os.cpu_count() or 1)) as executor:
        futures = {executor.submit(process_pdf_file, pdf[0], year, keywords, unsorted_files): pdf[0]
                  for pdf in pdf_files}

        for future in as_completed(futures):
            processed_files += 1
            # Calculate percentage
            percentage = (processed_files / total_files) * 100
            print(f"\r{BOLD_CYAN}Progress: {percentage:.1f}% ({processed_files}/{total_files}){RESET}",
                  end='', flush=True)

    print("\n")  # New line after progress
    delete_empty_folders(os.getcwd(), max_depth=2)

    if unsorted_files:
        print(f"\n{YELLOW}The following PDF files could not be sorted ({len(unsorted_files)} files):{RESET}")
        for filepath in unsorted_files:
            print(f"{filepath}")
    else:
        print(f"\n{CYAN}All PDF files have been sorted successfully.{RESET}")
