
# PDF Processing and Date Extraction Tool

This tool automates the processing of PDF documents, focusing on extracting dates and sorting files based on content criteria such as the presence of specific keywords. It supports multiple date formats, recognizes desired and undesired keywords, and manages PDF files within a directory structure.

## Features

- **Date Extraction**: Supports mmultiple date formats, such as  `dd/mm/yyyy`, `dd.mm.yyyy`, `dd-mm-yyyy`, `yyyy-mm-dd` and English and French month names.
- **Keyword Detection**: Identifies specific keywords to determine the relevance of a PDF.
- **File Processing**: Extracts text and images from PDF files using `fitz` and `EasyOCR`.
- **File Sorting**: Organizes files into directories based on extracted dates and keywords.

## Dependencies

Ensure you have Python 3.x installed on your system. This tool depends on several Python libraries which are listed in the `requirements.txt` file.

## Installation

1. Clone the repository or download the tool's source code to your local machine.
2. Navigate to the tool's directory in your terminal or command prompt.
3. Install the required dependencies by running:


pip install -r requirements.txt


## Usage

1. **Setup**: Place the script in the directory with your PDF files.
2. **Customization**: Customize the `keywords` list within the main block to match your document processing needs.
3. **Execution**: Run the script with optional year and keywords arguments.


python script_name.py [year] [additional keywords]


## Function Overview

- `extract_month_from_french(text)`: Extracts the month from text with French month names.
- `extract_date_from_text(text)`: Identifies dates in text using regular expressions.
- `generate_random_suffix(size, chars)`: Generates a random suffix for filenames.
- `contains_undesired_keywords(text, specific_keywords)`: Checks for undesired keywords in text.
- `contains_desired_keywords(text, specific_keywords)`: Checks for desired keywords in text.
- `process_pdf_file(filepath, year, keywords, unsorted_files)`: Processes a single PDF file, extracting text and/or images, and sorts the file based on the extracted date and keywords.
- `construct_target_file_path(target_folder_path, filepath)`: Constructs a target file path for moving a processed file.
- `find_pdf_files(directory, max_depth)`: Searches for PDF files within a specified directory and its subdirectories up to a specified depth.
- `unzip_files_in_directory(directory)`: Unzips all `.zip` files in a given directory.
- `delete_empty_folders(directory, max_depth)`: Deletes empty folders within a specified directory and its subdirectories up to a specified depth.

## Note

The script is versatile and can be adapted for various use cases beyond the provided functionalities. Feel free to modify and extend it as needed to fit your specific requirements.
