from pathlib import Path


def test_start_stop_scripts_exist_for_linux_and_mac() -> None:
    root = Path(__file__).resolve().parents[2]
    expected = [
        "scripts/start-linux.sh",
        "scripts/stop-linux.sh",
        "scripts/start-mac.sh",
        "scripts/stop-mac.sh",
    ]
    for relpath in expected:
        assert (root / relpath).exists(), f"Missing script: {relpath}"


def test_start_scripts_use_docker_compose() -> None:
    root = Path(__file__).resolve().parents[2]
    # Shared script contains the actual docker compose command;
    # platform wrappers delegate to it.
    content = (root / "scripts/start.sh").read_text(encoding="utf-8")
    assert "docker compose up -d --build" in content
