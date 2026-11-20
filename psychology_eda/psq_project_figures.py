"""Reproduce the six original LEMON PSQ figures."""

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd

from .lemon_psychology_eda import (
    OVERALL,
    PSQ_COLUMNS,
    parse_score,
    participant_groups,
    read_demographics,
    read_table,
    score_distribution,
)

LABELS = dict(zip(PSQ_COLUMNS, ("Total", "Worries", "Tension", "Joy", "Demands"), strict=True))
BLUE = "#24658e"
ORANGE = "#a44620"


def save(fig, name, output):
    fig.savefig(output / f"{name}.png", dpi=160)
    plt.close(fig)


def plot_total(scores, output):
    fig, ax = plt.subplots(figsize=(8, 4), layout="constrained")
    bins = score_distribution(scores)
    bin_starts = [row["lower_inclusive"] for row in bins]
    participant_counts = [row["n"] for row in bins]
    ax.bar(bin_starts, participant_counts, width=10, align="edge", color=BLUE, edgecolor="white")

    mean = scores.mean()
    median = scores.median()
    ax.axvline(mean, color=ORANGE, label=f"Mean {mean:.1f}")
    ax.axvline(median, color="#202835", linestyle="--", label=f"Median {median:.1f}")
    ax.set(title=f"PSQ total score (n={len(scores)})", xlabel="Score (0–100)",
           ylabel="Participants", xlim=(0, 100), xticks=range(0, 101, 10))
    ax.legend(frameon=False)
    save(fig, "psq_total_distribution", output)


def plot_subscales(scores, output):
    fig, axes = plt.subplots(2, 2, figsize=(8, 6), sharex=True, sharey=True, layout="constrained")
    for ax, column in zip(axes.flat, PSQ_COLUMNS[1:], strict=True):
        counts = scores[column].dropna().round(4).value_counts().sort_index()
        ax.bar(counts.index, counts.values, width=5, color=BLUE)
        ax.set_title(f"{LABELS[column]} (n={counts.sum()})")
        ax.set_xlim(-3, 103)
    fig.supxlabel("Score (0–100)")
    fig.supylabel("Participants")
    save(fig, "psq_subscale_distributions", output)


def plot_groups(scores, groups, group_labels, title, filename, output):
    fig, ax = plt.subplots(figsize=(6, 4), layout="constrained")
    values = [scores.loc[groups[name]].dropna() for name in group_labels]
    labels = [f"{label} (n={len(group)})" for label, group in zip(group_labels.values(), values, strict=True)]
    ax.boxplot(
        values,
        tick_labels=labels,
        patch_artist=True,
        boxprops={"facecolor": "#d7e8f3"},
        medianprops={"color": ORANGE},
    )
    ax.set(title=title, ylabel="Total score (0–100)", ylim=(-3, 103))
    save(fig, filename, output)


def plot_correlations(scores, output):
    # Complete rows give each cell the same sample size. Total is derived from the subscales.
    subscales = scores[list(PSQ_COLUMNS[1:])].rename(columns=LABELS).dropna()
    correlation = subscales.corr(method="spearman")
    fig, ax = plt.subplots(figsize=(6, 4.5), layout="constrained")
    image = ax.imshow(correlation, cmap="RdBu", vmin=-1, vmax=1)
    ticks = range(len(correlation))
    ax.set(xticks=ticks, yticks=ticks, xticklabels=correlation.columns,
           yticklabels=correlation.index, title=f"Subscale correlations (n={len(subscales)})")
    for row in ticks:
        for col in ticks:
            value = correlation.iat[row, col]
            ax.text(col, row, f"{value:.2f}" if pd.notna(value) else "NA", ha="center", va="center",
                    color="white" if abs(value) > 0.65 else "#202835")
    fig.colorbar(image, ax=ax, label="Spearman correlation")
    save(fig, "psq_subscale_correlations", output)


def plot_coverage(scores, output):
    valid = scores.notna().sum().rename(index=LABELS)
    missing = len(scores) - valid
    fig, ax = plt.subplots(figsize=(8, 4), layout="constrained")
    ax.barh(valid.index, valid, color=BLUE, label="Valid")
    ax.barh(valid.index, missing, left=valid, color="#d3dce4", label="Missing or invalid")
    for label, count in valid.items():
        ax.text(len(scores) + 2, label, f"{count}/{len(scores)}", va="center")
    ax.invert_yaxis()
    ax.set(title="PSQ score availability", xlabel="Participants", xlim=(0, len(scores) * 1.16))
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.18), frameon=False, ncols=2)
    save(fig, "psq_score_availability", output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output

    demographics = read_demographics()
    _, psq, _ = read_table(args.input, required=PSQ_COLUMNS)
    raw_scores = pd.DataFrame.from_dict(psq, orient="index")
    aligned_scores = raw_scores.reindex(index=list(demographics), columns=PSQ_COLUMNS)
    scores = aligned_scores.fillna("").map(parse_score).astype(float)
    total_scores = scores[OVERALL]
    valid_totals = total_scores.dropna()
    if valid_totals.empty:
        raise ValueError("No valid PSQ total scores to plot")

    output.mkdir(parents=True, exist_ok=True)
    groups = participant_groups(demographics)
    plot_total(valid_totals, output)
    plot_subscales(scores, output)
    plot_groups(total_scores, groups, {"younger": "Younger", "older": "Older"},
                "PSQ total by age group", "psq_by_age", output)
    plot_groups(total_scores, groups, {"female": "Women", "male": "Men"},
                "PSQ total by recorded gender", "psq_by_gender", output)
    plot_correlations(scores, output)
    plot_coverage(scores, output)
    print(f"PSQ figures: {output}")


if __name__ == "__main__":
    main()
