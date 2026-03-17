import os

basedir = os.path.abspath(os.path.dirname(__file__))


class BaseConfig:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-insecure-key-change-in-production')
    DATABASE_PATH = os.environ.get(
        'DATABASE_PATH',
        os.path.join(basedir, 'instance', 'novalis.db')
    )
    UPLOAD_FOLDER = os.path.join(basedir, 'uploads')
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB
    ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'xlsx'}

    GOOGLE_CREDENTIALS_B64 = os.environ.get('GOOGLE_CREDENTIALS_B64')
    USE_MOCK_OCR = False

    KNOWN_EMPLOYEES = [
        'Dwayne', 'Logan', 'Reed', 'Chad', 'Mikey', 'Ricky',
        'Carlos', 'Jorge', 'James', 'David', 'Nikk', 'Colton',
        'Carl', 'Rodney', 'Juan', 'Mark', 'Justin', 'Gerrod',
        'Daniel', 'Jydon',
    ]

    KNOWN_DEPARTMENTS = ['Extrusion', 'Finishing', 'UV', 'Regrind']

    FUZZY_EMPLOYEE_THRESHOLD = 70
    FUZZY_DEPARTMENT_THRESHOLD = 75
    FUZZY_PART_THRESHOLD = 65


class DevelopmentConfig(BaseConfig):
    DEBUG = True
    USE_MOCK_OCR = True


class ProductionConfig(BaseConfig):
    DEBUG = False


config_map = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
}
