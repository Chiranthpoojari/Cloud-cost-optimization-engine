"""
Estimates monthly savings from the office-hours schedule.

This is a standalone modeling script (not part of the Lambda) — run it
locally to size the expected savings for your own account before/after
deploying, using either your own resource cost figures or AWS Cost
Explorer's "Amortized cost" export for tagged resources.

Usage:
    python scripts/estimate_savings.py --total-bill 12000 \
        --tagged-cost 3600 --hours-per-week 65

`--tagged-cost` is the current 24/7 monthly cost of every resource that
carries the AutoSchedule=office-hours tag (i.e. what they cost today,
running all the time). `--hours-per-week` is how many hours/week the
schedule actually keeps them running (default matches the Terraform
default: 07:00-20:00 Mon-Fri = 65 hrs/week).
"""
import argparse

HOURS_PER_WEEK_FULL = 24 * 7


def estimate(total_bill, tagged_cost_24x7, scheduled_hours_per_week):
    running_fraction = scheduled_hours_per_week / HOURS_PER_WEEK_FULL
    reduced_tagged_cost = tagged_cost_24x7 * running_fraction
    tagged_savings = tagged_cost_24x7 - reduced_tagged_cost
    savings_pct_of_total = (tagged_savings / total_bill) * 100 if total_bill else 0

    return {
        "tagged_cost_24x7": round(tagged_cost_24x7, 2),
        "running_fraction": round(running_fraction, 3),
        "reduced_tagged_cost": round(reduced_tagged_cost, 2),
        "monthly_savings": round(tagged_savings, 2),
        "savings_pct_of_total_bill": round(savings_pct_of_total, 1),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--total-bill", type=float, required=True, help="Total monthly AWS bill, all environments")
    parser.add_argument("--tagged-cost", type=float, required=True, help="Current 24/7 monthly cost of AutoSchedule-tagged resources")
    parser.add_argument("--hours-per-week", type=float, default=65, help="Hours/week the schedule keeps tagged resources running (default 65)")
    args = parser.parse_args()

    result = estimate(args.total_bill, args.tagged_cost, args.hours_per_week)

    print("Cloud cost optimization — savings estimate")
    print("-------------------------------------------")
    for key, value in result.items():
        print(f"{key:28s}: {value}")


if __name__ == "__main__":
    main()
