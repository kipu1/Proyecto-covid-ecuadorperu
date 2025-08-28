from dagster import Definitions, load_assets_from_modules, load_asset_checks_from_modules
from . import assets, checks
from .definitions import defs

all_assets = load_assets_from_modules([assets])
all_checks = load_asset_checks_from_modules([checks])

defs = Definitions(assets=all_assets, asset_checks=all_checks)
