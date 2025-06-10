import gpiod

# The main GPIO controller is usually /dev/gpiochip0 on Raspberry Pi 5
chip = gpiod.Chip('gpiochip0')

print(f"Lines for {chip.name} ({chip.label}):")
print(f"{'Offset':>6}  {'Name':<16}  {'Direction':<10}  {'Used by'}")

for line in chip.get_all_lines():
    info = line.line_info
    offset = info.offset
    name = info.name or ""
    consumer = info.consumer or ""
    direction = "output" if info.direction == gpiod.LineDirection.OUTPUT else "input"
    print(f"{offset:>6}  {name:<16}  {direction:<10}  {consumer}")

chip.close()