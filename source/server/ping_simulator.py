import random

from server.config import load_config


def generate_ping_output(target_ip: str, loss_percent: int) -> str:
    """
    Generate Windows-style ping output with realistic GEO satellite latency.

    loss_percent: 0 → all succeed, 50 → 2/4 timeout, 75 → 3/4 timeout, 100 → all timeout.
    """
    config = load_config()
    sim = config["simulation"]
    packet_count = sim["ping_packet_count"]
    base_latency = sim["base_latency_ms"]
    jitter = sim["jitter_ms"]
    packet_size = 32

    lines: list[str] = []
    lines.append(f"Pinging {target_ip} with {packet_size} bytes of data:")

    # Determine how many packets are lost
    lost_count = round(packet_count * loss_percent / 100)
    success_count = packet_count - lost_count

    # Build packet sequence with random distribution of timeouts
    packets = ["success"] * success_count + ["timeout"] * lost_count
    random.shuffle(packets)

    latencies: list[int] = []
    for packet in packets:
        if packet == "success":
            latency = base_latency + random.randint(-jitter, jitter)
            latencies.append(latency)
            lines.append(
                f"Reply from {target_ip}: bytes={packet_size} time={latency}ms TTL=64"
            )
        else:
            lines.append("Request timed out.")

    lines.append("")
    lines.append(f"Ping statistics for {target_ip}:")

    # Recalculate actual loss percent for display
    actual_loss_pct = round(lost_count / packet_count * 100) if packet_count > 0 else 0
    lines.append(
        f"    Packets: Sent = {packet_count}, Received = {success_count}, "
        f"Lost = {lost_count} ({actual_loss_pct}% loss),"
    )

    if latencies:
        lines.append("Approximate round trip times in milli-seconds:")
        avg_latency = round(sum(latencies) / len(latencies))
        lines.append(
            f"    Minimum = {min(latencies)}ms, Maximum = {max(latencies)}ms, "
            f"Average = {avg_latency}ms"
        )

    return "\n".join(lines)
