# PDF Processing and Date Extraction Tool

This advanced tool streamlines the management of PDF documents by automatically extracting dates and keywords to organize files efficiently, eliminating the need for manual triaging. It leverages Optical Character Recognition (OCR) technology to read text from PDF files—even those that are image-based—ensuring that no document is overlooked due to its format. The tool intelligently sorts documents into directories based on the year and month extracted from their content, creating an organized archive without manual intervention.

Key features include:
- **Advanced Date Extraction**: Utilizes both text analysis and OCR to find dates within PDF documents, supporting a wide array of date formats including those with French month names. This ensures accurate sorting even in documents with dates in natural language or varied formats.
- **Keyword-Based Filtering**: Scans documents for specified keywords to identify relevant documents. This feature supports both inclusion and exclusion lists, allowing for precise control over which documents are considered significant.
- **Automated File Organization**: Automatically sorts documents into folders based on the extracted dates, arranging them by year and month for easy retrieval. This process is fully automated, drastically reducing the time and effort required for file management.
- **Versatile Document Handling**: Capable of processing both text-based and image-based PDFs thanks to integrated OCR technology, ensuring comprehensive coverage across all types of documents.

This tool is designed to significantly reduce the manual workload associated with document sorting and archiving, making it an indispensable asset for businesses, researchers, and anyone dealing with large volumes of PDF documents.

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


python script_name.py [year] [additional keywords to be matched]

[year] pdfs with given year will be triaged
Undesired words must be added in the code source directly for now

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

## System Requirements

- **Python 3.x**: Ensure Python 3.x is installed on your system.
- **RAM**: OCR processing, especially on image-heavy PDF files, can be memory-intensive. We recommend having at least 16 GB of RAM for optimal performance, though more may be required for processing large volumes of documents or very large files.

## Performance Considerations

This tool uses Optical Character Recognition (OCR) to extract text from image-based PDF documents. OCR can be resource-intensive, particularly for documents with a high volume of images or when processing multiple documents simultaneously. Users should be aware that:

- **Memory Usage**: Depending on the size and complexity of the documents, significant amounts of RAM may be consumed. Systems with limited memory may experience slow performance or may fail to process large files.
- **Processing Time**: OCR and document processing time can vary. Large files or batches of files will take longer to process.

For large-scale processing tasks, consider running the tool on a system with ample memory and processing power to ensure smooth operation. Additionally, closing other memory-intensive applications during the OCR process can help improve performance.


## Note

The script is versatile and can be adapted for various use cases beyond the provided functionalities. Feel free to modify and extend it as needed to fit your specific requirements.
