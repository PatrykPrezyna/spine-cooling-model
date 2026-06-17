import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# Read the complete CSV file
df = pd.read_csv('sensor_log_20260616_092249.csv')

# Convert timestamp to datetime
df['timestamp'] = pd.to_datetime(df['timestamp'])

# Calculate time in seconds from start
df['time_seconds'] = (df['timestamp'] - df['timestamp'].iloc[0]).dt.total_seconds()

# Find when compressor turns on
compressor_on_idx = df[df['compressor_cooling'] == 1].index[0]
compressor_on_time = df.loc[compressor_on_idx, 'time_seconds']

# Get final index
final_idx = df.index[-1]

print(f"Total data points: {len(df)}")
print(f"Total duration: {df['time_seconds'].iloc[-1]:.2f} seconds")
print(f"Compressor activated at: {compressor_on_time:.2f} seconds")
print(f"\nHeat Ex 1 temperatures:")
print(f"  Start: {df.loc[compressor_on_idx, 'heat_ex_c']:.2f}°C")
print(f"  End:   {df.loc[final_idx, 'heat_ex_c']:.2f}°C")
print(f"  Drop:  {df.loc[compressor_on_idx, 'heat_ex_c'] - df.loc[final_idx, 'heat_ex_c']:.2f}°C")

print(f"\nHeat Ex 2 temperatures:")
print(f"  Start: {df.loc[compressor_on_idx, 'heat_ex_2_c']:.2f}°C")
print(f"  End:   {df.loc[final_idx, 'heat_ex_2_c']:.2f}°C")
print(f"  Drop:  {df.loc[compressor_on_idx, 'heat_ex_2_c'] - df.loc[final_idx, 'heat_ex_2_c']:.2f}°C")

# Create simple visualization
fig, ax = plt.subplots(figsize=(14, 7))

# Plot temperatures
ax.plot(df['time_seconds'], df['heat_ex_c'], 'o-', linewidth=2.5, markersize=5, 
        label='Heat Exchanger 1', color='#FF6B6B', alpha=0.8)
ax.plot(df['time_seconds'], df['heat_ex_2_c'], 's-', linewidth=2.5, markersize=5, 
        label='Heat Exchanger 2', color='#4ECDC4', alpha=0.8)

# Plot compressor state as a line at the bottom
compressor_line = df['compressor_cooling'].values * (df['heat_ex_c'].min() - 2)
ax.plot(df['time_seconds'], compressor_line, linewidth=3, 
        label='Compressor ON/OFF', color='green', alpha=0.6)

# Add annotations
cooling_duration = df['time_seconds'].iloc[-1] - compressor_on_time
heat_ex_1_drop = df.loc[compressor_on_idx, 'heat_ex_c'] - df.loc[final_idx, 'heat_ex_c']
heat_ex_2_drop = df.loc[compressor_on_idx, 'heat_ex_2_c'] - df.loc[final_idx, 'heat_ex_2_c']

textstr = f'Stabilization Time: {cooling_duration:.1f} seconds\n'
textstr += f'Heat Ex 1: {df.loc[compressor_on_idx, "heat_ex_c"]:.2f}°C → {df.loc[final_idx, "heat_ex_c"]:.2f}°C (drop: {heat_ex_1_drop:.2f}°C)\n'
textstr += f'Heat Ex 2: {df.loc[compressor_on_idx, "heat_ex_2_c"]:.2f}°C → {df.loc[final_idx, "heat_ex_2_c"]:.2f}°C (drop: {heat_ex_2_drop:.2f}°C)'

ax.text(0.5, 0.95, textstr, transform=ax.transAxes, 
        ha='center', va='top', fontsize=11, bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.5),
        fontweight='bold', family='monospace')

# Labels and formatting
ax.set_xlabel('Time (seconds)', fontsize=13, fontweight='bold')
ax.set_ylabel('Temperature (°C)', fontsize=13, fontweight='bold')
ax.set_title('Heat Exchanger Temperature Stabilization', fontsize=15, fontweight='bold')
ax.grid(True, alpha=0.3)
ax.legend(loc='upper right', fontsize=11, framealpha=0.95)

plt.tight_layout()
plt.savefig('heat_exchanger_stabilization.png', dpi=300, bbox_inches='tight')
print("\n✓ Saved as 'heat_exchanger_stabilization.png'")
plt.show()

# Print detailed summary
print("\n" + "="*70)
print("HEAT EXCHANGER TEMPERATURE STABILIZATION SUMMARY")
print("="*70)
print(f"⏱️  Compressor Activated at: {compressor_on_time:.2f} seconds")
print(f"⏱️  Total Cooling Duration: {cooling_duration:.2f} seconds")
print(f"\n🌡️  Heat Exchanger 1:")
print(f"   Initial Temp: {df.loc[compressor_on_idx, 'heat_ex_c']:.2f}°C")
print(f"   Final Temp: {df.loc[final_idx, 'heat_ex_c']:.2f}°C")
print(f"   Total Drop: {heat_ex_1_drop:.2f}°C")

print(f"\n🌡️  Heat Exchanger 2:")
print(f"   Initial Temp: {df.loc[compressor_on_idx, 'heat_ex_2_c']:.2f}°C")
print(f"   Final Temp: {df.loc[final_idx, 'heat_ex_2_c']:.2f}°C")
print(f"   Total Drop: {heat_ex_2_drop:.2f}°C")
print("\n" + "="*70)