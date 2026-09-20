"""Portable Tripo V3 client. Secrets stay in TRIPO_API_KEY, never in reports."""
import argparse
import hashlib
import json
import mimetypes
import os
from pathlib import Path
import time
import urllib.request
import urllib.error
import uuid


class Tripo:
    def __init__(self, region="cn"):
        self.base = "https://openapi.tripo3d." + ("com" if region == "cn" else "ai") + "/v3"
        self.key = os.environ.get("TRIPO_API_KEY", "").strip()
        if not self.key:
            raise ValueError("Set TRIPO_API_KEY in the process environment")

    def request(self, route, data=None, content_type="application/json"):
        if isinstance(data, dict):
            data = json.dumps(data).encode()
        req = urllib.request.Request(self.base + route, data=data, headers={
            "Authorization": "Bearer " + self.key, "Content-Type": content_type})
        try:
            with urllib.request.urlopen(req, timeout=180) as response:
                result = json.load(response)
        except urllib.error.HTTPError as error:
            # Never print response bodies, request headers, or signed URLs.
            raise RuntimeError(f"Tripo HTTP {error.code} on {route.split('?')[0]}; no automatic resubmission") from None
        except (urllib.error.URLError, TimeoutError):
            raise RuntimeError('Tripo network failure; retain the journal and do not resubmit paid tasks') from None
        if result.get("code") != 0:
            raise RuntimeError(f"Tripo API code {result.get('code')}; no automatic resubmission")
        return result["data"]

    def upload(self, path):
        path = Path(path)
        boundary = "h2s" + uuid.uuid4().hex
        mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        body = (f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="input{path.suffix}"\r\nContent-Type: {mime}\r\n\r\n').encode()
        body += path.read_bytes() + f"\r\n--{boundary}--\r\n".encode()
        return self.request("/files", body, "multipart/form-data; boundary=" + boundary)["file_token"]


def save(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    temp.replace(path)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--region", choices=["cn", "global"], default="cn")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("balance")
    gen = sub.add_parser("generate")
    gen.add_argument("--image", type=Path, required=True)
    gen.add_argument("--job", type=Path, required=True)
    gen.add_argument("--model", default="v3.1-20260211")
    gen.add_argument("--allow-paid-generation", action="store_true", required=True)
    wait = sub.add_parser("fetch")
    wait.add_argument("--job", type=Path, required=True)
    wait.add_argument("--output", type=Path, required=True)
    wait.add_argument("--wait-seconds", type=int, default=0)
    a = p.parse_args()
    api = Tripo(a.region)
    if a.command == "balance":
        print(json.dumps(api.request("/account/balance")))
    elif a.command == "generate":
        if a.job.exists():
            raise ValueError("Job file already exists; fetch it instead of paying twice")
        if a.image.suffix.lower() not in (".png", ".jpg", ".jpeg", ".webp") or a.image.stat().st_size > 20*1024*1024:
            raise ValueError("Use an image under 20 MB")
        balance = api.request("/account/balance")
        if balance.get("balance", 0) < 60:
            raise ValueError("Insufficient available credits for the documented 60-credit preset")
        token = api.upload(a.image)
        payload = dict(input=token, model=a.model, texture=True, pbr=True,
                       geometry_quality="detailed", texture_quality="detailed",
                       texture_alignment="original_image", orientation="align_image",
                       enable_image_autofix=False, model_seed=20260920)
        journal = dict(region=a.region, state="submitting", image_sha256=hashlib.sha256(a.image.read_bytes()).hexdigest(),
                       parameters={k:v for k,v in payload.items() if k != "input"}, balance_before=balance)
        # Persist before submitting: uncertain timeouts must not silently pay again.
        save(a.job, journal)
        result = api.request("/generation/image-to-model", payload)
        journal.update(task_id=result["task_id"], state="submitted")
        save(a.job, journal)
        print(json.dumps({"task_id": result["task_id"], "state":"submitted"}))
    else:
        journal = json.loads(a.job.read_text(encoding="utf-8"))
        if journal["region"] != a.region:
            raise ValueError("Region must match the original job")
        task_id = journal["task_id"]
        deadline = time.monotonic() + a.wait_seconds
        while True:
            task = api.request("/tasks/" + task_id)
            status = task.get("status")
            print(json.dumps({"status":status,"progress":task.get("progress")}), flush=True)
            journal.update(state=status, progress=task.get("progress"), credits_consumed=task.get("credits_consumed"))
            save(a.job, journal)
            if status == "success":
                a.output.mkdir(parents=True, exist_ok=True)
                files = []
                for name, url in task.get("output", {}).items():
                    if not isinstance(url, str) or not url.startswith("https://"):
                        continue
                    # Downloads use no API Authorization header.
                    from urllib.parse import urlsplit
                    ext = Path(urlsplit(url).path).suffix
                    if ext.lower() not in (".glb", ".png", ".jpg", ".jpeg", ".zip", ".obj", ".fbx", ".webp"):
                        continue
                    target = a.output / ("".join(c for c in name if c.isalnum() or c == "_") + ext)
                    try:
                        with urllib.request.urlopen(url, timeout=180) as response:
                            data = response.read()
                    except (urllib.error.URLError, TimeoutError):
                        raise RuntimeError('Output download failed; fetch the existing job again for a fresh URL') from None
                    temp = target.with_suffix(target.suffix + '.partial')
                    temp.write_bytes(data)
                    temp.replace(target)
                    files.append(dict(file=target.name, bytes=len(data), sha256=hashlib.sha256(data).hexdigest()))
                journal.update(files=files, output_fields=list(task.get("output", {})), balance_after=api.request("/account/balance"))
                save(a.job, journal)
                if not any(f['file'].endswith(('.glb', '.obj', '.fbx', '.zip')) for f in files):
                    raise RuntimeError('Success response contained no supported model download; inspect output field names')
                print(json.dumps({"files":files,"balance_after":journal["balance_after"]}))
                return
            if status in ("failed", "cancelled", "canceled", "banned", "expired"):
                raise RuntimeError("Generation ended: " + str(status))
            if time.monotonic() >= deadline:
                return
            time.sleep(min(10, max(0, deadline-time.monotonic())))


if __name__ == "__main__":
    main()
