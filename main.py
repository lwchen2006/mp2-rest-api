import io
import json
import logging
from pathlib import Path
import pandas as pd
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from data_pipeline import create_cleaning_report, process_data, validate_dataframe
from src import (
    DatasetInfo,
    DatasetStorage,
    HealthResponse,
    ProcessConfig,
    ProcessingReport,
    log_requests,
    setup_logging,
)

setup_logging(verbose=True)
logger = logging.getLogger(__name__)

app = FastAPI(title="Data Processing API", version="1.0.0")
app.middleware("http")(log_requests)
storage = DatasetStorage()


@app.get("/health", response_model=HealthResponse)
def health_check():
    """Return the application status and version."""
    return {"status": "ok", "version": "1.0.0"}


@app.post("/upload", response_model=DatasetInfo)
async def upload_dataset(file: UploadFile = File(...)):
    """Read and store a CSV upload."""
    suffix = Path(file.filename or "").suffix.lower()
    if suffix != ".csv":
        logger.warning("Unsupported file format: %s", suffix)
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format: {suffix or 'none'}. Upload a .csv file.",
        )

    contents = await file.read()
    try:
        df = pd.read_csv(io.BytesIO(contents))
    except (pd.errors.EmptyDataError, pd.errors.ParserError, UnicodeDecodeError) as error:
        logger.warning("Could not read CSV %s: %s", file.filename, error)
        raise HTTPException(
            status_code=400, detail=f"Could not read CSV file: {error}"
        )

    dataset_id = storage.save(df, file.filename)
    logger.info(
        "Uploaded dataset: id=%s, filename=%s, rows=%s",
        dataset_id,
        file.filename,
        len(df),
    )
    return storage.get_metadata(dataset_id)


@app.get("/datasets/{dataset_id}")
def get_dataset(dataset_id: int, limit: int = Query(default=100, ge=1)):
    """Return up to limit rows from a stored dataset."""
    df = storage.get(dataset_id)
    if df is None:
        logger.warning("Dataset not found: %s", dataset_id)
        raise HTTPException(status_code=404, detail=f"Dataset {dataset_id} not found")

    records = json.loads(df.head(limit).to_json(orient="records"))
    logger.info("Retrieved dataset: id=%s, returned_rows=%s", dataset_id, len(records))
    return {"id": dataset_id, "data": records, "total_rows": len(df)}


@app.post("/datasets/{dataset_id}/process", response_model=ProcessingReport)
def process_dataset(dataset_id: int, config: ProcessConfig):
    """Validate and process a stored dataset using MP1 functions."""
    df = storage.get(dataset_id)
    if df is None:
        logger.warning("Dataset not found: %s", dataset_id)
        raise HTTPException(status_code=404, detail=f"Dataset {dataset_id} not found")

    config_dict = config.model_dump()
    validation = config_dict["validation"]

    try:
        for column in validation["numeric_columns"]:
            if column not in df.columns:
                raise ValueError(f"Missing numeric column: {column}")

        validated = validate_dataframe(
            df, validation["required_columns"], validation["numeric_columns"]
        )
        validation_rows_removed = len(df) - len(validated)
        validated = validated.copy()

        processed = process_data(validated, config_dict)
        report = create_cleaning_report(validated, processed)
    except ValueError as error:
        logger.warning("Processing failed for dataset %s: %s", dataset_id, error)
        raise HTTPException(status_code=400, detail=str(error))

    storage.update(dataset_id, processed)
    logger.info(
        "Processed dataset: id=%s, validation_removed=%s, rows_before=%s, rows_after=%s",
        dataset_id,
        validation_rows_removed,
        report["rows_before"],
        report["rows_after"],
    )
    return {
        "id": dataset_id,
        "validation_rows_removed": validation_rows_removed,
        "cleaning_report": report,
    }
