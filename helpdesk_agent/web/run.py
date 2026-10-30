import uvicorn

if __name__ == "__main__":
    print("🚀 Starting CampusOS AI Helpdesk SaaS Platform on http://127.0.0.1:8000 ...")
    uvicorn.run("web.app:app", host="0.0.0.0", port=8000, reload=True)


# uv run python web/run.py