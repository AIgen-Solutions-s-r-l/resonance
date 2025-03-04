if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",  # Passa l'applicazione come stringa di importazione
        host="0.0.0.0",
        port=8016,
        reload=True,  # Attiva il riavvio automatico quando i file cambiano
    )
