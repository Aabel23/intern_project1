"""Operator CLI at the factory station: python -m server.src.factory_register --serial ... (contracts v2 D1)."""
import sys
from server.src.devices import main

if __name__ == '__main__':
    sys.exit(main())
