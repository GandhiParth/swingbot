from dataclasses import dataclass
from enum import Enum

from config.base import RateLimitConfig

NSE_URL = "https://www.nseindia.com"


class DownloadSoure(Enum):
    NSE = "nse"
    NSE_INDICES = "nse_indices"


@dataclass
class IndexConfig:
    name: str
    url: str
    filename: str
    source: DownloadSoure


INDICES_DOWNLOAD_RATE_LIMIT = RateLimitConfig(calls=1, period=10)

SECTOR_INDICES = [
    IndexConfig(
        name="NIFTY_AUTO",
        url="https://www.niftyindices.com/indices/equity/sectoral-indices/nifty-auto",
        filename="nse_index_nifty_auto.csv",
        source=DownloadSoure.NSE_INDICES,
    ),
    IndexConfig(
        name="NIFTY_BANK",
        url="https://www.niftyindices.com/indices/equity/sectoral-indices/nifty-bank",
        filename="nse_index_nifty_bank.csv",
        source=DownloadSoure.NSE_INDICES,
    ),
    IndexConfig(
        name="NIFTY_CEMENT",
        url="https://niftyindices.com/indices/equity/sectoral-indices/nifty-cement",
        filename="nse_index_nifty_cement.csv",
        source=DownloadSoure.NSE_INDICES,
    ),
    IndexConfig(
        name="NIFTY_CHEMICAL",
        url="https://niftyindices.com/indices/equity/sectoral-indices/nifty-chemicals",
        filename="nse_index_nifty_chemical.csv",
        source=DownloadSoure.NSE_INDICES,
    ),
    IndexConfig(
        name="NIFTY_FINANCIAL_SERVICES",
        url="https://www.niftyindices.com/indices/equity/sectoral-indices/nifty-financial-services",
        filename="nse_index_nifty_financial_services.csv",
        source=DownloadSoure.NSE_INDICES,
    ),
    IndexConfig(
        name="NIFTY_FINANCIAL_SERVICES_25/50",
        url="https://www.niftyindices.com/indices/equity/sectoral-indices/nifty-financial-services-25-50-index",
        filename="nse_index_nifty_financial_services_25_50.csv",
        source=DownloadSoure.NSE_INDICES,
    ),
    IndexConfig(
        name="NIFTY_FMCG",
        url="https://www.niftyindices.com/indices/equity/sectoral-indices/nifty-fmcg",
        filename="nse_index_nifty_fmcg.csv",
        source=DownloadSoure.NSE_INDICES,
    ),
    IndexConfig(
        name="NIFTY_HEALTHCARE",
        url="https://www.niftyindices.com/indices/equity/sectoral-indices/nifty-healthcare-index",
        filename="nse_index_nifty_healthcare.csv",
        source=DownloadSoure.NSE_INDICES,
    ),
    IndexConfig(
        name="NIFTY_IT",
        url="https://www.niftyindices.com/indices/equity/sectoral-indices/nifty-it",
        filename="nse_index_nifty_it.csv",
        source=DownloadSoure.NSE_INDICES,
    ),
    IndexConfig(
        name="NIFTY_MEDIA",
        url="https://www.niftyindices.com/indices/equity/sectoral-indices/nifty-media",
        filename="nse_index_nifty_media.csv",
        source=DownloadSoure.NSE_INDICES,
    ),
    IndexConfig(
        name="NIFTY_METAL",
        url="https://www.niftyindices.com/indices/equity/sectoral-indices/nifty-metal",
        filename="nse_index_nifty_metal.csv",
        source=DownloadSoure.NSE_INDICES,
    ),
    IndexConfig(
        name="NIFTY_PHARMA",
        url="https://www.niftyindices.com/indices/equity/sectoral-indices/nifty-pharma",
        filename="nse_index_nifty_pharma.csv",
        source=DownloadSoure.NSE_INDICES,
    ),
    IndexConfig(
        name="NIFTY_PRIVATE_BANK",
        url="https://www.niftyindices.com/indices/equity/sectoral-indices/nifty-private-bank",
        filename="nse_index_nifty_private_bank.csv",
        source=DownloadSoure.NSE_INDICES,
    ),
    IndexConfig(
        name="NIFTY_PSU_BANK",
        url="https://www.niftyindices.com/indices/equity/sectoral-indices/nifty-psu-bank",
        filename="nse_index_nifty_psu_bank.csv",
        source=DownloadSoure.NSE_INDICES,
    ),
    IndexConfig(
        name="NIFTY_REALTY",
        url="https://www.niftyindices.com/indices/equity/sectoral-indices/nifty-realty",
        filename="nse_index_nifty_realty.csv",
        source=DownloadSoure.NSE_INDICES,
    ),
    IndexConfig(
        name="NIFTY_REIT_REALTY",
        url="https://niftyindices.com/indices/equity/sectoral-indices/nifty-reits-realty",
        filename="nse_index_nifty_reits_realty.csv",
        source=DownloadSoure.NSE_INDICES,
    ),
    IndexConfig(
        name="NIFTY_CONSUMER_DURABLES",
        url="https://www.niftyindices.com/indices/equity/sectoral-indices/nifty-consumer-durables-index",
        filename="nse_index_nifty_consumer_durables.csv",
        source=DownloadSoure.NSE_INDICES,
    ),
    IndexConfig(
        name="NIFTY_CONSUMER_DURABLES",
        url="https://www.niftyindices.com/indices/equity/sectoral-indices/nifty-consumer-durables-index",
        filename="nse_index_nifty_consumer_durables.csv",
        source=DownloadSoure.NSE_INDICES,
    ),
    IndexConfig(
        name="NIFTY_OIL_GAS",
        url="https://www.niftyindices.com/indices/equity/sectoral-indices/nifty-oil-and-gas-index",
        filename="nse_index_nifty_oil_gas.csv",
        source=DownloadSoure.NSE_INDICES,
    ),
    IndexConfig(
        name="NIFTY_500_HEALTHCARE",
        url="https://niftyindices.com/indices/equity/sectoral-indices/nifty500-healthcare",
        filename="nse_index_nifty_500_healthcare.csv",
        source=DownloadSoure.NSE_INDICES,
    ),
    IndexConfig(
        name="NIFTY_MID_SMALL_FINANCIAL_SERVICES",
        url="https://www.niftyindices.com/indices/equity/sectoral-indices/nifty-midsmall-financial-services",
        filename="nse_index_nifty_mid_small_financial_services.csv",
        source=DownloadSoure.NSE_INDICES,
    ),
    IndexConfig(
        name="NIFTY_MID_SMALL_HEALTHCARE",
        url="https://www.niftyindices.com/indices/equity/sectoral-indices/nifty-midsmall-healthcare",
        filename="nse_index_nifty_mid_small_healthcare.csv",
        source=DownloadSoure.NSE_INDICES,
    ),
    IndexConfig(
        name="NIFTY_MID_SMALL_IT_TELECOM",
        url="https://www.niftyindices.com/indices/equity/sectoral-indices/nifty-midsmall-it-telecom",
        filename="nse_index_nifty_mid_small_it_telecom.csv",
        source=DownloadSoure.NSE_INDICES,
    ),
]


