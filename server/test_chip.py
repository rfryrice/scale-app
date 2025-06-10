import gpiod

chip = gpiod.Chip('gpiochip0')  # Use 'gpiochip0' or '/dev/gpiochip0' as appropriate

print("GPIO Line Info for chip:", chip.path if hasattr(chip, 'path') else chip.name)

for offset in range(chip.num_lines):
    line = chip.get_line(offset)
    info = line.line_info
    # Defensive: some versions have .name, some do not
    line_name = getattr(info, 'name', '')
    consumer = getattr(info, 'consumer', '')
    direction = "output" if info.direction == gpiod.LineDirection.OUTPUT else "input"
    print(f"Offset: {offset:>3}  Name: {line_name:<16}  Direction: {direction:<6}  Used by: {consumer}")

chip.close()