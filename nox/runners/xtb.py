import pathlib
import shutil

from nox.parsers.xtb_json import parse_xtbout_text


class XTBNotAvailable(RuntimeError):
    pass


def run_xtb(smiles: str | None = None, infile: str | None = None) -> dict:
    """
    Minimal placeholder: expects an existing input file and a neighboring xtbout.json.
    In real flow we'll invoke xtb; for CI we just parse the JSON so tests stay green.
    """
    if shutil.which("xtb") is None:
        raise XTBNotAvailable("xtb binary not found on PATH")
    if not infile and not smiles:
        raise ValueError("Provide infile or smiles")

    path = pathlib.Path(infile or "")
    if not path.exists():
        raise FileNotFoundError(f"input file not found: {path}")

    out_json = path.with_name("xtbout.json")
    text = out_json.read_text(encoding="utf-8")
    return parse_xtbout_text(text)
