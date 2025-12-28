import os
import logging

class BaseConfig:
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "dev-secret-key-change-in-production")
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "lsfile")
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", 16777216))
    LOG_LEVEL = getattr(logging, os.getenv("LOG_LEVEL", "INFO"))

class DevConfig(BaseConfig):
    DEBUG = True

class TestConfig(BaseConfig):
    TESTING = True
    DEBUG = False

class ProdConfig(BaseConfig):
    DEBUG = False
