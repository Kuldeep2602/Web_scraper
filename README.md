
# Apache Jira Data Scraper for LLM Training

This tool scrapes public issue data from Apache's Jira and transforms it into LLM-ready datasets.

## Features
- Async, high-throughput scraping via Jira REST API
- Checkpoint/resume for fault tolerance
- Rate limiting and error handling
- Multi-task data transformation (summarization, classification, Q&A, etc.)
- Outputs clean JSONL for LLM training

## Quick Start

```bash
# Clone and setup
git clone <repository-url>
cd web_scraper
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt

# Run
python run.py --projects KAFKA SPARK AIRFLOW
```

## Configuration
Edit `.env` to set projects, rate limits, output paths, etc.

## Usage
Run with default settings:
```
python run.py
```
Advanced options:
```
python run.py --projects KAFKA SPARK
python run.py --rate-limit 5 --max-concurrent 3
python run.py --resume
```

## Output
- Project and combined JSONL files in `output/`
- Each line: `{ "task": ..., "input": ..., "output": ..., "metadata": ... }`
## Project Structure

```
web_scraper/
├── src/
│   ├── api_client.py          # Async HTTP client with retry logic
│   ├── state_manager.py       # Checkpoint system
│   ├── scraper.py             # Main scraping logic
│   ├── transformer.py         # Data transformation
│   ├── config.py              # Configuration
│   ├── logger.py              # Logging setup
│   └── main.py                # Entry point
├── run.py                      # CLI interface
├── utils.py                    # Analysis utilities
├── test_setup.py              # Installation tests
├── setup.bat / setup.sh       # Setup scripts
├── requirements.txt           # Dependencies
├── .env.                      # Config template
├── README.md                  # Main docs

```



## Testing & Validation
- Use `utils.py` for analysis, sampling, and validation:
```
python utils.py analyze output/combined_training_data.jsonl
python utils.py sample output/combined_training_data.jsonl --n 5
python utils.py validate output/combined_training_data.jsonl
```


## Architecture Overview
The pipeline is modular and async, built around:
- **API Client:** Async Jira REST API client with retry, rate limiting, and connection pooling.
- **State Manager:** Atomic checkpointing for safe resume and fault tolerance.
- **Scraper:** Orchestrates async, concurrent data collection and progress tracking.
- **Transformer:** Cleans and transforms issues into multiple LLM tasks (summarization, classification, Q&A, etc.).
- **CLI & Utilities:** Easy command-line usage and data validation tools.

## Edge Cases Handled
- Network errors, timeouts, and rate limits (with retries and backoff)
- Server/API errors (429, 5xx, permission issues)
- Incomplete or malformed data (safe extraction, defaults)
- Interruption and resume (atomic state saves)
- Disk/memory issues (batch processing, atomic writes)

## Optimization Decisions
- Async I/O and connection pooling for high throughput
- Token bucket rate limiting to avoid bans
- Batch processing and checkpointing for efficiency and reliability
- Modular design for easy extension and maintenance





