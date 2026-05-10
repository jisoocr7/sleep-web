"""Test script to verify Chinese font rendering in matplotlib charts."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import pandas as pd
import numpy as np

print("=" * 60)
print("Testing Chinese Font Configuration")
print("=" * 60)

# Check available fonts
print("\n1. Available Chinese fonts:")
chinese_fonts = []
for f in fm.findSystemFonts():
    try:
        name = fm.FontProperties(fname=f).get_name()
        if any(k in name.lower() for k in ['hei', 'song', 'kai', 'ming', 'noto sans cjk', 'wenquanyi', 'microsoft yahei', 'simhei', 'simsun']):
            chinese_fonts.append(name)
            print(f"   ✓ {name}")
    except:
        pass

if not chinese_fonts:
    print("   ⚠ No Chinese fonts found! Using DejaVu Sans fallback.")

# Test plot with Chinese text
print("\n2. Creating test plot with Chinese text...")
fig, ax = plt.subplots(figsize=(8, 4), facecolor="#FEFAF5")
ax.set_facecolor("#FEFAF5")

# Sample data
x = np.linspace(0, 10, 100)
y = np.sin(x)

ax.plot(x, y, color="#5DAF8B", linewidth=2)
ax.set_title("中文标题测试 - Sleep Analysis", fontsize=16, fontweight="bold", 
             fontproperties=fm.FontProperties(size=16, weight='bold'))
ax.set_xlabel("时间 (小时)", fontsize=13, fontproperties=fm.FontProperties(size=13))
ax.set_ylabel("心率 (bpm)", fontsize=13, fontproperties=fm.FontProperties(size=13))
ax.tick_params(colors="#6D5C4F", labelsize=11)

# Add legend with Chinese
ax.legend(["心率曲线"], loc="upper right", prop=fm.FontProperties(size=12))

plt.tight_layout()

# Save test image
output_path = Path(__file__).resolve().parent / "test_chinese_font.png"
fig.savefig(output_path, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
plt.close(fig)

print(f"   ✓ Test plot saved to: {output_path}")
print(f"   ✓ Please check if Chinese characters are visible in the image")

# Test report module imports
print("\n3. Testing report module imports...")
try:
    from src.report import plot_hypnogram, plot_stage_distribution
    print("   ✓ Report module imported successfully")
    
    # Create dummy predictions
    dummy_predictions = pd.DataFrame({
        "predicted_label": [0, 1, 2, 1, 0, 2, 1, 1, 0, 2] * 10
    })
    
    print("   ✓ Generating hypnogram test...")
    hypo_fig = plot_hypnogram(dummy_predictions)
    hypo_path = Path(__file__).resolve().parent / "test_hypnogram.png"
    hypo_fig.savefig(hypo_path, dpi=150, bbox_inches="tight")
    plt.close(hypo_fig)
    print(f"   ✓ Hypnogram saved to: {hypo_path}")
    
    print("   ✓ Generating stage distribution test...")
    dist_fig = plot_stage_distribution(dummy_predictions)
    dist_path = Path(__file__).resolve().parent / "test_distribution.png"
    dist_fig.savefig(dist_path, dpi=150, bbox_inches="tight")
    plt.close(dist_fig)
    print(f"   ✓ Distribution chart saved to: {dist_path}")
    
except Exception as e:
    print(f"   ✗ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("Font configuration test completed!")
print("=" * 60)
print("\nNext steps:")
print("1. Check the generated PNG files for Chinese text visibility")
print("2. If Chinese text is still missing, install Chinese fonts on your system")
print("3. For PythonAnywhere, run: sudo apt-get install fonts-wqy-microhei")
