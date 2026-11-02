from pathlib import Path
 
import logging
import pandas as pd
import json
import yaml
 
 
# Use the logging configuration from Part 1.
logger = logging.getLogger(__name__)
 
 
def load_csv(filepath):
    df = pd.read_csv(filepath)
    logger.info("Loaded CSV file: %s (%d rows)", filepath, len(df))
    return df

def load_json(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    logger.info("Loaded JSON file: %s", filepath)
    return data


def load_yaml(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    logger.info("Loaded YAML file: %s", filepath)
    return data



def load_data(filepath):
    path = Path(filepath)
    extension = path.suffix.lower()
 
    if extension == ".csv":
        return load_csv(path)
    elif extension == ".json":
        return load_json(path)
    elif extension == ".yaml":
        return load_yaml(path)
    else:
        logger.error("Unsupported file format: %s", extension)
        raise ValueError(f"Unsupported file format: {extension}")
    