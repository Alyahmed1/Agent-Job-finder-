"""Read LinkedIn alert emails and the free remote-job sites -> score new jobs -> print the top ones."""
import argparse

import db
import pipeline
from score import load_profile


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=2, help="how many days of emails to read")
    ap.add_argument("--rescore", action="store_true", help="re-score saved jobs, skip Gmail and the web")
    ap.add_argument("--force", action="store_true", help="ignore the cooldown on the remote-job sites")
    args = ap.parse_args()

    profile = load_profile()
    conn = db.connect()

    if args.rescore:
        print(f"Re-scored {pipeline.rescore(conn, profile)} saved jobs")
    else:
        report = pipeline.refresh(conn, profile, days=args.days, force=args.force)
        print(f"{pipeline.total_new(report)} new jobs")
        for source, result in report.items():
            print(f"  {source}: {result}")

    top_n = profile["scoring"]["top_n"]
    print(f"\n=== TOP {top_n} JOBS ===")
    for rank, r in enumerate(db.top_jobs(conn, top_n), 1):
        print(f"{rank}. [{r['score']}] {r['title']} - {r['company']} ({r['location']})")
        print(f"   {r['reason']}")
        print(f"   {r['url']}")


if __name__ == "__main__":
    main()
