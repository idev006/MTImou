from __future__ import annotations

from mtimou.config import load_config_from_env
from mtimou.p2p_adapter import PlaceholderDhP2PClient
from mtimou.runner import run_stream_probe


def main() -> None:
    config = load_config_from_env()
    run_stream_probe(config, client_factory=PlaceholderDhP2PClient)


if __name__ == "__main__":
    main()

