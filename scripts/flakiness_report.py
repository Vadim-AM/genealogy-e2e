#!/usr/bin/env python3
"""Analyze JUnit XML reports for flaky tests.

A test is 'flaky' if it failed in some runs but passed in others
without code changes to its file.

Usage:
    python scripts/flakiness_report.py --results-dir allure-results/
    python scripts/flakiness_report.py --results-dir merged-results/ --threshold 2
"""

from __future__ import annotations

import argparse
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path
from typing import cast


def parse_junit_xml(path: Path) -> list[dict[str, str]]:
    """Extract test results from a JUnit XML file."""
    results: list[dict[str, str]] = []
    try:
        tree = ET.parse(path)
    except ET.ParseError:
        return results

    for testcase in tree.iter("testcase"):
        name = testcase.get("classname", "") + "::" + testcase.get("name", "")
        failure = testcase.find("failure")
        error = testcase.find("error")
        skipped = testcase.find("skipped")

        if failure is not None or error is not None:
            status = "failed"
        elif skipped is not None:
            status = "skipped"
        else:
            status = "passed"

        results.append({"name": name, "status": status, "file": str(path)})
    return results


def collect_results(results_dir: Path) -> list[dict[str, str]]:
    """Collect all test results from JUnit XML files in directory."""
    all_results: list[dict[str, str]] = []
    for xml_file in results_dir.rglob("*.xml"):
        all_results.extend(parse_junit_xml(xml_file))
    return all_results


def find_flaky(results: list[dict[str, str]], threshold: int = 1) -> list[dict[str, object]]:
    """Find tests that have both passed and failed across runs."""
    by_test: dict[str, list[str]] = defaultdict(list)
    for r in results:
        by_test[r["name"]].append(r["status"])

    flaky: list[dict[str, object]] = []
    for name, statuses in sorted(by_test.items()):
        passes = statuses.count("passed")
        fails = statuses.count("failed")
        if fails >= threshold and passes > 0:
            flaky.append({
                "test": name,
                "passes": passes,
                "fails": fails,
                "total": len(statuses),
                "fail_rate": f"{fails / len(statuses):.0%}",
            })

    return sorted(flaky, key=lambda x: cast("int", x["fails"]), reverse=True)


def main(argv: list[str] | None = None) -> int:
    """Run flakiness analysis and print report."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--results-dir",
        type=Path,
        required=True,
        help="Directory containing JUnit XML reports",
    )
    parser.add_argument(
        "--threshold",
        type=int,
        default=1,
        help="Minimum failures to flag as flaky (default: 1)",
    )
    args = parser.parse_args(argv)

    if not args.results_dir.exists():
        print(f"Results directory not found: {args.results_dir}")
        return 1

    results = collect_results(args.results_dir)
    if not results:
        print(f"No JUnit XML results found in {args.results_dir}")
        return 0

    flaky = find_flaky(results, threshold=args.threshold)

    print(f"Analyzed {len(results)} test results from {args.results_dir}")
    print()

    if not flaky:
        print("No flaky tests detected.")
        return 0

    print(f"Found {len(flaky)} flaky test(s):\n")
    print(f"{'Test':<80} {'Fails':>5} {'Passes':>6} {'Rate':>6}")
    print("-" * 100)
    for f in flaky:
        test_name = str(f["test"])
        if len(test_name) > 78:
            test_name = "..." + test_name[-75:]
        print(f"{test_name:<80} {f['fails']:>5} {f['passes']:>6} {f['fail_rate']:>6}")

    return 1


if __name__ == "__main__":
    sys.exit(main())
