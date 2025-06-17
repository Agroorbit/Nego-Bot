import numpy as np
import matplotlib.pyplot as plt

# Parameters
max_margin = 20
sigmoid_k = 0.01
sigmoid_midpoint = 750
sigmoid_threshold = 50

plateau_margin = 20
plateau_order_count = 900    # Plateau starts here (earlier)
decline_rate = 5             # Margin reduction per step (more visible)
decline_step_orders = 50     # Orders between decline steps (shorter for more steps)
decline_steps = 5            # Number of steps to show

# Sigmoid margin up to plateau
order_counts_increase = np.arange(0, plateau_order_count + 1)
sigmoid_margin = np.where(
    order_counts_increase < sigmoid_threshold,
    0,
    max_margin / (1 + np.exp(-sigmoid_k * (order_counts_increase - sigmoid_midpoint)))
)

# Stepwise decline after plateau
step_down_counts = []
step_down_margins = []
current_margin = plateau_margin

for i in range(decline_steps):
    start_order = plateau_order_count + i * decline_step_orders
    end_order = plateau_order_count + (i + 1) * decline_step_orders
    for order in range(start_order, end_order):
        sigmoid_floor = max_margin / (1 + np.exp(-sigmoid_k * (order - sigmoid_midpoint)))
        final_margin = max(current_margin, sigmoid_floor)
        step_down_counts.append(order)
        step_down_margins.append(final_margin)
    current_margin -= decline_rate

# Combine both parts
all_order_counts = np.concatenate([order_counts_increase, step_down_counts])
all_margins = np.concatenate([sigmoid_margin, step_down_margins])

plt.figure(figsize=(12, 6))
plt.plot(all_order_counts, all_margins, label='Margin Journey (Increase + Stepwise Decline)', color='tab:blue', linewidth=3)
plt.axhline(y=max_margin, linestyle='--', color='tab:green', alpha=0.5, label='Plateau (20%)')
plt.axvline(x=plateau_order_count, color='tab:orange', linestyle='--', label='Plateau Start / Decline Trigger')

plt.xlabel('Order Count (Units Sold)')
plt.ylabel('Margin (%)')
plt.title('Full Journey: Margin Increase and Stepwise Decline vs Order Count')
plt.legend()
plt.grid(True, linestyle='--', alpha=0.4)
plt.tight_layout()
plt.show()
