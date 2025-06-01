import logging
import logging.config
import os
from datetime import datetime
from pythonjsonlogger import jsonlogger

def setup_logging(log_level: str = "INFO", log_file: str = "logs/app.log"):
    """Setup structured logging configuration"""
    
    # Ensure logs directory exists
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    
    # Custom JSON formatter
    class CustomJsonFormatter(jsonlogger.JsonFormatter):
        def add_fields(self, log_record, record, message_dict):
            super(CustomJsonFormatter, self).add_fields(log_record, record, message_dict)
            log_record['timestamp'] = datetime.utcnow().isoformat()
            log_record['level'] = record.levelname
            log_record['service'] = 'postnatal-stories-api'
            
            # Add request ID if available
            if hasattr(record, 'request_id'):
                log_record['request_id'] = record.request_id
    
    LOGGING_CONFIG = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'json': {
                '()': CustomJsonFormatter,
                'format': '%(timestamp)s %(level)s %(name)s %(message)s'
            },
            'standard': {
                'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
            },
        },
        'handlers': {
            'console': {
                'level': 'DEBUG',
                'class': 'logging.StreamHandler',
                'formatter': 'standard',
            },
            'file': {
                'level': 'INFO',
                'class': 'logging.handlers.RotatingFileHandler',
                'filename': log_file,
                'maxBytes': 10485760,  # 10MB
                'backupCount': 5,
                'formatter': 'json',
            },
            'error_file': {
                'level': 'ERROR',
                'class': 'logging.handlers.RotatingFileHandler',
                'filename': log_file.replace('.log', '_errors.log'),
                'maxBytes': 10485760,
                'backupCount': 5,
                'formatter': 'json',
            },
        },
        'loggers': {
            '': {  # root logger
                'handlers': ['console', 'file', 'error_file'],
                'level': log_level,
                'propagate': False
            },
            'uvicorn': {
                'handlers': ['console', 'file'],
                'level': 'INFO',
                'propagate': False
            },
            'uvicorn.access': {
                'handlers': ['file'],
                'level': 'INFO',
                'propagate': False
            },
        }
    }
    
    logging.config.dictConfig(LOGGING_CONFIG)

# Request ID middleware for tracing
from fastapi import Request
import uuid

async def add_request_id_middleware(request: Request, call_next):
    """Add unique request ID to each request for tracing"""
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    
    # Add to logging context
    old_factory = logging.getLogRecordFactory()
    
    def record_factory(*args, **kwargs):
        record = old_factory(*args, **kwargs)
        record.request_id = request_id
        return record
    
    logging.setLogRecordFactory(record_factory)
    
    try:
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
    finally:
        logging.setLogRecordFactory(old_factory)