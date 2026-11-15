"""TODO C: metrics from received measurements, independent of transport.

records is a list of dictionaries: {stamp: float seconds, arrival: monotonic
seconds, value: float gyro_z or None}. A backwards stamp starts a new epoch;
only use the newest epoch. Deduplicate stamps, retaining the first arrival.
Return keys: samples, sim_hz, wall_hz, gyro_mean, gyro_std, epochs.
epochs is zero for empty input, otherwise one plus the number of backwards
stamp jumps in the raw sequence. samples counts unique stamps in the newest
epoch. With fewer than two unique samples both rates
are None. gyro_mean and gyro_std are None without finite gyro samples;
gyro_std is population standard deviation (ddof=0). Do not mutate records.
See tests/test_homework_metrics.py for examples and docs for the contract.
"""

import math
from statistics import fmean, pstdev


def analyze_samples(records):
    result = {
        "samples": 0,
        "sim_hz": None,
        "wall_hz": None,
        "gyro_mean": None,
        "gyro_std": None,
        "epochs": 0,
    }

    if not records:
        return result

    # Detect epochs in the original arrival order, before deduplication.
    epochs = 1
    epoch_start = 0

    for index in range(1, len(records)):
        if records[index]["stamp"] < records[index - 1]["stamp"]:
            epochs += 1
            epoch_start = index

    # Keep the first complete record for each stamp in the newest epoch.
    samples = []
    seen_stamps = set()

    for index in range(epoch_start, len(records)):
        record = records[index]
        stamp = record["stamp"]

        if stamp not in seen_stamps:
            seen_stamps.add(stamp)
            samples.append(record)

    count = len(samples)
    result["samples"] = count
    result["epochs"] = epochs

    if count >= 2:
        sim_span = samples[-1]["stamp"] - samples[0]["stamp"]
        wall_span = samples[-1]["arrival"] - samples[0]["arrival"]

        if sim_span > 0:
            result["sim_hz"] = (count - 1) / sim_span

        if wall_span > 0:
            result["wall_hz"] = (count - 1) / wall_span

    gyro_values = [
        record["value"]
        for record in samples
        if record["value"] is not None
        and math.isfinite(record["value"])
    ]

    if gyro_values:
        result["gyro_mean"] = fmean(gyro_values)
        result["gyro_std"] = pstdev(gyro_values)

    return result
