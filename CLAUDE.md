# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

GithubTrending is a Chinese-language GitHub trending repositories scraper that automatically fetches top 10 trending repositories and displays them in a beautiful HTML interface with AI-generated Chinese summaries. The project runs on GitHub Actions daily at 10 AM Beijing time.

## Key Commands

### Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run main script (generates HTML output)
python github_trending_cards.py

# Generate history statistics page
python generate_history_stats.py

# Test network connectivity
python test_network.py
```

### Testing
```bash
# Run network diagnostics
python test_network.py

# Test web scraping locally
python github_trending_cards.py --dry-run  # If implemented
```

## Architecture

### Core Scripts
- **github_trending_cards.py**: Main scraper that fetches GitHub trending data, optionally generates AI summaries via OpenRouter API, and creates HTML cards
- **generate_history_stats.py**: Scans history/ directory and generates statistics/overview pages for historical data
- **test_network.py**: Network connectivity diagnostics tool

### Data Flow
1. GitHub Actions triggers daily at UTC 2:00 (Beijing 10:00 AM)
2. Script scrapes GitHub trending pages (daily/weekly/monthly)
3. Optionally generates Chinese AI summaries via OpenRouter API
4. Creates HTML cards with repository information
5. Saves historical data to `history/YYYY-MM-DD/` directories
6. Deploys to GitHub Pages via gh-pages branch

### Key Directories
- **history/**: Contains dated subdirectories with archived trending data
- **publish/**: Temporary directory for GitHub Pages deployment
- **.github/workflows/**: CI/CD automation configuration

### External Dependencies
- **GitHub API**: Scrapes trending repositories from github.com
- **OpenRouter API**: Optional AI summary generation (requires API key)

## Important Implementation Details

### Web Scraping Strategy
- Uses BeautifulSoup to parse GitHub's trending pages
- Handles network errors with comprehensive retry logic
- Supports multiple timeframes: daily, weekly, monthly
- Implements rate limiting and user-agent headers

### Historical Data Management
- Automatically saves daily snapshots to gh-pages branch
- Each historical entry contains: HTML page, CSS, metadata.json
- History statistics page provides overview of all archived data
- Data integrity checks ensure completeness

### Error Handling
- Network connectivity issues are handled gracefully
- GitHub Actions continues on error for non-critical steps
- Comprehensive logging for debugging deployment issues
- Fallback mechanisms for API failures

### Deployment
- Uses GitHub Actions for automated daily updates
- Deploys to GitHub Pages on gh-pages branch
- Preserves historical data during deployments
- Network diagnostics run before main script execution