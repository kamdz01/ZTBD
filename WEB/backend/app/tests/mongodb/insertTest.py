import sys
import json

def main():
    if len(sys.argv) < 2:
        print("Proszę podać argument.")
        sys.exit(1)
    try:
        value = float(sys.argv[1])
    except ValueError:
        print("Podany argument nie jest liczbą.")
        sys.exit(1)
    
    result = value * 10
    json_line = json.dumps({f"time": result})
    print(json_line)

if __name__ == '__main__':
    main()