# Snippy

A tool for searching academic articles using Crossref and filtering for JUFO rankings.

## Setup

1. Install dependencies: `pip install -r requirements.txt`
2. Set up environment variables (see `.env.example`)
3. Run locally: `python app.py`
4. Deploy to Vercel: `vercel`

## Features

- Search academic articles with keyword filtering
- Filter by JUFO rankings
- Save searches and organize into projects
- Download results as CSV

## Vercel Deployment

This application is designed to be deployed on Vercel using:
- Vercel Blob for storing search results and project data
- Vercel Edge Config for caching JUFO rankings and configuration

See `vercel.json` for configuration details.
