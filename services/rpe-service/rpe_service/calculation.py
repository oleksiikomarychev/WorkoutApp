import math
from typing import Dict, Optional, Union
import os
import json
from pathlib import Path
from typing import Dict, Union, Optional
import logging

logger = logging.getLogger(__name__)


#Преобразует строковые значения словаря в целые числа
def _normalize_int_keys(d):
    if isinstance(d, dict):
        out = {}
        for k, v in d.items():
            try:
                ik = int(k)
            except (TypeError, ValueError):
                ik = k
            out[ik] = _normalize_int_keys(v)
        return out
    return d
    
#Округляет значение до ближайшего кратного
def round_to_step(value: float, step: float, mode: str) -> float:
    if step <= 0:
        return value
    ratio = value / step
    if mode == 'floor':
        return math.floor(ratio) * step
    if mode == 'ceil':
        return math.ceil(ratio) * step
    return round(ratio) * step

    
#Проверяет структуру таблицы RPE на соответствие ожидаемому формату
def validate_rpe_table(table: Dict) -> bool:
    if not isinstance(table, dict):
        return False
    for intensity, efforts in table.items():
        if not isinstance(intensity, int) or not (40 <= intensity <= 100):
            return False
        if not isinstance(efforts, dict):
            return False
            
        for effort, reps in efforts.items():
            if not isinstance(effort, int) or not (1 <= effort <= 10):
                return False
            if not isinstance(reps, int) or not (1 <= reps <= 100):
                return False
    return True


#Загружает таблицу RPE из JSON-файла или переменной окружения
def load_rpe_table() -> Dict[int, Dict[int, int]]:
    default_json_path = Path(__file__).parent.parent / 'rpe_table.json'
    json_str = os.getenv('RPE_TABLE_JSON')
    json_path = os.getenv('RPE_TABLE_PATH', str(default_json_path))

    if json_str:
        try:
            data = json.loads(json_str)
            logger.info("Loaded RPE table from environment")
        except json.JSONDecodeError as e:
            logger.error("Invalid JSON in RPE_TABLE_JSON environment variable")
            raise RuntimeError("Invalid JSON in RPE_TABLE_JSON environment variable") from e
    else:
        if not os.path.exists(json_path):
            logger.error("RPE table file not found at %s", json_path)
            raise RuntimeError(f"RPE table file not found at {json_path}")
        try:
            with open(json_path, 'r') as f:
                data = json.load(f)
                logger.info("Loaded RPE table from file: %s", json_path)
        except (OSError, json.JSONDecodeError) as e:
            logger.error("Error reading RPE table from %s", json_path)
            raise RuntimeError(f"Error reading RPE table from {json_path}") from e

    try:
        return _normalize_int_keys(data)
    except Exception as e:
        logger.error("Error normalizing RPE table keys")
        raise RuntimeError("Error normalizing RPE table keys") from e

_RPE_TABLE_CACHE = None


#Возвращает кэшированную таблицу RPE (загружает при первом вызове)
def get_rpe_table() -> Dict[int, Dict[int, int]]:
    global _RPE_TABLE_CACHE
    if _RPE_TABLE_CACHE is None:
        _RPE_TABLE_CACHE = load_rpe_table()
        if not validate_rpe_table(_RPE_TABLE_CACHE):
            raise RuntimeError("Invalid RPE table structure")
    return _RPE_TABLE_CACHE
