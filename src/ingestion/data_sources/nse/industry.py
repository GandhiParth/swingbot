import logging
import random
import time

import polars as pl
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from sqlalchemy import create_engine, text

from config.ingestion.data_sources import NSEConfig

logger = logging.getLogger(__name__)


def _create_classification_table():

    engine = create_engine(NSEConfig.DB_CONN)
    table_id = NSEConfig.get_db_tbl(
        tbl_name=NSEConfig.CLASSIFICATION_TABLE_ID, failed_tbl=False
    )

    with engine.connect() as conn:
        # Enable foreign keys (SQLite)
        conn.execute(text("PRAGMA foreign_keys = ON"))

        # Create table if not exists
        conn.execute(
            text(
                f"""
            CREATE TABLE IF NOT EXISTS {table_id} (
                timestamp TEXT NOT NULL,
                symbol TEXT NOT NULL,
                macro_economic_sector TEXT,
                sector TEXT,
                industry TEXT,
                basic_industry TEXT,
                market_cap_cr REAL,
                PRIMARY KEY (symbol, timestamp)
            )
        """
            )
        )

        # Commit changes (needed for SQLite)
        conn.commit()

    logger.info("NSE Classification table created")


def _prepare_symbol_list(
    ins_df: pl.DataFrame,
    fetch_date: str,
) -> list[str]:
    """ """

    table_id = NSEConfig.get_db_tbl(
        tbl_name=NSEConfig.CLASSIFICATION_TABLE_ID, failed_tbl=False
    )
    query = f"""
        select symbol
        from {table_id}
        where timestamp = '{fetch_date}'
    """
    success_df = pl.read_database_uri(query=query, uri=NSEConfig.DB_CONN)
    success_symbols = success_df.get_column("symbol").to_list()

    logger.info(f"# of Symbols data already fecthed for: {len(success_symbols)}")

    ins_df = (
        ins_df.lazy()
        .filter(
            (pl.col("segment") == "NSE")
            & (pl.col("name").str.len_chars() > 0)
            & (~pl.col("symbol").str.ends_with("INAV"))
        )
        .with_columns(
            pl.col("symbol")
            .str.split(by="-")
            .list.get(index=1, null_on_oob=True)
            .fill_null("EQ")
            .alias("suffix")
        )
        .filter(pl.col("suffix").is_in(["EQ"]))
        .collect()
    )

    logger.info(f"# of Symbols to fetch data: {ins_df.shape[0]}")

    fetch_symbols = (
        ins_df.remove(pl.col("symbol").is_in(success_symbols))
        .sort("symbol")
        .get_column("symbol")
        .to_list()
    )

    logger.info(f"# of Symbols data will be fecthed for: {len(fetch_symbols)}")

    return fetch_symbols


