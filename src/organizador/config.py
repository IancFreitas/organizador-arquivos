"""Categorias de arquivos e carregamento de configuração personalizada."""

from __future__ import annotations

import tomllib
from pathlib import Path

DEFAULT_CATEGORIES: dict[str, list[str]] = {
    "Imagens": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp", ".heic"],
    "Documentos": [".pdf", ".doc", ".docx", ".odt", ".txt", ".rtf", ".md"],
    "Planilhas": [".xls", ".xlsx", ".ods", ".csv"],
    "Apresentacoes": [".ppt", ".pptx", ".odp"],
    "Videos": [".mp4", ".mkv", ".avi", ".mov", ".wmv"],
    "Audios": [".mp3", ".wav", ".flac", ".ogg", ".m4a"],
    "Compactados": [".zip", ".rar", ".7z", ".tar", ".gz"],
    "Instaladores": [".exe", ".msi", ".dmg", ".deb", ".apk"],
    "Codigo": [".py", ".js", ".ts", ".html", ".css", ".json", ".java", ".cs", ".sql"],
}

FALLBACK_CATEGORY = "Outros"

# Downloads ainda em andamento: mover esses arquivos corromperia o download.
IGNORED_SUFFIXES = frozenset({".crdownload", ".part", ".partial", ".tmp", ".download"})


class ConfigError(Exception):
    """Arquivo de configuração inválido."""


def load_extension_map(config_path: Path | None = None) -> dict[str, str]:
    """Retorna um mapa ``extensão -> categoria``.

    Sem ``config_path`` usa as categorias padrão. O arquivo TOML deve ter uma
    tabela ``[categorias]`` em que cada chave é o nome da pasta e o valor é a
    lista de extensões, por exemplo ``Fotos = ["jpg", "png"]``.
    """
    if config_path is None:
        return build_extension_map(DEFAULT_CATEGORIES)

    try:
        with config_path.open("rb") as file:
            data = tomllib.load(file)
    except FileNotFoundError as error:
        raise ConfigError(f"Arquivo de configuração não encontrado: {config_path}") from error
    except tomllib.TOMLDecodeError as error:
        raise ConfigError(f"TOML inválido em {config_path}: {error}") from error

    categories = data.get("categorias")
    if not isinstance(categories, dict) or not categories:
        raise ConfigError(f"{config_path} precisa ter uma tabela [categorias] não vazia.")

    for name, extensions in categories.items():
        if not isinstance(extensions, list) or not all(isinstance(e, str) for e in extensions):
            raise ConfigError(f"A categoria '{name}' deve ser uma lista de extensões (texto).")

    return build_extension_map(categories)


def build_extension_map(categories: dict[str, list[str]]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for category, extensions in categories.items():
        for extension in extensions:
            normalized = extension.strip().lower()
            if not normalized.startswith("."):
                normalized = f".{normalized}"
            mapping[normalized] = category
    return mapping
