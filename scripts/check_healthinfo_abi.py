"""Compile-check the original SM8150 touch telemetry event numbering."""
import argparse
import pathlib
import re
import subprocess
import tempfile


def check(vendor):
    header = vendor / "vendor/oplus/kernel/touchpanel/oplus_touchscreen/touchpanel_healthinfo.h"
    text = header.read_text()
    enum = re.search(r"typedef enum\s*\{[^{}]+\}\s*healthinfo_type;", text)
    if not enum:
        raise ValueError("Health event enum missing")
    extensions = "\n".join(line for line in text.splitlines()
                           if line.startswith(("#define HEALTH_GESTURE_READ ", "#define HEALTH_BELOW_RATE ")))
    # Original Image: dispatch accepts 0..16; its CRC is 0xa56a839d.
    original = ("TOUCH", "GESTURE", "FINGERPRINT", "FACE_DETECT", "REPORT",
                "PROBE", "RESUME", "SUSPEND", "TEST_AUTO", "TEST_BLACKSCREEN",
                "BUS", "ALLOC_SUCCESS", "ALLOC_FAILED", "FW_UPDATE",
                "FW_UPDATE_COST", "GRIP", "GRIP_UP")
    source = enum[0] + "\n" + extensions + "\n"
    for value, name in enumerate(original):
        source += '_Static_assert(HEALTH_' + name + ' == ' + str(value) + ', "stock event ID");\n'
    source += '''
_Static_assert(sizeof(healthinfo_type) == 4, "stock enum width");
_Static_assert(HEALTH_GESTURE_READ > HEALTH_GRIP_UP &&
               HEALTH_BELOW_RATE > HEALTH_GRIP_UP &&
               HEALTH_GESTURE_READ != HEALTH_BELOW_RATE, "private event IDs");
int main(void) { return 0; }
'''
    with tempfile.TemporaryDirectory() as directory:
        c = pathlib.Path(directory) / "events.c"
        binary = pathlib.Path(directory) / "events"
        c.write_text(source)
        subprocess.run(["cc", "-std=gnu11", "-Wall", "-Werror", str(c), "-o", str(binary)], check=True)
        subprocess.run([str(binary)], check=True)
    print("SM8150 touch telemetry: 17 stock event IDs, enum width and private extensions verified.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("vendor", type=pathlib.Path)
    check(parser.parse_args().vendor)
