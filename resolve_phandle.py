import fire
import os
import logging
logging.basicConfig(level=logging.INFO)


# Utilities

SCRIPTHOME = os.path.realpath(__file__)
# Properties that contain pointers and edited by this script
PTR_PROPERTIES = {
    "assigned-clocks",
    "clocks",
    "dmas",
    "gpio-controller",
    "gpios",
    "hwlocks",
    "interrupt-extended",
    "interrupt-parent",
    "iommus",
    "iommus",
    "memory-region",
    "msi-parent",
    "phys",
    "power-dodmain",
    "pwms",
    "regulators",
    "resets",
    "vin-supply",
}
# Pointer properties detected during device tree walk
PTR_PROPS_IN_TREE = []
PTR_TO_PATH: dict[bytes, str] = {}
# Number of properties successfully substituted (cuz it's cool)
NUM_SUBSTITUTED = 0


# Helpers

def to_phandles(filepath: str) -> list[bytes]:
    phandles: list[bytes] = []
    with open(filepath, "rb") as f:
        while True:
            content = f.read(4) # A pointer is 32 bits
            if len(content) < 4:
                break
            phandles.append(content)
    return phandles

def handle_phandle(filepath: str):
    """Handle a phandle property on first tree walk"""
    phandle = to_phandles(filepath)
    if len(phandle) != 1:
        logging.warning(f"Node {filepath} has invalid phandle property")
    phandle = phandle[0]
    PTR_TO_PATH[phandle] = filepath

def substitute(filepath: str):
    """Substitute `filepath` with a directory.

    This directory will contain an `index` with phandles and the target filepath
    for each line. Order/duplicates are preserved

    Additionally, for each phandle in the original `filepath`, a symbolic link
    is created in the new directory with the name being the handle and the
    destination being the node with the phandle.
    """
    global NUM_SUBSTITUTED
    phandles = to_phandles(filepath)
    os.remove(filepath)
    os.mkdir(filepath)
    with open(f"{filepath}/index.txt", "w") as index:
        for phandle in phandles:
            link_name = f"{filepath}/{phandle.hex()}"
            index.write(f"{phandle.hex()}")
            if phandle in PTR_TO_PATH:
                NUM_SUBSTITUTED = NUM_SUBSTITUTED + 1
                target = PTR_TO_PATH[phandle]
                index.write(f"\t{target}")
                try:
                    os.symlink(target, link_name)
                except FileExistsError as e: # Duplicate phandles are expected
                    logging.debug(e)
            else:
                open(link_name, "w")
                logging.warning(
                    f"Phandle {phandle.hex()} in {filepath} cannot be mapped"
                )
            index.write(f"\n")


# Main routine

def main(base: None | str):
    """Modifies device tree located at `base` such that pointer properties are
    readable relative path based on `base`.

    Properties are deemed to contain pointers if their name matches a standard
    property that contains pointers. For a comprehensive list, see
    PTR_PROPERTIES.

    PTR_PROPERTIES
    * clock
    """
    # Resolve arguments
    if base is None:
        base = os.path.dirname(SCRIPTHOME)

    # Walk device tree
    logging.info("Walking device tree")
    for dirpath, _, filenames in os.walk(base):
        logging.debug(f"Walking {dirpath}")
        for filename in filenames:
            filepath = f"{dirpath}/{filename}"

            if filename == "phandle":
                handle_phandle(filepath)
            elif filename in PTR_PROPERTIES:
                PTR_PROPS_IN_TREE.append(filepath)

    # Substitute pointers with paths
    logging.info("Substituting properties with symlinks")
    for filepath in PTR_PROPS_IN_TREE:
        logging.debug(f"Substituting {filepath}")
        try:
            substitute(filepath)
        except Exception as e:
            logging.error(f"{e}; Failed to substitute {filepath}, continuing")
    logging.info(f"Successfully substituted {NUM_SUBSTITUTED} properties")


if __name__ == "__main__":
    fire.Fire(main)
