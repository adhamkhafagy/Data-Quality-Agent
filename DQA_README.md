# Automated Data Quality Agent

An AI-powered agent that scans any uploaded CSV or Excel file, detects common data quality issues, and returns clear explanations plus ready-to-use Python fixes — all without exposing real column names or data values to the LLM.

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![Streamlit](https://img.shields.io/badge/App-Streamlit-red.svg)
![Groq](https://img.shields.io/badge/LLM-Groq%20API-orange.svg)
![License](https://img.shields.io/badge/License-MIT-lightgrey.svg)

## Table of Contents
- [Overview](#overview)
- [Features](#features)
- [Privacy Design](#privacy-design)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Setup](#setup)
- [Usage](#usage)
- [Detected Issue Types](#detected-issue-types)
- [Future Improvements](#future-improvements)
- [License](#license)

## Overview
This project automates the first step of any data analysis workflow: assessing data quality. Instead of manually scanning a dataset for missing values, duplicates, outliers, and inconsistencies, the agent runs a full diagnostic pass, masks the results for privacy, and asks an LLM to explain each issue in plain language with a matching pandas fix — all displayed in a clean, expandable Streamlit report.

## Features
- Supports both CSV and Excel (.xlsx) uploads
- 11 automated data quality checks covering the most common real-world issues
- Column masking before any data reaches the LLM (privacy by design)
- Structured JSON output from the LLM, rendered as expandable sections with severity indicators
- Ready-to-copy pandas code for each detected issue
- Clean, professional Streamlit interface

## Privacy Design
Before anything is sent to the LLM, column names are replaced with generic placeholders (`col_1`, `col_2`, ...) and only aggregate statistics (counts, percentages, data types) are shared — never the raw data values themselves. The mapping between real and masked column names stays local and is used only to reconstruct the final report for the user.

## Tech Stack
- Python
- pandas
- Groq API (`llama-3.3-70b-versatile`)
- Streamlit
- python-dotenv

## Project Structure
```
data-quality-agent/
├── app.py
├── requirements.txt
├── .gitignore
├── .env (not tracked)
└── README.md
```

## Setup
1. Clone the repository
```bash
git clone https://github.com/adhamkhafagy/data-quality-agent.git
cd data-quality-agent
```

2. Install dependencies
```bash
pip install -r requirements.txt
```

3. Add your Groq API key in a `.env` file
```
GROQ_API_KEY=your_actual_key_here
```

4. Run the app
```bash
streamlit run app.py
```

## Usage
1. Upload a `.csv` or `.xlsx` file
2. Review the data preview
3. Click **Analyze Data Quality**
4. Expand each detected issue to see the explanation and the pandas fix

## Detected Issue Types
| Issue | Description |
|---|---|
| Missing Values | Null or empty values per column |
| Duplicates | Fully duplicated rows |
| Type Issues | Numeric columns polluted with invalid text values |
| Outliers | Statistical outliers detected via the IQR method |
| Inconsistent Categories | Same category written in different cases/whitespace |
| Whitespace Issues | Leading/trailing whitespace in text values |
| Negative Values | Unexpected negative values in numeric columns |
| Date Format Issues | Mixed date formats within the same column |
| Constant Columns | Columns where every value is identical |
| ID Uniqueness Issues | Expected-unique identifier columns containing duplicates |
| Mixed Types | Columns containing a mix of different data types |

## Future Improvements
- Allow the user to apply the suggested fixes directly and download the cleaned file
- Add support for SQL database connections as a data source
- Add a downloadable PDF/CSV summary of the report
- Support batch analysis of multiple files at once

## License
This project is licensed under the MIT License.
