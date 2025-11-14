import os
from typing import Optional


def load_banner() -> str:
    """Загружает баннер из файла с обработкой ошибок."""
    try:
        banner_path = "resources/banner.txt"
        if os.path.exists(banner_path):
            with open(banner_path, "r", encoding="utf-8") as f:
                banner = f.read()
                # Добавляем невидимый символ в начало первой строки
                lines = banner.split('\n')
                if lines and lines[0].startswith(' '):
                    lines[0] = '\u200B' + lines[0]  # Zero-width space
                banner = '\n'.join(lines)
                return banner

        # Fallback banner
        return """
╔════════════════════════════════════════════════════════════════════════╗
║                           BIG BROTHER SCANNER                         ║
║                   Advanced Subdomain Discovery Tool                   ║
╚════════════════════════════════════════════════════════════════════════╝
"""
    except Exception as e:
        return f"""
╔════════════════════════════════════════════════════════════════════════╗
║                           BIG BROTHER SCANNER                         ║
║                   Error loading banner: {str(e):<20}           ║
╚════════════════════════════════════════════════════════════════════════╝
"""