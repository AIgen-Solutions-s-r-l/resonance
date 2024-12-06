# app/main.py

import asyncio
from typing import Dict

from fastapi import FastAPI, HTTPException
from loguru import logger

from app.core.config import Settings
from app.core.logging_config import (
    setup_logging,
    get_logger_context,
    LoggingConfig,
)
from app.routers.jobs_matched_router import router as jobs_router  # Importa il router dei lavori

settings = Settings()

# Configura il logging
logging_config = LoggingConfig(
    service_name=settings.service_name,
    log_level=settings.log_level,
    logstash_host=settings.logstash_host,
    logstash_port=settings.logstash_port,
    enable_file_logging=True,
    enable_console_logging=True,
    enable_logstash=settings.enable_logstash,
    environment=settings.environment,
)

# Inizializza il logging
setup_logging(logging_config)

# Test della connessione Logstash se abilitato
if settings.enable_logstash:
    from app.core.logging_config import test_logstash_connection  # Importa qui per evitare import circolari

    if test_logstash_connection(settings.logstash_host, settings.logstash_port):
        logger.info("Logstash connection successful")
    else:
        logger.warning("Logstash connection failed, continuing with local logging only")

async def lifespan(app: FastAPI):
    """
    Gestisce l'avvio e lo spegnimento dell'applicazione.

    Args:
        app: Istanza dell'applicazione FastAPI
    """
    context = get_logger_context(action="lifespan")

    try:
        logger.info("Starting application", context)
        # Inizializza eventuali compiti di avvio qui
        yield
        logger.info("Shutting down application", context)
        # Finalizza eventuali compiti di spegnimento qui
    except Exception as e:
        context["error"] = str(e)
        logger.error("Application lifecycle error", context)
        raise

app = FastAPI(
    lifespan=lifespan,
    title="Job Matching API",
    description="API for matching jobs with user resumes.",
    version="1.0.0",
)

# Includi il router dei lavori
app.include_router(jobs_router)

@app.get("/")
async def root() -> Dict[str, str]:
    """
    Endpoint di controllo dello stato di salute.

    Returns:
        Dict contenente il messaggio di stato del servizio
    """
    context = get_logger_context(action="health_check")
    logger.info("Health check requested", context)
    return {"message": "Matching Service is running!"}

