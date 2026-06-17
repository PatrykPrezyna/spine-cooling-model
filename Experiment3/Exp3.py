import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import sys
import os

print("="*70)
print("DEBUGGING PUMP SPEED IMPACT ANALYSIS")
print("="*70)

# Check Python and library versions
print(f"Python version: {sys.version}")
print(f"Pandas version: {pd.__version__}")
print(f"Matplotlib version: {plt.matplotlib.__version__}")
print(f"Current directory: {os.getcwd()}")

# List files in current directory
print(f"\nFiles in current directory:")
for f in os.listdir('.'):
    if f.endswith('.csv'):
        print(f"  ✓ {f}")

# Try to read the file
try:
    df = pd.read_csv('sensor_log_20260616_092249.csv')
    print(f"\n✓ CSV file loaded successfully")
    print(f"  Shape: {df.shape}")
    print(f"  Columns: {list(df.columns)}")
except Exception as e:
    print(f"\n✗ ERROR loading CSV: {e}")
    sys.exit(1)

# Set backend explicitly
print(f"\nCurrent matplotlib backend: {plt.get_backend()}")
print("Trying to set backend to 'Agg' (non-interactive)...")
plt.switch_backend('Agg')
print(f"New backend: {plt.get_backend()}")

# Convert timestamp to datetime
df['timestamp'] = pd.to_datetime(df['timestamp'])
df['time_seconds'] = (df['timestamp'] - df['timestamp'].iloc[0]).dt.total_seconds()

print(f"\n✓ Data processed")
print(f"  Time range: {df['time_seconds'].min():.2f}s to {df['time_seconds'].max():.2f}s")
print(f"  Pump speeds: {sorted(df['peristaltic_pump_set_speed_rpm'].unique())}")
print(f"  Cart out temp range: {df['cart_out_c'].min():.2f}°C to {df['cart_out_c'].max():.2f}°C")

# Create figure
print(f"\nCreating figure...")
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))
print(f"✓ Figure created")

try:
    # ===== PLOT 1: Time Series with Dual Axes =====
    print("Creating Plot 1 (Time Series)...")
    color_pump = '#FF6B6B'
    color_temp = '#4ECDC4'

    ax1_twin = ax1.twinx()

    # Plot pump speed
    line1 = ax1.plot(df['time_seconds'], df['peristaltic_pump_set_speed_rpm'], 'o-', 
                     linewidth=2.5, markersize=4, label='Pump Speed (RPM)', 
                     color=color_pump, alpha=0.8)
    ax1.set_ylabel('Pump Speed (RPM)', fontsize=12, fontweight='bold', color=color_pump)
    ax1.tick_params(axis='y', labelcolor=color_pump)

    # Plot cart out temperature
    line2 = ax1_twin.plot(df['time_seconds'], df['cart_out_c'], 's-', 
                          linewidth=2.5, markersize=4, label='Cart Out Temp (°C)', 
                          color=color_temp, alpha=0.8)
    ax1_twin.set_ylabel('Cart Out Temperature (°C)', fontsize=12, fontweight='bold', color=color_temp)
    ax1_twin.tick_params(axis='y', labelcolor=color_temp)

    ax1.set_xlabel('Time (seconds)', fontsize=12, fontweight='bold')
    ax1.set_title('Impact of Pump Speed on Cart Out Temperature (Time Series)', 
                  fontsize=14, fontweight='bold')
    ax1.grid(True, alpha=0.3)

    lines = line1 + line2
    labels = [l.get_label() for l in lines]
    ax1.legend(lines, labels, loc='upper left', fontsize=11, framealpha=0.95)
    print("✓ Plot 1 created")

    # ===== PLOT 2: Scatter Plot =====
    print("Creating Plot 2 (Scatter)...")
    speeds = df['peristaltic_pump_set_speed_rpm'].values
    temps = df['cart_out_c'].values

    scatter = ax2.scatter(speeds, temps, c=df['time_seconds'], cmap='viridis', 
                         s=100, alpha=0.6, edgecolors='black', linewidth=0.5)

    # Add trend line if there's variation in pump speed
    unique_speeds = df['peristaltic_pump_set_speed_rpm'].unique()
    if len(unique_speeds) > 1:
        z = np.polyfit(speeds, temps, 2)
        p = np.poly1d(z)
        speed_range = np.linspace(speeds.min(), speeds.max(), 100)
        ax2.plot(speed_range, p(speed_range), "r--", linewidth=2.5, alpha=0.8, 
                label='Trend (polynomial fit)')
        ax2.legend(fontsize=11, framealpha=0.95)

    ax2.set_xlabel('Pump Speed (RPM)', fontsize=12, fontweight='bold')
    ax2.set_ylabel('Cart Out Temperature (°C)', fontsize=12, fontweight='bold')
    ax2.set_title('Correlation: Pump Speed vs Cart Out Temperature', fontsize=14, fontweight='bold')
    ax2.grid(True, alpha=0.3)

    cbar = plt.colorbar(scatter, ax=ax2)
    cbar.set_label('Time (seconds)', fontsize=11, fontweight='bold')
    print("✓ Plot 2 created")

    # Tight layout
    plt.tight_layout()
    print("✓ Layout adjusted")

except Exception as e:
    print(f"\n✗ ERROR creating plots: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Try to save
output_file = 'pump_speed_impact.png'
try:
    print(f"\nSaving to {output_file}...")
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"✓ Saved successfully to {output_file}")
    
    # Check file exists
    if os.path.exists(output_file):
        file_size = os.path.getsize(output_file)
        print(f"  File size: {file_size} bytes")
    else:
        print(f"✗ File not found after save!")
        
except Exception as e:
    print(f"✗ ERROR saving file: {e}")
    import traceback
    traceback.print_exc()

# Try to show (will likely not work in some environments)
try:
    print(f"\nAttempting to display plot...")
    plt.show()
    print("✓ Plot displayed")
except Exception as e:
    print(f"Note: Could not display plot (expected in some environments): {e}")

# Print statistics
print(f"\n" + "="*70)
print("PUMP SPEED IMPACT ON CART OUT TEMPERATURE")
print("="*70)

correlation = df['peristaltic_pump_set_speed_rpm'].corr(df['cart_out_c'])
print(f"Correlation coefficient: {correlation:.4f}")

if abs(correlation) < 0.3:
    print("  ↓ Weak correlation - Pump speed has minimal effect")
elif abs(correlation) < 0.7:
    print("  ↓ Moderate correlation - Some relationship exists")
else:
    print("  ↓ Strong correlation - Clear relationship exists")

if correlation > 0:
    print("\n  Direction: Higher pump speed → Higher cart out temperature")
else:
    print("\n  Direction: Higher pump speed → Lower cart out temperature")

print("\nStatistics by Pump Speed:")
for speed in sorted(df['peristaltic_pump_set_speed_rpm'].unique()):
    mask = df['peristaltic_pump_set_speed_rpm'] == speed
    if mask.sum() > 0:
        avg_temp = df[mask]['cart_out_c'].mean()
        min_temp = df[mask]['cart_out_c'].min()
        max_temp = df[mask]['cart_out_c'].max()
        std_temp = df[mask]['cart_out_c'].std()
        print(f"\nPump Speed {speed:.2f} RPM ({mask.sum()} samples):")
        print(f"  Avg: {avg_temp:.2f}°C | Min: {min_temp:.2f}°C | Max: {max_temp:.2f}°C | Std: {std_temp:.2f}°C")

print("="*70)
print("\n✓ Analysis complete!")
print(f"\nCheck for '{output_file}' in your current directory")