from dataclasses import dataclass
from enum import Enum

from config.base import RateLimitConfig, StorageConfig


class EditConfig:
    # Path Where Indices are Downloaded
    INDICES_DOWNLOAD_PATH = StorageConfig().tmp_root("nse", "indices")

    # Table ID where Industry Classification is Downloaded
    CLASSIFICATION_TABLE_ID = "industry_classification"
    FAILED_CLASSIFICATION_TABLE_ID = "industry_classification_failed"


class DownloadSoure(Enum):
    NSE = "nse"
    NSE_INDICES = "nse_indices"


@dataclass
class IndexConfig:
    name: str
    url: str
    filename: str
    source: DownloadSoure


class NSEConfig(EditConfig):
    NSE_URL = "https://www.nseindia.com"
    INDICES_DOWNLOAD_RATE_LIMIT = RateLimitConfig(calls=1, period=10)
    SECTOR_INDICES = [
        IndexConfig(
            name="NIFTY AUTO",
            url="https://www.niftyindices.com/indices/equity/sectoral-indices/nifty-auto",
            filename="nse_index_nifty_auto.csv",
            source=DownloadSoure.NSE_INDICES,
        ),
        IndexConfig(
            name="NIFTY BANK",
            url="https://www.niftyindices.com/indices/equity/sectoral-indices/nifty-bank",
            filename="nse_index_nifty_bank.csv",
            source=DownloadSoure.NSE_INDICES,
        ),
        IndexConfig(
            name="NIFTY CEMENT",
            url="https://niftyindices.com/indices/equity/sectoral-indices/nifty-cement",
            filename="nse_index_nifty_cement.csv",
            source=DownloadSoure.NSE_INDICES,
        ),
        IndexConfig(
            name="NSE INDEX NIFTY CHEMICALS",
            url="https://niftyindices.com/indices/equity/sectoral-indices/nifty-chemicals",
            filename="nse_index_nifty_chemical.csv",
            source=DownloadSoure.NSE_INDICES,
        ),
        IndexConfig(
            name="NIFTY FINANCIAL SERVICES",
            url="https://www.niftyindices.com/indices/equity/sectoral-indices/nifty-financial-services",
            filename="nse_index_nifty_financial_services.csv",
            source=DownloadSoure.NSE_INDICES,
        ),
        IndexConfig(
            name="NIFTY FINSRV25 50",
            url="https://www.niftyindices.com/indices/equity/sectoral-indices/nifty-financial-services-25-50-index",
            filename="nse_index_nifty_financial_services_25_50.csv",
            source=DownloadSoure.NSE_INDICES,
        ),
        IndexConfig(
            name="NIFTY FMCG",
            url="https://www.niftyindices.com/indices/equity/sectoral-indices/nifty-fmcg",
            filename="nse_index_nifty_fmcg.csv",
            source=DownloadSoure.NSE_INDICES,
        ),
        IndexConfig(
            name="NIFTY HEALTHCARE",
            url="https://www.niftyindices.com/indices/equity/sectoral-indices/nifty-healthcare-index",
            filename="nse_index_nifty_healthcare.csv",
            source=DownloadSoure.NSE_INDICES,
        ),
        IndexConfig(
            name="NIFTY IT",
            url="https://www.niftyindices.com/indices/equity/sectoral-indices/nifty-it",
            filename="nse_index_nifty_it.csv",
            source=DownloadSoure.NSE_INDICES,
        ),
        IndexConfig(
            name="NIFTY MEDIA",
            url="https://www.niftyindices.com/indices/equity/sectoral-indices/nifty-media",
            filename="nse_index_nifty_media.csv",
            source=DownloadSoure.NSE_INDICES,
        ),
        IndexConfig(
            name="NIFTY METAL",
            url="https://www.niftyindices.com/indices/equity/sectoral-indices/nifty-metal",
            filename="nse_index_nifty_metal.csv",
            source=DownloadSoure.NSE_INDICES,
        ),
        IndexConfig(
            name="NIFTY PHARMA",
            url="https://www.niftyindices.com/indices/equity/sectoral-indices/nifty-pharma",
            filename="nse_index_nifty_pharma.csv",
            source=DownloadSoure.NSE_INDICES,
        ),
        IndexConfig(
            name="NIFTY PVT BANK",
            url="https://www.niftyindices.com/indices/equity/sectoral-indices/nifty-private-bank",
            filename="nse_index_nifty_private_bank.csv",
            source=DownloadSoure.NSE_INDICES,
        ),
        IndexConfig(
            name="NIFTY PSU BANK",
            url="https://www.niftyindices.com/indices/equity/sectoral-indices/nifty-psu-bank",
            filename="nse_index_nifty_psu_bank.csv",
            source=DownloadSoure.NSE_INDICES,
        ),
        IndexConfig(
            name="NIFTY REALTY",
            url="https://www.niftyindices.com/indices/equity/sectoral-indices/nifty-realty",
            filename="nse_index_nifty_realty.csv",
            source=DownloadSoure.NSE_INDICES,
        ),
        IndexConfig(
            name="NIFTY REIT REALTY",
            url="https://niftyindices.com/indices/equity/sectoral-indices/nifty-reits-realty",
            filename="nse_index_nifty_reits_realty.csv",
            source=DownloadSoure.NSE_INDICES,
        ),
        IndexConfig(
            name="NIFTY CONSR DURBL",
            url="https://www.niftyindices.com/indices/equity/sectoral-indices/nifty-consumer-durables-index",
            filename="nse_index_nifty_consumer_durables.csv",
            source=DownloadSoure.NSE_INDICES,
        ),
        IndexConfig(
            name="NIFTY OIL AND GAS",
            url="https://www.niftyindices.com/indices/equity/sectoral-indices/nifty-oil-and-gas-index",
            filename="nse_index_nifty_oil_gas.csv",
            source=DownloadSoure.NSE_INDICES,
        ),
        IndexConfig(
            name="NIFTY500 HEALTH",
            url="https://niftyindices.com/indices/equity/sectoral-indices/nifty500-healthcare",
            filename="nse_index_nifty_500_healthcare.csv",
            source=DownloadSoure.NSE_INDICES,
        ),
        IndexConfig(
            name="NIFTY MIDSMALL FINANCIAL SERVICES",
            url="https://www.niftyindices.com/indices/equity/sectoral-indices/nifty-midsmall-financial-services",
            filename="nse_index_nifty_mid_small_financial_services.csv",
            source=DownloadSoure.NSE_INDICES,
        ),
        IndexConfig(
            name="NIFTY MID SMALL HEALTHCARE",
            url="https://www.niftyindices.com/indices/equity/sectoral-indices/nifty-midsmall-healthcare",
            filename="nse_index_nifty_mid_small_healthcare.csv",
            source=DownloadSoure.NSE_INDICES,
        ),
        IndexConfig(
            name="NIFTY MIDSMALL IT & TELECOM",
            url="https://www.niftyindices.com/indices/equity/sectoral-indices/nifty-midsmall-it-telecom",
            filename="nse_index_nifty_mid_small_it_telecom.csv",
            source=DownloadSoure.NSE_INDICES,
        ),
    ]

    MARKET_INDICES = [
        IndexConfig(
            name="NIFTY 50",
            url="https://www.nseindia.com/static/products-services/indices-nifty50-index",
            filename="nse_index_nifty_50.csv",
            source=DownloadSoure.NSE,
        ),
        IndexConfig(
            name="NIFTY NEXT 50",
            url="https://www.nseindia.com/static/products-services/indices-niftynext50-index",
            filename="nse_index_nifty_next_50.csv",
            source=DownloadSoure.NSE,
        ),
        IndexConfig(
            name="NIFTY 100",
            url="https://www.nseindia.com/static/products-services/indices-nifty100-index",
            filename="nse_index_nifty_100.csv",
            source=DownloadSoure.NSE,
        ),
        IndexConfig(
            name="NIFTY 200",
            url="https://www.nseindia.com/static/products-services/indices-nifty200-index",
            filename="nse_index_nifty_200.csv",
            source=DownloadSoure.NSE,
        ),
        IndexConfig(
            name="NIFTY TOTAL MKT",
            url="https://www.nseindia.com/static/products-services/indices-nifty-total-market-index",
            filename="nse_index_nifty_total_market.csv",
            source=DownloadSoure.NSE,
        ),
        IndexConfig(
            name="NIFTY 500",
            url="https://www.nseindia.com/static/products-services/indices-nifty500-index",
            filename="nse_index_nifty_500.csv",
            source=DownloadSoure.NSE,
        ),
        IndexConfig(
            name="NIFTY500 MULTICAP",
            url="https://www.nseindia.com/static/products-services/indices-nifty500-multicap-50-25-25-index",
            filename="nse_index_nifty_500_multicap_50_25_25.csv",
            source=DownloadSoure.NSE,
        ),
        IndexConfig(
            name="NIFTY SMLCAP 250",
            url="https://www.nseindia.com/static/products-services/indices-niftysmallcap250-index",
            filename="nse_index_nifty_smallcap_250.csv",
            source=DownloadSoure.NSE,
        ),
    ]
