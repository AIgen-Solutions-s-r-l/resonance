import nest_asyncio

# Applica la patch di nest_asyncio
nest_asyncio.apply()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",  # Passa l'applicazione come stringa di importazione
        host="0.0.0.0",
        port=9006,
        reload=True  # Attiva il riavvio automatico quando i file cambiano
    )
