# Metrics and Evaluation

CLEAR reports six primary evaluation metrics.

## 1. Success Rate (SR)

Success Rate measures the percentage of attempted benchmarks that are repaired successfully.

$$\mathrm{SR} = \frac{N_{\mathrm{successful}}}{N_{\mathrm{total}}} \times 100$$

Where:

* $N_{\mathrm{successful}}$ is the number of successfully repaired benchmarks.
* $N_{\mathrm{total}}$ is the total number of attempted benchmarks.

## 2. Pass@1

Pass@1 measures the percentage of benchmarks repaired successfully on the first repair attempt.

$$\mathrm{Pass@1} = \frac{N_{\mathrm{successful\ at\ iteration\ 1}}}{N_{\mathrm{total}}} \times 100$$

Where $N_{\mathrm{successful\ at\ iteration\ 1}}$ is the number of benchmarks repaired successfully during the first iteration.

## 3. Time to Resolution (TTR)

Time to Resolution measures the mean repair time for successfully repaired benchmarks.

$$\mathrm{TTR} = \frac{\sum_{i=1}^{N_{\mathrm{successful}}} T_i}{N_{\mathrm{successful}}}$$

Where $T_i$ is the repair time for successfully repaired benchmark $i$.

## 4. Iteration Efficiency (IE)

Iteration Efficiency rewards successful repairs that require fewer iterations.

$$\mathrm{IE} = \frac{1}{N_{\mathrm{successful}}} \sum_{i=1}^{N_{\mathrm{successful}}} \frac{1}{k_i}$$

Where $k_i$ is the number of repair iterations required for successfully repaired benchmark $i$.

> A benchmark repaired in one iteration contributes 1, while benchmarks requiring additional iterations contribute progressively smaller values.

## 5. Average Repair Iterations (ARI)

Average Repair Iterations measures the mean number of iterations required to repair successful benchmarks.

$$\mathrm{ARI} = \frac{\sum_{i=1}^{N_{\mathrm{successful}}} k_i}{N_{\mathrm{successful}}}$$

Where $k_i$ is the number of repair iterations required for successfully repaired benchmark $i$.

## 6. Failure Rate (FR)

Failure Rate measures the percentage of attempted benchmarks that are not repaired successfully.

$$\mathrm{FR} = \frac{N_{\mathrm{failed}}}{N_{\mathrm{total}}} \times 100$$

Where $N_{\mathrm{failed}}$ is the number of benchmarks that remain unresolved after the permitted repair process.

Provided that every attempted benchmark is classified as either successful or failed:

$$\mathrm{SR} + \mathrm{FR} = 100\%$$

---

## Reporting Notes

* **Success Rate** and **Failure Rate** are calculated using all attempted benchmarks.
* **Pass@1** uses the total number of attempted benchmarks as its denominator, allowing direct comparison across experiments.
* **Time to Resolution**, **Iteration Efficiency**, and **Average Repair Iterations** are calculated only over successfully repaired benchmarks.
* Failed benchmarks are excluded from TTR, IE, and ARI because they do not have a successful resolution time or final successful iteration count.
* When $N_{\mathrm{successful}} = 0$, TTR, IE, and ARI should be reported as **undefined** or **not applicable** rather than as zero.