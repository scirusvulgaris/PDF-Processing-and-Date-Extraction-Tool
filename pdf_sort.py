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
        'janvier': 1, 'février': 2, 'mars': 3, 'avril': 4,
        'mai': 5, 'juin': 6, 'juillet': 7, 'août': 8,
        'septembre': 9, 'octobre': 10, 'novembre': 11, 'décembre': 12
    }
    for month, number in months_french.items():
        if month in text.lower():
            words = text.split()
            year = next((int(word) for word in words if word.isdigit() and len(word) == 4), None)
            if year:
                return f"01/{number:02d}/{year}"
    return None


def extract_date_from_text(text):
    # Define a reasonable year range for validation
    current_year = datetime.now().year
    min_year = 1900  # Minimum year considered valid
    max_year = current_year + 1  # Allow current year and next year as valid to handle future-dated documents

    date_formats = [
        # Note: Added stricter day and month checks in regex could be done, but left as is for clarity
        # r'\b(0[1-9]|[1-2][0-9]|3[01]).(0[1-9]|1[0-2]).(20[0-9]{2})\b'      # Format any type where dd mm yyyy; but will produce false positive results
        r'(\b(0[1-9]|[1-2][0-9]|3[01])/(0[1-9]|1[0-2])/(20[0-9]{2}).*?)',    # Format: dd/mm/yyyy
        r'\b(0[1-9]|[1-2][0-9]|3[01])\.(0[1-9]|1[0-2])\.(20[0-9]{2}).*?',    # Format: dd.mm.yyyy
        r'\b(0[1-9]|[1-2][0-9]|3[01])\ (0[1-9]|1[0-2])\ (20[0-9]{2}).*?',    # Format: dd mm yyyy
        r'\b(0[1-9]|[1-2][0-9]|3[01])\-(0[1-9]|1[0-2])\-(20[0-9]{2}).*?',    # Format: dd-mm-yyyy
        r'\b(20[0-9]{2})\-(0[1-9]|1[0-2])\-(0[1-9]|[12][0-9]|3[01]).*?',     # Format: yyyy-mm-dd

        # r'\b(0[1-9]|[1-2][0-9]|3[01]).(0[1-9]|1[0-2]).(?:[0-9]{2})\b',     # Format any type where dd mm yy
        r'(\b(0[1-9]|[1-2][0-9]|3[01])\ (0[1-9]|1[0-2])\ (?:[0-9]{2}).*?)',  # Format: dd mm yy
        r'\b(0[1-9]|[1-2][0-9]|3[01])\.(0[1-9]|1[0-2])\.(?:[0-9]{2}).*?',    # Format: dd.mm.yy
        r'(\b(0[1-9]|[1-2][0-9]|3[01])/(0[1-9]|1[0-2])/(?:[0-9]{2}).*?)',    # Format: dd/mm/yy

        r'(\b(0[1-9]|[1-2][0-9]|3[01])\s[A-Za-z]{3}\.?\s(20[0-9]{2}).*?)'      # Format: 13 Jul 2023 or [with a dot] 13 Jul. 2023
        r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\ (0[1-9]|1[0-2])\,\ (20[0-9]{2}).*?'
    ]

    for date_format in date_formats:
        date_match = re.search(date_format, text)
        # print(f"Here's function {BOLD_GREEN}extract_date_from_text and {BLUE}{date_match}{RESET}, {text[:50]}\n")
        if date_match:
            # print(f"Here's function {BOLD_GREEN}extract_date_from_text and {BLUE}{date_match}{RESET}, {text[:50]}\n")
            for fmt in ('%d/%m/%Y', '%d.%m.%Y', '%d.%m.%y', '%d %m %Y', '%d %b %Y', '%Y-%m-%d'):
                try:
                    date_obj = datetime.strptime(date_match.group(0), fmt)
                    # Adjust year for two-digit formats to handle the century correctly
                    if fmt.endswith('%y'):
                        # print(fmt.endswith('%y'))
                        year = 2000 + (date_obj.year % 100)  # Adjust for yy format assuming 2000s
                    else:
                        print
                        year = date_obj.year

                    # Validate the year to ensure it's within a reasonable range
                    if min_year <= year <= max_year:
                        # print(f"here is date found : {date_obj.month}, {year}")
                        return date_obj.month, year
                    else:
                        # print(f"Found an unrealistic year: {year}. Skipping this date.")
                        continue  # Skip this date match and continue searching
                except ValueError:
                    continue

    # Check for French month names if no standard date format is found
    french_date = extract_month_from_french(text)
    if french_date:
        try:
            date_obj = datetime.strptime(french_date, "%d/%m/%Y")
            return date_obj.month, date_obj.year
        except ValueError:
            pass
    return None, None


def generate_random_suffix(size=3, chars=string.ascii_letters + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))


def contains_undesired_keywords(text, specific_keywords=["ceci n'est pas une facture"]):
    return any(keyword.lower() in text for keyword in specific_keywords)


def contains_desired_keywords(text, specific_keywords=["facture", "invoice", "rechnung", "facturation", "repas"]):
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

    # Convert total size to readable format
    size_str = ""
    if total_size < 1024:
        size_str = f"{total_size} bytes"
    elif total_size < 1024 * 1024:
        size_str = f"{total_size/1024:.2f} KB"
    else:
        size_str = f"{total_size/(1024*1024):.2f} MB"

    print(f"{BOLD_GREEN}Found {pdf_count} PDF files{RESET} (Total size: {BOLD_YELLOW}{size_str}{RESET})")

    # Sort files by size and show the largest ones
    if pdf_files:
        print(f"\n{BOLD_CYAN}Largest files:{RESET}")
        for path, size in sorted(pdf_files, key=lambda x: x[1], reverse=True)[:3]:
            size_mb = size/(1024*1024)
            print(f"{BLUE}{os.path.basename(path)}{RESET}: {YELLOW}{size_mb:.2f} MB{RESET}")

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

    # Ask for confirmation
    response = input(f"\n{BOLD_YELLOW}Do you want to proceed with processing {total_files} files? (y/n): {RESET}")
    if response.lower() != 'y':
        print(f"{RED}Operation cancelled by user.{RESET}")
        sys.exit(0)

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


