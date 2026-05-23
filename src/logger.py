# src/logger.py
import logging
import sys
import os
from pathlib import Path

def get_logger(name="RocoNav"):
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(filename)s:%(lineno)d - %(message)s')
        
        # 强制将日志输出到 D:\github\Roco\roco_debug.log
        log_path = Path(__file__).parent.parent / 'roco_debug.log'
        fh = logging.FileHandler(str(log_path), encoding='utf-8')
        fh.setFormatter(formatter)
        logger.addHandler(fh)
        
        # 同时输出到控制台
        ch = logging.StreamHandler(sys.stdout)
        ch.setFormatter(formatter)
        logger.addHandler(ch)
        
    return logger