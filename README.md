# Corvus PDF Mission Extractor

## Description

This project contains a Python script designed to parse PDF documents for the tabletop game "Infinity the Game". It specifically extracts mission and scenario data from the official ITS season documents and converts it into a structured JSON format. This extracted data is intended to be ingested by the Rules of Engagement web app to easily display all of that information for users in an easy/quick to access format.

The script uses a combination of regular expressions and text analysis to identify and parse different sections of the mission descriptions, including objectives, deployment rules, special rules, and more.

## Installation

1.  **Python:** See the .venv dir for the correct version of python, v3, and all of the necessary packages
2.  **Dependencies:** Install the required Python packages. A `requirements.txt` is provided. The core dependencies are:
    *   `pymupdf` (PyMuPDF): For PDF text extraction.
    *   `click`: For creating the command-line interface.
    *   `rich`: For formatted console output.

    You can install them using pip, though they shoul already be included within the local env:
    ```bash
    pip install -r requirements.txt
    pip install pymupdf
    ```

## Usage

The script is executed from the command line and requires the path to the PDF file you want to process.

```bash
python main.py <path_to_pdf_file> [OPTIONS]
```

### Options

*   `--json_output <path>`: Specify a custom path for the output JSON file.
*   `-d`, `--debug`: Enable detailed debug output in the console during extraction.
*   `-r`, `--raw`: Output the raw, unprocessed text extracted for each scenario into the `raw_text/` directory.
*   `-z`, `--slow`: Add a small delay between processing each mission to make the console output easier to follow.

### Example

```bash
python main.py its-rules-season-17-en-v1.0.1.pdf --debug
```

## Core Logic (`main.py`)

The script's logic is organized into several key functions:

*   **`main(pdf_path, ...)`**: The main entry point for the CLI. It handles command-line arguments, determines some metadata from the PDF filename (like season and version), calls the core extraction function, and saves the final output to a JSON file.

*   **`extract_missions_from_pdf(pdf_path, ...)`**: This is the main orchestrator. It opens the PDF, reads the table of contents to identify where each mission starts and ends, and then iterates through them, calling other functions to extract and parse the text for each one.

*   **`parse_table_of_contents(toc_text, ...)`**: Scans the text of the table of contents page to find the names of all "ITS Scenarios" and "Direct Actions" and their corresponding page numbers.

*   **`extract_text_from_pages(doc, start_page, end_page, ...)`**: Given a page range, this function extracts all text from those pages within the PDF document and performs initial whitespace normalization.

*   **`parse_mission(name, text, ...)`**: This function takes the raw text of a single mission and breaks it down into structured data. It calls various specialized `extract_*` functions to handle specific sections.

*   **`extract_*` helper functions**: A series of specialized functions responsible for parsing distinct parts of a mission's text:
    *   `extract_objectives()`: Parses the main and secondary objectives, including handling complex tables of objective points.
    *   `extract_deployment()`: Extracts army point configurations and deployment zone details.
    *   `extract_special_rules()`: Parses scenario-specific rules, including complex, structured skills with requirements and effects.
    *   `extract_end_of_mission()`: Extracts the conditions for the mission's conclusion.
    *   ...and others for smaller details like tactical support options.

## Output

The script generates a single JSON file (e.g., `infinity_its_missions_season_17_v1.0.1.json`). The structure of this file is as follows:

```json
{
  "name": "Season 17",
  "version": "1.0.1",
  "missions": [
    {
      "name": "ANNIHILATION",
      "type": "ITS Scenario",
      "tables": {},
      "tactical_support_options": 4,
      "suitable_for_reinforcements": true,
      "mission_objectives": {
        "main_objectives": [
          "..."
        ],
        "secondary_objectives": [
          "..."
        ]
      },
      "forces_and_deployment": {
        "sides": "SIDE A and SIDE B",
        "deployment_table": [
            {...}
        ],
        "special_notes": []
      },
      "scenario_special_rules": {
        "rule_one": "...",
        "rule_two": {
            "name": "SKILL NAME",
            "skill_type": "short skill",
            "requirements": "...",
            "effects": "..."
        }
      },
      "end_of_mission": "..."
    },
    // ... more missions
  ]
}
```
