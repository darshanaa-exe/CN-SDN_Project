#!/usr/bin/env python3
import re
import os

RESULTS_DIR = "results"
FILE_PATH = os.path.join(RESULTS_DIR, "rtt_results.txt")

os.makedirs(RESULTS_DIR, exist_ok=True)


def ping_rtt(src_host, dst_ip, count=10):
    result = src_host.cmd(f"ping -c {count} {dst_ip}")

    summary = re.search(
        r"rtt min/avg/max/mdev = ([\d.]+)/([\d.]+)/([\d.]+)/([\d.]+)",
        result
    )

    stats = {}
    if summary:
        stats = {
            "min": round(float(summary.group(1)), 2),
            "avg": round(float(summary.group(2)), 2),
            "max": round(float(summary.group(3)), 2),
            "mdev": round(float(summary.group(4)), 2),
        }

    loss_match = re.search(r"(\d+)% packet loss", result)
    stats["loss"] = int(loss_match.group(1)) if loss_match else None

    return stats


def format_table(results):
    header = f"{'Path':<10} {'Min RTT':<12} {'Avg RTT':<12} {'Max RTT':<12} {'Mdev':<12} {'Loss %':<8}"
    sep = "-" * len(header)

    lines = [header, sep]

    for r in results:
        line = (
            f"{r['path']:<10} "
            f"{str(r['min']):<12} "
            f"{str(r['avg']):<12} "
            f"{str(r['max']):<12} "
            f"{str(r['mdev']):<12} "
            f"{str(r['loss']):<8}"
        )
        lines.append(line)

    return "\n".join(lines)


def run_all_measurements(net):
    hosts = sorted(net.hosts, key=lambda h: h.name)

    results = []

    print("\n===== MEASUREMENT STARTED =====")

    for i in range(len(hosts)):
        for j in range(i + 1, len(hosts)):
            src = hosts[i]
            dst = hosts[j]
            dst_ip = dst.IP()
            label = f"{src.name}->{dst.name}"

            print(f"\n[*] Measuring {label} ...")
            stats = ping_rtt(src, dst_ip, count=10)

            row = {
                "path": label,
                "min": stats.get("min", "N/A"),
                "avg": stats.get("avg", "N/A"),
                "max": stats.get("max", "N/A"),
                "mdev": stats.get("mdev", "N/A"),
                "loss": stats.get("loss", "N/A")
            }

            results.append(row)

            print(
                f"    min/avg/max/mdev = "
                f"{row['min']} / {row['avg']} / {row['max']} / {row['mdev']} ms"
            )
            print(f"    packet loss = {row['loss']}%")

    table_text = format_table(results)

    with open(FILE_PATH, "w") as f:
        f.write("===== RTT MEASUREMENT RESULTS =====\n\n")
        f.write(table_text + "\n")

    print("\n===== CLEAN RTT SUMMARY =====")
    print(table_text)

    print(f"\n[+] Results saved to: {FILE_PATH}")

    return FILE_PATH
