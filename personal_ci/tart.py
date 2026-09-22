"""Run one GitHub job inside one owned Tart clone."""

import os
import subprocess
import time
from pathlib import Path


class TartProvider:
    def __init__(self, config):
        self.config = config
        self.bin = str(config.tart_bin)
        self.environment = os.environ.copy()
        self.environment["PATH"] = "/opt/homebrew/bin:" + self.environment.get("PATH", "")

    def command(self, *args, input_text=None, timeout=120):
        return subprocess.run([self.bin, *args], input=input_text, text=True,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              timeout=timeout, check=True, env=self.environment)

    def available_images(self):
        return set(self.command("list", "--source", "local", "--quiet").stdout.splitlines())

    def exists(self, name):
        return name in self.available_images()

    def _ready(self, name, process):
        deadline = time.monotonic() + 360
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError("Tart VM exited before guest became ready")
            try:
                self.command("exec", name, "/usr/bin/true", timeout=8)
                return
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
                time.sleep(3)
        raise TimeoutError("Tart guest did not become ready within 360 seconds")

    def run_job(self, job, name, jit_factory, log_path):
        lane = self.config.lanes[job.lane]
        if lane.base_image not in self.available_images():
            raise RuntimeError("missing prepared Tart image: " + lane.base_image)
        cloned = False
        process = None
        log_path = Path(log_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a") as log:
            try:
                self.command("clone", lane.base_image, name, timeout=300)
                cloned = True
                self.command("set", name, "--cpu", str(self.config.cpu_per_vm),
                             "--memory", str(self.config.memory_mb_per_vm))
                process = subprocess.Popen([self.bin, "run", "--no-graphics", "--no-clipboard",
                                            "--net-softnet", name],
                                           stdin=subprocess.DEVNULL, stdout=log,
                                           stderr=subprocess.STDOUT, env=self.environment)
                self._ready(name, process)
                jit = jit_factory(job, name)
                # Tart -i forwards stdin to the guest. The JIT config is never
                # placed in a command-line argument or in a base image.
                guest_script = 'IFS= read -r config; cd "$1"; exec ./run.sh --jitconfig "$config"'
                result = subprocess.run([self.bin, "exec", "-i", name, "/bin/bash", "-lc",
                                         guest_script, "runner", lane.runner_dir],
                                        input=jit + "\n", text=True, stdout=log,
                                        stderr=subprocess.STDOUT, env=self.environment)
                if result.returncode:
                    raise RuntimeError("guest runner exited with status {}".format(result.returncode))
            finally:
                if process is not None:
                    process.terminate()
                    try:
                        process.wait(timeout=20)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=5)
                if cloned:
                    # An owned clone only. Tart refuses deletion of a live VM.
                    self.command("delete", name, timeout=120)
