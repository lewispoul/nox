import requests

BASE = "http://127.0.0.1:8080"
TOKEN = "Xmf7vYpHipwaR3TKyvVC"  # même valeur que dans le service
H = {"Authorization": f"Bearer {TOKEN}"}


def health():
    print(requests.get(f"{BASE}/health").json())


def put(local, remote):
    with open(local, "rb") as f:
        r = requests.post(f"{BASE}/put", headers=H, files={"f": f}, params={"path": remote})
    print(r.json())


def run_py(code, filename="snippet.py", args=None):
    d = {"code": code, "filename": filename, "args": args or []}
    r = requests.post(f"{BASE}/run_py", headers=H, json=d)
    print(r.json())


def run_sh(*cmd):
    r = requests.post(f"{BASE}/run_sh", headers=H, json={"cmd": list(cmd)})
    print(r.json())


if __name__ == "__main__":
    # exemples
    health()
    put("/tmp/hello.py", "tests/hello.py")
    run_py('print("Nox OK")', "test.py")
    run_sh("ls", "-la", ".")
