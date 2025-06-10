import gpiod

chip = gpiod.Chip('gpiochip0')  # Or use '/dev/gpiochip0'

print(f"Lines for {chip.path} ({chip.label}):")
print(f"{'Offset':>6}  {'Name':<16}  {'Direction':<10}  {'Used by'}")

for line in chip:
    info = line.line_info
    offset = info.offset
    name = info.name or ""
    consumer = info.consumer or ""
    direction = "output" if info.direction == gpiod.LineDirection.OUTPUT else "input"
    print(f"{offset:>6}  {name:<16}  {direction:<10}  {consumer}")

chip.close()