import os


def get_project_root():
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def get_models_dir():
    return os.getenv("AIALAVIC_MODELS_DIR", os.path.join(get_project_root(), "models"))


def get_downloads_dir():
    return os.getenv("AIALAVIC_DOWNLOADS_DIR", os.path.join(get_models_dir(), "downloads"))


def apply_proxy_env():
    proxy_url = os.getenv("AIALAVIC_PROXY_URL", "").strip()
    if proxy_url:
        os.environ["HTTP_PROXY"] = proxy_url
        os.environ["HTTPS_PROXY"] = proxy_url


def require_env(name):
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value
