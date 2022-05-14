import random

timeout = 220
url_nasdaq_companies = "https://pkgstore.datahub.io/core/nasdaq-listings/nasdaq-listed_csv/data/7665719fb51081ba0bd834fde71ce822/nasdaq-listed_csv.csv"
USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.71 Safari/537.36",
    # "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/44.0.2403.157 Safari/537.36",
    # "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/72.0.3626.121 Safari/537.36",
    # "Mozilla/5.0 (X11; Datanyze; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/65.0.3325.181 Safari/537.36",
]
headers_html = {
    "User-Agent": "{}".format(random.choices(USER_AGENTS)[0]),
}
headers_json = {
    "User-Agent": "{}".format(random.choices(USER_AGENTS)[0]),
    "Content-Type": "application/json",
}
headers_sec = {
    "User-Agent": "jwpr-company@jwpr.com",
    "Content-Type": "application/json",
}
