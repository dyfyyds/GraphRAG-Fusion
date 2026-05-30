from app.exceptions import register_exception_handlers


def setup_exception_handlers(app):
    register_exception_handlers(app)