def fetch_nse_industry_classification(
    ins_df: pl.DataFrame,
    fetch_date: str,
):

    _create_classification_table()
    symbol_list = _prepare_symbol_list(ins_df=ins_df, fetch_date=fetch_date)
    count = 0

    logger.info("Starting NSE Classification")

    options = FirefoxOptions()
    options.set_preference(
        "general.useragent.override",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
    )
    options.set_preference("dom.webdriver.enabled", False)
    options.add_argument("--headless")
    driver = webdriver.Firefox(options=options)
    driver.get(NSEConfig.NSE_URL)
    driver.implicitly_wait(15)
    driver.maximize_window()
    time.sleep(random.uniform(3, 6))

    for symbol in symbol_list:
        if count % 100 == 0:
            logger.info(
                f"Fetched data Successfully for {count}/{len(symbol_list)} symbols"
            )

        try:
            search_box = driver.find_element(
                By.XPATH,
                "//input[@role='combobox' and contains(@class,'rbt-input-main')]",
            )

            search_box.click()
            search_box.send_keys(Keys.CONTROL, "a")
            search_box.send_keys(Keys.BACKSPACE)

            for ch in symbol:
                time.sleep(random.uniform(0.3, 1))
                search_box.send_keys(ch)

            time.sleep(random.uniform(0.5, 1.5))
            search_box.send_keys(Keys.ARROW_DOWN)
            search_box.send_keys(Keys.ENTER)

            wait = WebDriverWait(driver, 10)
            _ = wait.until(
                EC.presence_of_element_located(
                    (
                        By.XPATH,
                        "//span[@role='button' and contains(@aria-label,'Industry Classification')]",
                    )
                )
            )

            time.sleep(random.uniform(2, 4))

            info_btn = driver.find_element(
                By.XPATH,
                "//span[@role='button' and contains(@aria-label,'Industry Classification')]",
            )
            driver.execute_script("arguments[0].click();", info_btn)

            time.sleep(random.uniform(0.7, 3))

            macro_sector = driver.find_element(
                By.XPATH,
                "//td[normalize-space()='Macro-Economic Sector']/following-sibling::td",
            ).text

            sector = driver.find_element(
                By.XPATH, "//td[normalize-space()='Sector']/following-sibling::td"
            ).text

            industry = driver.find_element(
                By.XPATH, "//td[normalize-space()='Industry']/following-sibling::td"
            ).text

            basic_industry = driver.find_element(
                By.XPATH,
                "//td[normalize-space()='Basic Industry']/following-sibling::td",
            ).text

            time.sleep(random.uniform(1, 2))

            driver.execute_script(
                "arguments[0].click();",
                driver.find_element(By.XPATH, "//button[@aria-label='Close']"),
            )

            time.sleep(random.uniform(0.5, 1.5))  # allow modal overlay to disappear

            market_cap = driver.find_element(
                By.XPATH,
                "//div[normalize-space()='Total Market Cap (₹ Cr.)']/following-sibling::div[1]",
            ).text

            data = {
                "timestamp": fetch_date,
                "symbol": symbol,
                "macro_economic_sector": macro_sector,
                "sector": sector,
                "industry": industry,
                "basic_industry": basic_industry,
                "market_cap_cr": market_cap,
            }

            df = (
                pl.DataFrame([data])
                .lazy()
                .with_columns(
                    pl.when(pl.col("market_cap_cr") == "-")
                    .then(None)
                    .otherwise(pl.col("market_cap_cr"))
                    .alias("market_cap_cr")
                )
                .with_columns(
                    pl.col("market_cap_cr")
                    .str.replace_all(pattern=",", value="", literal=True)
                    .cast(pl.Float64)
                    .round(2)
                )
                .collect()
            )

            df.write_database(
                table_name=NSEConfig.get_db_tbl(
                    tbl_name=NSEConfig.CLASSIFICATION_TABLE_ID, failed_tbl=False
                ),
                connection=NSEConfig.DB_CONN,
                if_table_exists="append",
            )

            count += 1
            time.sleep(random.uniform(3, 6))

        except Exception as e:
            logger.error(f"Failed for {symbol}: {e}")

            data = {
                "timestamp": fetch_date,
                "symbol": symbol,
            }

            df = pl.DataFrame([data])

            df.write_database(
                table_name=NSEConfig.get_db_tbl(
                    tbl_name=NSEConfig.CLASSIFICATION_TABLE_ID, failed_tbl=True
                ),
                connection=NSEConfig.DB_CONN,
                if_table_exists="append",
            )

            logger.warning("Error Occured: Restarting Driver")

            driver.quit()
            options = FirefoxOptions()
            options.add_argument("--headless")
            driver = webdriver.Firefox(options=options)
            driver.get(NSEConfig.NSE_URL)
            driver.implicitly_wait(15)
            driver.maximize_window()
            time.sleep(random.uniform(3, 6))

    driver.quit()

    logger.info(f"Fetched data Successfully for {count}/{len(symbol_list)} symbols")
