import os
import time
import requests
from datetime import datetime, timezone

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")

URLS_FILE = "urls.txt"

HEADERS = {
    "User-Agent": "BigCartelStatusMonitor/1.0"
}


def load_urls():
    try:
        with open(URLS_FILE, "r", encoding="utf-8") as file:
            urls = []

            for line in file:
                line = line.strip()

                if not line:
                    continue

                if line.startswith("#"):
                    continue

                if not line.startswith("http://") and not line.startswith("https://"):
                    line = "https://" + line

                urls.append(line)

            return urls

    except FileNotFoundError:
        print("urls.txt tidak ditemukan.")
        return []


def check_site(url: str):
    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=20,
            allow_redirects=True
        )

        status_code = response.status_code
        body = response.text or ""
        body_lower = body.lower()

        page_not_found_keywords = [
            "page not found",
            "<title>page not found</title>",
            ">page not found<",
        ]

        is_page_not_found = any(
            keyword in body_lower for keyword in page_not_found_keywords
        )

        if status_code == 404 or is_page_not_found:
            return {
                "url": url,
                "active": False,
                "status": status_code,
                "message": "Page Not Found"
            }

        if 200 <= status_code < 400:
            return {
                "url": url,
                "active": True,
                "status": status_code,
                "message": "Active"
            }

        return {
            "url": url,
            "active": False,
            "status": status_code,
            "message": f"HTTP {status_code}"
        }

    except requests.exceptions.Timeout:
        return {
            "url": url,
            "active": False,
            "status": "TIMEOUT",
            "message": "Request Timeout"
        }

    except requests.exceptions.RequestException as err:
        return {
            "url": url,
            "active": False,
            "status": "ERROR",
            "message": str(err)
        }


def send_discord_report(results):
    if not DISCORD_WEBHOOK_URL:
        print("DISCORD_WEBHOOK_URL belum diset di GitHub Secrets.")
        return

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    active_count = sum(1 for item in results if item["active"])
    problem_count = len(results) - active_count

    color = 0x2ECC71 if problem_count == 0 else 0xE74C3C

    lines = []
    for item in results:
        emoji = "🟢" if item["active"] else "🔴"
        lines.append(
            f'{emoji} **{item["url"]}**\n'
            f'`Status: {item["status"]}` - {item["message"]}'
        )

    description = "\n\n".join(lines)

    if not description:
        description = "Tidak ada URL di urls.txt"

    payload = {
        "username": "BigCartel Monitor",
        "embeds": [
            {
                "title": "BigCartel Domain Status",
                "description": description[:4000],
                "color": color,
                "fields": [
                    {
                        "name": "🟢 Active",
                        "value": str(active_count),
                        "inline": True
                    },
                    {
                        "name": "🔴 Page Not Found / Problem",
                        "value": str(problem_count),
                        "inline": True
                    },
                    {
                        "name": "Total URL",
                        "value": str(len(results)),
                        "inline": True
                    },
                    {
                        "name": "Checked At",
                        "value": now,
                        "inline": False
                    }
                ],
                "footer": {
                    "text": "Auto check by GitHub Actions"
                }
            }
        ]
    }

    try:
        response = requests.post(
            DISCORD_WEBHOOK_URL,
            json=payload,
            timeout=20
        )

        if response.status_code not in (200, 204):
            print("Discord webhook failed:", response.status_code, response.text)

    except requests.exceptions.RequestException as err:
        print("Failed to send Discord webhook:", err)


def main():
    print("BigCartel monitor started by GitHub Actions...")

    results = []
    urls = load_urls()

    print("=" * 60)
    print("CHECK:", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"))
    print("Total URL:", len(urls))

    for url in urls:
        result = check_site(url)
        results.append(result)

        status_icon = "UP" if result["active"] else "PAGE NOT FOUND"
        print(f'[{status_icon}] {result["url"]} - {result["status"]} - {result["message"]}')

        time.sleep(1)

    send_discord_report(results)

    print("Check selesai.")


if __name__ == "__main__":
    main()
