import re
import socket

import requests
from bs4 import BeautifulSoup

from database.database import save_financial_statement


KAP_BASE_URL = "https://www.kap.org.tr"

COMPANY_IDS = {
    "ASTOR": "8acae2c562329bd10164405fe6c17996",
}


def download_kap_page(url, headers=None):
    if headers is None:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/151.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
        }

    last_error = None

    try:
        response = requests.get(
            url,
            headers=headers,
            timeout=30
        )

        response.raise_for_status()
        return response

    except Exception as error:
        last_error = error

    kap_ips = [
        "185.53.60.150",
        "185.53.61.150",
    ]

    for ip in kap_ips:
        try:
            host = "www.kap.org.tr"
            original_getaddrinfo = socket.getaddrinfo

            def custom_getaddrinfo(
                hostname,
                port,
                family=0,
                type=0,
                proto=0,
                flags=0
            ):
                if hostname == host:
                    return [
                        (
                            socket.AF_INET,
                            socket.SOCK_STREAM,
                            6,
                            "",
                            (ip, port),
                        )
                    ]

                return original_getaddrinfo(
                    hostname,
                    port,
                    family,
                    type,
                    proto,
                    flags
                )

            socket.getaddrinfo = custom_getaddrinfo

            try:
                response = requests.get(
                    url,
                    headers=headers,
                    timeout=30
                )

                response.raise_for_status()
                return response

            finally:
                socket.getaddrinfo = original_getaddrinfo

        except Exception as error:
            last_error = error

    raise RuntimeError(
        f"KAP sayfasına erişilemedi: {last_error}"
    )


def get_company_id(symbol):
    symbol = symbol.upper().strip()

    company_id = COMPANY_IDS.get(symbol)

    if not company_id:
        raise ValueError(
            f"{symbol} için KAP şirket ID'si tanımlı değil."
        )

    return company_id


def get_company_financial_url(symbol):
    company_id = get_company_id(symbol)

    return (
        f"{KAP_BASE_URL}/tr/"
        f"sirket-finansal-bilgileri/"
        f"{company_id}"
    )


def check_kap_period(symbol, period):
    symbol = symbol.upper().strip()
    period = str(period).strip()

    url = get_company_financial_url(symbol)

    try:
        response = download_kap_page(url)

        html = response.text

        soup = BeautifulSoup(
            html,
            "html.parser"
        )

        text = soup.get_text(
            " ",
            strip=True
        )

        text = re.sub(
            r"\s+",
            " ",
            text
        )

        found = period in text

        if not found:
            match = re.match(
                r"^(\d{4})/(\d{2})$",
                period
            )

            if match:
                year = match.group(1)
                month = match.group(2)

                alternative_patterns = {
                    "03": [
                        f"31.03.{year}",
                        f"31/03/{year}",
                        f"31-03-{year}",
                        f"{year}-03-31",
                    ],
                    "06": [
                        f"30.06.{year}",
                        f"30/06/{year}",
                        f"30-06-{year}",
                        f"{year}-06-30",
                    ],
                    "09": [
                        f"30.09.{year}",
                        f"30/09/{year}",
                        f"30-09-{year}",
                        f"{year}-09-30",
                    ],
                    "12": [
                        f"31.12.{year}",
                        f"31/12/{year}",
                        f"31-12-{year}",
                        f"{year}-12-31",
                    ],
                }

                for pattern in alternative_patterns.get(
                    month,
                    []
                ):
                    if pattern in text:
                        found = True
                        break

        return {
            "symbol": symbol,
            "period": period,
            "found": found,
            "url": url,
            "status_code": response.status_code,
        }

    except Exception as error:
        return {
            "symbol": symbol,
            "period": period,
            "found": False,
            "url": url,
            "status_code": None,
            "error": str(error),
        }


def get_kap_company_page(symbol):
    url = get_company_financial_url(symbol)

    response = download_kap_page(url)

    return response.text


def extract_periods_from_kap(symbol):
    html = get_kap_company_page(symbol)

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    text = soup.get_text(
        " ",
        strip=True
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    periods = set()

    periods.update(
        re.findall(
            r"\b20\d{2}/(?:03|06|09|12)\b",
            text
        )
    )

    dates = re.findall(
        r"\b\d{2}\.\d{2}\.20\d{2}\b",
        text
    )

    for date in dates:
        day, month, year = date.split(".")

        if month in {
            "03",
            "06",
            "09",
            "12",
        }:
            periods.add(
                f"{year}/{month}"
            )

    return sorted(periods)


if __name__ == "__main__":

    result = check_kap_period(
        "ASTOR",
        "2026/06"
    )

    print(result)