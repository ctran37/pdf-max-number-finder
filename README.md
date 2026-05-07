# PDF Max Number Finder

Finds the largest numerical value in a PDF document — both as written (`max_numerical_raw`) and with natural language scale adjustments applied (`max_numerical_adjusted`).

For example, if the document states that values are in millions, a raw value of `3.15` is treated as `3,150,000`.

## How it works

- Extracts tables and prose text separately using `pdfplumber`
- Detects scale declarations (`dollars in millions`, `in thousands`, etc.) at the document and per-page/table level
- Applies scale context to each number while filtering out false positives: years, page numbers, numbers already expressed at full scale

## Setup

Requires Python 3 to be installed.

```bash
pip install -r requirements.txt
```

## Usage

```bash
# Local file
python analyze.py path/to/document.pdf
python analyze.py FY25_Air_Force_Working_Capital_Fund.pdf

# URL
python analyze.py "https://file.notion.so/f/f/4ca3621f-ff13-4a92-b9af-13f5359fce08/1da321a8-a16f-473f-8647-a60569e5935c/FY25_Air_Force_Working_Capital_Fund.pdf?table=block&id=355cc2a5-3b3a-80e9-a0be-d3bbca52b816&spaceId=4ca3621f-ff13-4a92-b9af-13f5359fce08&expirationTimestamp=1778157828100&signature=mdrN6CzCbbKMF_xdnRGrq-0kttj-BEQJUSwrksGcGNE&downloadName=FY25+Air+Force+Working+Capital+Fund.pdf"
```

## Output

```
============================================================
FINAL RESULTS
============================================================
max_numerical_raw     : 6,000,000.00
  Number in document  : '$6,000,000'
  Found at            : page 93, table 1, row 6
  Context             : '...This category includes an array of minor construction projects
                         that allows flexibility in adapting to new and changing workloads.
                         Projects are smaller in scale (costing between $250,000 and
                         $6,000,000) and are designed, scheduled, and constructed in
                         accordance with Air Logistic Complexes' established priorities...'

max_numerical_adjusted: 30,704,100,000.00
  Number in document  : '30,704.1' x millions
  Found at            : page 13, table 1, row 2
  Context             : '...Total Revenue Total Revenue 28,239.2 29,176.6 30,704.1
                         Cost of Goods Sold Cost of Goods Sold 27,950.4 29,494.7 30,083.2
                         Net Operating Result (NOR) 293.8 (364.7) 622.9...'

============================================================
```