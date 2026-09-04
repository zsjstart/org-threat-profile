import argparse
import csv
from pprint import pprint

from org_threat_profile import metric


def write_scores(filename: str, scores: dict[str, dict[str, metric.Score]]) -> str:
    with open(filename, "w") as f:
        csv_writer = None
        for agent, agent_scores in scores.items():
            agent_data: dict[str, str | int | float] = {"agent": agent}
            for score_name, score_values in agent_scores.items():
                agent_data[f"{score_name} value"] = score_values.value
                agent_data[f"{score_name} total"] = score_values.total
            if csv_writer is None:
                csv_writer = csv.DictWriter(f, fieldnames=agent_data.keys())
                csv_writer.writeheader()
            csv_writer.writerow(agent_data)
    return f"Results written to {filename}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "topic", type=str, help="Topic/organisation that the agents focused on."
    )
    parser.add_argument(
        "output_folder",
        type=str,
        help="Folder containing yaml outputs from the agents.",
    )
    args = parser.parse_args()

    print(f"Processing outputs focused on {args.topic} in {args.output_folder}...")
    scores = metric.score_all_outputs(args.topic, args.output_folder)
    print("=== Results ===")
    pprint(scores)

    write_status = write_scores("results.csv", scores)
    print(write_status)