MARKET_INDICES = [
    IndexConfig(
        name="NIFTY_50",
        url="https://www.nseindia.com/static/products-services/indices-nifty50-index",
        filename="nse_index_nifty_50.csv",
        source=DownloadSoure.NSE,
    ),
    IndexConfig(
        name="NIFTY_NEXT_50",
        url="https://www.nseindia.com/static/products-services/indices-niftynext50-index",
        filename="nse_index_nifty_next_50.csv",
        source=DownloadSoure.NSE,
    ),
    IndexConfig(
        name="NIFTY_100",
        url="https://www.nseindia.com/static/products-services/indices-nifty100-index",
        filename="nse_index_nifty_100.csv",
        source=DownloadSoure.NSE,
    ),
    IndexConfig(
        name="NIFTY_200",
        url="https://www.nseindia.com/static/products-services/indices-nifty200-index",
        filename="nse_index_nifty_200.csv",
        source=DownloadSoure.NSE,
    ),
    IndexConfig(
        name="NIFTY_TOTAL_MARKET",
        url="https://www.nseindia.com/static/products-services/indices-nifty-total-market-index",
        filename="nse_index_nifty_total_market.csv",
        source=DownloadSoure.NSE,
    ),
    IndexConfig(
        name="NIFTY_500",
        url="https://www.nseindia.com/static/products-services/indices-nifty500-index",
        filename="nse_index_nifty_500.csv",
        source=DownloadSoure.NSE,
    ),
    IndexConfig(
        name="NIFTY_500_MULTICAP_50:25:25",
        url="https://www.nseindia.com/static/products-services/indices-nifty500-multicap-50-25-25-index",
        filename="nse_index_nifty_500_multicap_50_25_25.csv",
        source=DownloadSoure.NSE,
    ),
    IndexConfig(
        name="NIFTY_SMALLCAP_250",
        url="https://www.nseindia.com/static/products-services/indices-niftysmallcap250-index",
        filename="nse_index_nifty_smallcap_250.csv",
        source=DownloadSoure.NSE,
    ),
]
