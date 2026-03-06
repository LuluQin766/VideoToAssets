#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志工具模块
提供统一的日志记录功能
"""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from datetime import datetime
from config import LOG_DIR, ENABLE_LOGGING, LOG_LEVEL, LOG_MAX_SIZE_MB, LOG_BACKUP_COUNT, LOG_FORMAT, LOG_DATE_FORMAT

def setup_logger(name, log_file=None, level=None):
    """设置并返回日志记录器
    
    Args:
        name: 日志记录器名称（通常是模块名）
        log_file: 日志文件路径（默认使用配置的日志目录）
        level: 日志级别（默认使用配置的级别）
    
    Returns:
        logger: 配置好的日志记录器
    """
    logger = logging.getLogger(name)
    
    # 如果已经配置过，直接返回
    if logger.handlers:
        return logger
    
    # 设置日志级别
    log_level = getattr(logging, level or LOG_LEVEL, logging.INFO)
    logger.setLevel(log_level)
    
    # 如果禁用日志，只使用 NullHandler
    if not ENABLE_LOGGING:
        logger.addHandler(logging.NullHandler())
        return logger
    
    # 创建格式器
    formatter = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)
    
    # 控制台处理器（输出到标准输出）
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 文件处理器（如果指定了日志文件）
    if log_file:
        log_path = Path(log_file)
        if not log_path.is_absolute():
            log_path = LOG_DIR / log_path
        
        # 确保日志目录存在
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 使用 RotatingFileHandler 实现日志轮转
        max_bytes = LOG_MAX_SIZE_MB * 1024 * 1024  # 转换为字节
        file_handler = RotatingFileHandler(
            log_path,
            maxBytes=max_bytes,
            backupCount=LOG_BACKUP_COUNT,
            encoding='utf-8'
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger

def get_log_file_name(script_name, suffix=''):
    """生成日志文件名
    
    Args:
        script_name: 脚本名称（不含扩展名）
        suffix: 文件名后缀（可选）
    
    Returns:
        日志文件路径
    """
    timestamp = datetime.now().strftime('%Y%m%d')
    if suffix:
        return f"{script_name}_{suffix}_{timestamp}.log"
    return f"{script_name}_{timestamp}.log"

