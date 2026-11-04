"""Generate an ASCII card with public GitHub activity.

Run with: python scripts/build_stats.py path/to/stats.svg
Requires the GitHub CLI, authenticated locally or through GH_TOKEN.
Private repositories are always left out, whichever token is used.
"""
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from build_scene import border, col_x, row, stylesheet, svg_document, text

LOGIN = "Fjjorda"
# Featured public projects used for the language shares.
REPOSITORIES = [
    "Fjjorda/casa-esperanza",
    "Fjjorda/satellite-wildfire-detection-and-analysis",
    "Dalibex/urban-incidence-manager",
]
# Build and configuration files, not languages worth highlighting.
CONFIG_LANGUAGES = {"Dockerfile", "Makefile", "Batchfile", "jq"}
WEEKS = 12
BAR_WIDTH = 24
GRAPH_HEIGHT = 4
LANGUAGE_COLORS = {"Java": "fox", "TypeScript": "accent", "Python": "gold", "CSS": "fire", "Other": "dim"}

ACTIVITY_QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      commitContributionsByRepository(maxRepositories: 100) {
        repository { isPrivate }
        contributions(first: 100, orderBy: {field: OCCURRED_AT, direction: DESC}) { nodes { occurredAt commitCount } }
      }
      issueContributionsByRepository(maxRepositories: 100) {
        repository { isPrivate }
        contributions(first: 100, orderBy: {direction: DESC}) { totalCount nodes { occurredAt } }
      }
      pullRequestContributionsByRepository(maxRepositories: 100) {
        repository { isPrivate }
        contributions(first: 100, orderBy: {direction: DESC}) { totalCount nodes { occurredAt } }
      }
      pullRequestReviewContributionsByRepository(maxRepositories: 100) {
        repository { isPrivate }
        contributions(first: 100, orderBy: {direction: DESC}) { totalCount nodes { occurredAt } }
      }
    }
  }
}
"""


def gh(*args):
    result = subprocess.run(["gh", "api", *args], capture_output=True, text=True, encoding="utf-8", check=True)
    return json.loads(result.stdout)


def my_commits(repository):
    contributors = gh(f"repos/{repository}/contributors?per_page=100")
    return next((c["contributions"] for c in contributors if c["login"] == LOGIN), 0)


def language_shares():
    """Split each repository's commits across its languages, then total them."""
    totals = {}
    for repository in REPOSITORIES:
        commits = my_commits(repository)
        languages = gh(f"repos/{repository}/languages")
        languages = {name: size for name, size in languages.items() if name not in CONFIG_LANGUAGES}
        size = sum(languages.values()) or 1
        for language, bytes_used in languages.items():
            totals[language] = totals.get(language, 0) + commits * bytes_used / size
    grand_total = sum(totals.values()) or 1
    top = sorted(totals.items(), key=lambda item: item[1], reverse=True)[:4]
    shares = [(name, value / grand_total) for name, value in top]
    shares.append(("Other", max(0.0, 1 - sum(share for _, share in shares))))
    return shares


def public_activity(now):
    """Return yearly public code reviews and contributions per week, oldest week first."""
    data = gh("graphql", "-f", f"query={ACTIVITY_QUERY}", "-f", f"login={LOGIN}")
    collection = data["data"]["user"]["contributionsCollection"]
    weekly = [0] * WEEKS
    reviews = 0

    def add_to_week(occurred_at, amount):
        moment = datetime.fromisoformat(occurred_at.replace("Z", "+00:00"))
        weeks_ago = (now - moment).days // 7
        if 0 <= weeks_ago < WEEKS:
            weekly[WEEKS - 1 - weeks_ago] += amount

    for group in collection["commitContributionsByRepository"]:
        if group["repository"]["isPrivate"]:
            continue
        for node in group["contributions"]["nodes"]:
            add_to_week(node["occurredAt"], node["commitCount"])

    for field in ("issueContributionsByRepository", "pullRequestContributionsByRepository",
                  "pullRequestReviewContributionsByRepository"):
        for group in collection[field]:
            if group["repository"]["isPrivate"]:
                continue
            if field.startswith("pullRequestReview"):
                reviews += group["contributions"]["totalCount"]
            for node in group["contributions"]["nodes"]:
                add_to_week(node["occurredAt"], 1)
    return reviews, weekly


def merged_pull_requests(now):
    since = (now - timedelta(days=365)).date().isoformat()
    query = f"author:{LOGIN} is:pr is:merged is:public merged:>={since}"
    return gh("search/issues", "--method", "GET", "-f", f"q={query}", "-F", "per_page=1")["total_count"]


def card(shares, reviews, weekly, merged):
    body = [text("guest@forest:~$ git stats", row(1), css="dim"),
            text("languages, weighted by my commits", row(3), css="dim")]
    for i, (name, share) in enumerate(shares):
        y = row(4 + i)
        filled = max(1, round(share * BAR_WIDTH)) if share >= 0.005 else 0
        body.append(text(name[:10], y))
        body.append(text("[", y, x0=col_x(11), css="dim"))
        if filled:
            body.append(text("#" * filled, y, x0=col_x(12), css=LANGUAGE_COLORS.get(name, "dim")))
        if filled < BAR_WIDTH:
            body.append(text("." * (BAR_WIDTH - filled), y, x0=col_x(12 + filled), css="dim"))
        body.append(text("]", y, x0=col_x(12 + BAR_WIDTH), css="dim"))
        body.append(text(f"{share:>4.0%}", y, x0=col_x(14 + BAR_WIDTH)))

    body.append(text(f"public activity, last {WEEKS} weeks", row(10), css="dim"))
    peak = max(weekly) or 1
    for i, value in enumerate(weekly):
        bars = max(1, round(value / peak * GRAPH_HEIGHT)) if value else 0
        for level in range(GRAPH_HEIGHT):
            active = level < bars
            body.append(text("##" if active else "..", row(14 - level), x0=col_x(i * 3), css="ok" if active else "dim"))

    body.append(text("public totals, last 12 months", row(16), css="dim"))
    summary = f"{merged} merged PRs  {reviews} code reviews"
    body.append(text(summary, row(17)))
    return svg_document("GitHub stats: language shares, recent public activity and yearly totals", 18,
                        stylesheet([]), border("~/stats", 18) + "".join(body))


def main():
    now = datetime.now(timezone.utc)
    shares = language_shares()
    reviews, weekly = public_activity(now)
    merged = merged_pull_requests(now)
    print(", ".join(f"{name} {share:.0%}" for name, share in shares))
    print("weekly", weekly, "| reviews", reviews, "| merged PRs", merged)
    output = Path(sys.argv[1])
    output.write_text(card(shares, reviews, weekly, merged), encoding="utf-8")


if __name__ == "__main__":
    main()
