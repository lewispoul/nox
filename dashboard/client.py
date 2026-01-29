# dashboard/client.py
import requests


class NoxClient:
    def __init__(self, base_url: str, token: str, timeout: float = 15.0):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        if token:  # Seulement si token fourni
            self.session.headers.update({"Authorization": f"Bearer {token}"})
        self.timeout = timeout

    def health(self):
        r = self.session.get(f"{self.base_url}/health", timeout=self.timeout)
        r.raise_for_status()
        return r.json(), r.headers

    def put(self, dest_path: str, local_path: str):
        with open(local_path, "rb") as f:
            files = {"f": f}
            r = self.session.post(
                f"{self.base_url}/put",
                params={"path": dest_path},
                files=files,
                timeout=self.timeout,
            )
        r.raise_for_status()
        return r.json(), r.headers

    def run_py(self, code: str, filename: str = "run.py"):
        r = self.session.post(
            f"{self.base_url}/run_py",
            json={"code": code, "filename": filename},
            timeout=self.timeout,
        )
        r.raise_for_status()
        return r.json(), r.headers

    def run_sh(self, cmd: str):
        r = self.session.post(f"{self.base_url}/run_sh", json={"cmd": cmd}, timeout=self.timeout)
        r.raise_for_status()
        return r.json(), r.headers

    def list_files(self, path: str = "", recursive: bool = False):
        params = {"path": path, "recursive": recursive}
        r = self.session.get(f"{self.base_url}/list", params=params, timeout=self.timeout)
        r.raise_for_status()
        return r.json(), r.headers

    def cat_file(self, path: str):
        r = self.session.get(f"{self.base_url}/cat", params={"path": path}, timeout=self.timeout)
        r.raise_for_status()
        return r.json(), r.headers

    def delete_file(self, path: str):
        r = self.session.delete(
            f"{self.base_url}/delete", params={"path": path}, timeout=self.timeout
        )
        r.raise_for_status()
        return r.json(), r.headers

    def get_metrics(self):
        r = self.session.get(f"{self.base_url}/metrics", timeout=self.timeout)
        r.raise_for_status()
        return r.text, r.headers
