"""Test Chinese font rendering using the actual report module."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

print("=" * 60)
print("Testing Report Module with Chinese Fonts")
print("=" * 60)

# Import report module (this will trigger font configuration)
print("\n1. Importing report module...")
from src.report import plot_hypnogram, plot_stage_distribution, fig_to_base64
print("   ✓ Report module imported")

# Create dummy predictions
print("\n2. Creating test data...")
dummy_predictions = pd.DataFrame({
    "predicted_label": [0, 1, 2, 1, 0, 2, 1, 1, 0, 2] * 20  # 200 epochs
})
print(f"   ✓ Created {len(dummy_predictions)} epochs")

# Test hypnogram
print("\n3. Generating hypnogram...")
try:
    hypo_fig = plot_hypnogram(dummy_predictions)
    hypo_path = Path(__file__).resolve().parent / "output" / "test_hypnogram_fixed.png"
    hypo_path.parent.mkdir(exist_ok=True)
    hypo_fig.savefig(hypo_path, dpi=150, bbox_inches="tight", facecolor=hypo_fig.get_facecolor())
    plt.close(hypo_fig)
    print(f"   ✓ Hypnogram saved to: {hypo_path}")
except Exception as e:
    print(f"   ✗ Error: {e}")
    import traceback
    traceback.print_exc()

# Test stage distribution
print("\n4. Generating stage distribution...")
try:
    dist_fig = plot_stage_distribution(dummy_predictions)
    dist_path = Path(__file__).resolve().parent / "output" / "test_distribution_fixed.png"
    dist_fig.savefig(dist_path, dpi=150, bbox_inches="tight", facecolor=dist_fig.get_facecolor())
    plt.close(dist_fig)
    print(f"   ✓ Distribution chart saved to: {dist_path}")
except Exception as e:
    print(f"   ✗ Error: {e}")
    import traceback
    traceback.print_exc()

# Test base64 conversion (used in HTML reports)
print("\n5. Testing base64 conversion...")
try:
    test_fig = plot_hypnogram(dummy_predictions.head(50))
    b64_str = fig_to_base64(test_fig)
    print(f"   ✓ Base64 conversion successful (length: {len(b64_str)} chars)")
except Exception as e:
    print(f"   ✗ Error: {e}")

print("\n" + "=" * 60)
print("Test completed!")
print("=" * 60)
print("\nPlease check the generated PNG files in the 'output' folder.")
print("Chinese characters should now be visible in the charts.")
