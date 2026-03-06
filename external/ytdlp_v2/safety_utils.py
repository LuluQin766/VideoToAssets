#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
安全工具模块
提供速率控制、错误检测等安全功能
"""

import time
from config import (
    REQUEST_DELAY, RATE_LIMIT_EXTRA_DELAY, RATE_LIMIT_MAX_RETRIES,
    USER_AGENT, CUSTOM_HEADERS,
    YT_DLP_DEFAULT_OPTS
)

def is_rate_limit_error(error):
    """检测是否是速率限制错误
    
    Args:
        error: 异常对象或错误字符串
    
    Returns:
        bool: 是否是速率限制错误
    """
    error_str = str(error).lower()
    # 检测常见的速率限制错误信息
    rate_limit_indicators = [
        '429',
        'too many requests',
        'rate limit',
        'quota exceeded',
        'http error 429',
        'http 429',
        'quotaexceeded',
        'ratelimitexceeded'
    ]
    return any(indicator in error_str for indicator in rate_limit_indicators)

def is_ip_blocked_error(error):
    """检测是否是IP封禁错误
    
    Args:
        error: 异常对象或错误字符串
    
    Returns:
        bool: 是否是IP封禁错误
    """
    error_str = str(error).lower()
    # 检测常见的IP封禁错误信息
    ip_block_indicators = [
        '403',
        'forbidden',
        'ip blocked',
        'access denied',
        'http error 403',
        'http 403',
        'blocked',
        'banned'
    ]
    return any(indicator in error_str for indicator in ip_block_indicators)

def get_ydl_opts(base_opts=None, **extra_opts):
    """获取配置好的 yt-dlp 选项，包括用户代理和自定义请求头
    
    Args:
        base_opts: 基础选项字典（默认使用 YT_DLP_DEFAULT_OPTS）
        **extra_opts: 额外的选项
    
    Returns:
        配置好的选项字典
    """
    if base_opts is None:
        opts = YT_DLP_DEFAULT_OPTS.copy()
    else:
        opts = base_opts.copy()
    
    # 添加用户代理
    if USER_AGENT:
        opts['user_agent'] = USER_AGENT
    
    # 添加自定义请求头
    if CUSTOM_HEADERS:
        if 'http_headers' not in opts:
            opts['http_headers'] = {}
        opts['http_headers'].update(CUSTOM_HEADERS)
    
    # 添加额外选项
    opts.update(extra_opts)
    
    return opts

def apply_request_delay():
    """应用请求延迟（如果配置了）"""
    if REQUEST_DELAY > 0:
        time.sleep(REQUEST_DELAY)

def handle_rate_limit_error(error, logger=None, retry_count=0):
    """处理速率限制错误
    
    Args:
        error: 错误对象
        logger: 日志记录器（可选）
        retry_count: 当前重试次数
    
    Returns:
        int: 建议的等待时间（秒），如果应该放弃则返回 -1
    """
    if not is_rate_limit_error(error):
        return 0
    
    if retry_count >= RATE_LIMIT_MAX_RETRIES:
        if logger:
            logger.error(f"⚠️  速率限制重试次数已达上限 ({RATE_LIMIT_MAX_RETRIES})，建议停止运行")
        return -1
    
    wait_time = RATE_LIMIT_EXTRA_DELAY * (retry_count + 1)
    if logger:
        logger.warning(f"⚠️  检测到速率限制，等待 {wait_time} 秒后重试 ({retry_count + 1}/{RATE_LIMIT_MAX_RETRIES})")
    
    return wait_time

def handle_ip_block_error(error, logger=None):
    """处理IP封禁错误
    
    Args:
        error: 错误对象
        logger: 日志记录器（可选）
    
    Returns:
        bool: 是否应该停止运行
    """
    if not is_ip_blocked_error(error):
        return False
    
    if logger:
        logger.error("🚨 检测到IP可能被封禁！建议立即停止运行并等待 24-48 小时")
    
    return True

