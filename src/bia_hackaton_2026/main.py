from fastapi import FastAPI
from bia_hackaton_2026.whatsapp.webhook import router as whatsapp_router

app = FastAPI(title="Sahayi - Voice Assistance & SOS System")

# Mount WhatsApp webhook router
app.include_router(whatsapp_router)


@app.get("/health")
def health_check() -> dict:
    """Service health check endpoint."""
    return {"status": "healthy", "service": "sahayi-backend"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("bia_hackaton_2026.main:app", host="0.0.0.0", port=8000, reload=True)

