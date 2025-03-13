import sys
import json

def main():
    result = 50
    json_line = json.dumps({f"time": result})
    print(json_line)

if __name__ == '__main__':
    main()