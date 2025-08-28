# pipeline_covid/definitions.py
from dagster import (
    Definitions,
    load_assets_from_modules,
    load_asset_checks_from_modules,
    FilesystemIOManager,
)
from . import assets, checks

all_assets = load_assets_from_modules([assets])
all_checks = load_asset_checks_from_modules([checks])

# Guarda artefactos en ./storage (persistente y estable)
io_manager = FilesystemIOManager(base_dir="storage")

defs = Definitions(
    assets=all_assets,
    asset_checks=all_checks,
    resources={"io_manager": io_manager},
)
