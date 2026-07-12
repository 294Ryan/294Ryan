"""
update.py
------------------------------------------------------------------
用途：抓取 GitHub 統計數據，計算 Uptime，並更新 README.md 中
      <!-- START_STATS --> ~ <!-- END_STATS --> 之間的內容，
      並維持虛線對齊；標題與標籤以 <b> 粗體呈現層次。

環境變數：
  GH_TOKEN   - 具備 repo, read:user 權限的 Personal Access Token
------------------------------------------------------------------
"""

import os
import re
import calendar
from datetime import date, datetime

import requests

# ------------------------- 基本設定 -------------------------
USERNAME = "294Ryan"
GITHUB_TOKEN = os.environ["GH_TOKEN"]
HEADERS = {"Authorization": f"bearer {GITHUB_TOKEN}"}

README_PATH = "README.md"
START_MARK = "<!-- START_STATS -->"
END_MARK = "<!-- END_STATS -->"

START_CODING_DATE = date(2025, 7, 1)  # 你的寫程式起算日

LINE_WIDTH = 60  # 純文字視覺寬度（不含 HTML tag）


# ------------------------- 工具函式 -------------------------
def calc_uptime(start: date) -> str:
    """精確計算「年 / 月 / 日」的資歷字串，處理跨月借位。"""
    today = date.today()
    years = today.year - start.year
    months = today.month - start.month
    days = today.day - start.day

    if days < 0:
        months -= 1
        prev_month = today.month - 1 or 12
        prev_year = today.year if today.month > 1 else today.year - 1
        days += calendar.monthrange(prev_year, prev_month)[1]

    if months < 0:
        years -= 1
        months += 12

    return f"{years} years, {months} months, {days} days."


def render_line(label: str, value: str, width: int = LINE_WIDTH) -> str:
    """
    產生單行：粗體標籤 + 虛線 + 數值，維持終端機對齊感。
    虛線長度依「純文字長度」計算，HTML tag 不列入寬度。
    """
    prefix = f"\u2022 {label}"  # • 符號
    dash_len = max(width - len(prefix) - len(value) - 2, 3)
    dashes = "-" * dash_len
    return f"<b>{prefix}</b> {dashes} {value}"


def title_line(text: str) -> str:
    return f"<b>{text}</b>"


# ------------------------- 資料抓取 -------------------------
def fetch_repo_stats() -> dict:
    """透過 REST API 抓取 Repos 數量與 Stars。"""
    repos = []
    page = 1
    while True:
        resp = requests.get(
            "https://api.github.com/user/repos",
            headers=HEADERS,
            params={"per_page": 100, "page": page, "affiliation": "owner"},
        )
        resp.raise_for_status()
        data = resp.json()
        if not data:
            break
        repos.extend(data)
        page += 1

    public_repos = sum(1 for r in repos if not r["private"])
    private_repos = sum(1 for r in repos if r["private"])
    stars = sum(r["stargazers_count"] for r in repos)

    user = requests.get(
        f"https://api.github.com/users/{USERNAME}", headers=HEADERS
    ).json()
    followers = user.get("followers", 0)

    return {
        "total_repos": len(repos),
        "public_repos": public_repos,
        "private_repos": private_repos,
        "stars": stars,
        "followers": followers,
    }


def fetch_total_commits() -> int:
    """
    GraphQL 的 contributionsCollection 單次只能查一年區間，
    因此從帳號建立年份開始逐年迴圈加總。
    """
    created_query = "query($login:String!){ user(login:$login){ createdAt } }"
    resp = requests.post(
        "https://api.github.com/graphql",
        json={"query": created_query, "variables": {"login": USERNAME}},
        headers=HEADERS,
    ).json()
    created_at = datetime.strptime(
        resp["data"]["user"]["createdAt"], "%Y-%m-%dT%H:%M:%SZ"
    )

    contrib_query = """
    query($login:String!, $from:DateTime!, $to:DateTime!) {
      user(login:$login) {
        contributionsCollection(from:$from, to:$to) {
          totalCommitContributions
          restrictedContributionsCount
        }
      }
    }
    """

    total = 0
    for year in range(created_at.year, datetime.utcnow().year + 1):
        variables = {
            "login": USERNAME,
            "from": f"{year}-01-01T00:00:00Z",
            "to": f"{year}-12-31T23:59:59Z",
        }
        r = requests.post(
            "https://api.github.com/graphql",
            json={"query": contrib_query, "variables": variables},
            headers=HEADERS,
        ).json()
        c = r["data"]["user"]["contributionsCollection"]
        total += c["totalCommitContributions"] + c["restrictedContributionsCount"]

    return total


# ------------------------- 組裝與寫回 -------------------------
def build_stats_block() -> str:
    stats = fetch_repo_stats()
    commits = fetch_total_commits()
    uptime = calc_uptime(START_CODING_DATE)

    lines = [
        title_line("294Ryan - Coder"),
        render_line("Uptime", uptime),
        render_line("IDE", "VS Code 1.128.0"),
        render_line("Langs.Programming", "Python, C++, C, Java"),
        render_line("Langs.Real", "English, Chinese"),
        render_line("Interests", "Algorithms, Data Structures, Backend"),
        render_line("Hobbies", "Coding, Gaming, Volleyball"),
        "",
        title_line("Contact"),
        render_line("Email", "294ryan@gmail.com"),
        render_line("Discord", "294coder"),
        "",
        title_line("Github Stats"),
        render_line("Total Repos", str(stats["total_repos"])),
        render_line("Public Repos", str(stats["public_repos"])),
        render_line("Private Repos", str(stats["private_repos"])),
        render_line("Stars", str(stats["stars"])),
        render_line("Followers", str(stats["followers"])),
        render_line("Commits", str(commits)),
    ]
    return "\n".join(lines)


def update_readme() -> None:
    with open(README_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    new_block = build_stats_block()
    pattern = re.compile(f"{re.escape(START_MARK)}.*?{re.escape(END_MARK)}", re.DOTALL)
    replacement = f"{START_MARK}\n{new_block}\n{END_MARK}"

    if not pattern.search(content):
        raise RuntimeError("找不到 START_STATS / END_STATS 錨點，請確認 README.md 格式。")

    content = pattern.sub(replacement, content)

    with open(README_PATH, "w", encoding="utf-8") as f:
        f.write(content)


if __name__ == "__main__":
    update_readme()
    print("README.md 更新完成。")