import gpiod

chip_path = "/dev/gpiochip0"
chip = gpiod.Chip(chip_path)

info = chip.get_info()
print(f"Chip path: {chip.path}")
print(f"Label: {getattr(info, 'label', 'N/A')}")
print(f"Name: {getattr(info, 'name', 'N/A')}")
print(f"Number of lines: {info.num_lines}")
print()
print(f"{'Offset':>6}  {'Name':<16}  {'Direction':<8}  {'Active-low':<10}  {'Used by'}")

for offset in range(info.num_lines):
    line_info = chip.get_line_info(offset)
    line_name = getattr(line_info, "name", "")
    consumer = getattr(line_info, "consumer", "")
    direction = "output" if line_info.direction == gpiod.line.Direction.OUTPUT else "input"
    active_low = str(getattr(line_info, "active_low", False))
    print(f"{offset:>6}  {line_name:<16}  {direction:<8}  {active_low:<10}  {consumer}")

chip.close()