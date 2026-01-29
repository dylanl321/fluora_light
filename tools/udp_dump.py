import argparse
import socket


def main() -> int:
    parser = argparse.ArgumentParser(description="Dump UDP packets as hex.")
    parser.add_argument("--host", default="0.0.0.0", help="Bind host (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=6767, help="Bind port (default: 6767)")
    args = parser.parse_args()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((args.host, args.port))
    print(f"Listening on udp://{args.host}:{args.port}")

    while True:
        data, addr = sock.recvfrom(4096)
        print(f"{addr[0]}:{addr[1]}  {data.hex()}")


if __name__ == "__main__":
    raise SystemExit(main())
