"""Test Chinese font rendering in report charts."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from src.report import plot_hypnogram, plot_stage_distribution, fig_to_base64

# Create dummy predictions data
dummy_predictions = pd.DataFrame({
    "predicted_label": [0, 1, 2, 1, 0, 2, 1, 1, 0, 2] * 20  # 200 epochs
})

print("Testing hypnogram chart...")
hypo_fig = plot_hypnogram(dummy_predictions)
hypo_path = Path(__file__).resolve().parent / "output" / "test_hypnogram_chinese.png"
hypo_path.parent.mkdir(exist_ok=True)
hypo_fig.savefig(hypo_path, dpi=150, bbox_inches="tight", facecolor=hypo_fig.get_facecolor())
plt.close(hypo_fig)
print(f"✓ Hypnogram saved to: {hypo_path}")

print("\nTesting stage distribution chart...")
dist_fig = plot_stage_distribution(dummy_predictions)
dist_path = Path(__file__).resolve().parent / "output" / "test_distribution_chinese.png"
dist_fig.savefig(dist_path, dpi=150, bbox_inches="tight", facecolor=dist_fig.get_facecolor())
plt.close(dist_fig)
print(f"✓ Distribution chart saved to: {dist_path}")

print("\n✅ All tests passed! Check the output images for Chinese text rendering.")
