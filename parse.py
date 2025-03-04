import sys
import re
import argparse
import xml.etree.ElementTree as ET
#from lark import Lark, Transformer, Tree


TOKEN_TYPES = [
    (r"class", "KEY_CLASS"),
    (r"self", "KEY_SELF"),
    (r"super", "KEY_SUPER"),
    (r"nil", "KEY_NIL"),
    (r"true", "KEY_TRUE"),
    (r"false", "KEY_FALSE"),
    (r"\bObject\b", "OBJECT_CLASS"),
    (r"\bNil\b", "NIL_CLASS"),
    (r"\bTrue\b", "TRUE_CLASS"),
    (r"\bFalse\b", "FALSE_CLASS"),
    (r"\bInteger\b", "INTEGER_CLASS"),
    (r"\bString\b", "STRING_CLASS"),
    (r"\bBlock\b", "BLOCK_CLASS"),
    (r"\b[a-z][a-zA-Z0-9]*:\s*", "SELECTOR"),
    (r"\b[A-Z][a-zA-Z0-9]*\b", "CLASS_ID"),
    (r"[_a-z][_a-zA-Z0-9]*", "ID"), 
    (r"[+-]?\d+", "INTEGER"), 
    (r"'(?:\\['n\\]|[^'\\\n])*'", "STRING"),  
    (r"\{", "L_CURLY"),   
    (r"\}", "R_CURLY"),   
    (r"\[", "L_BRACKET"), 
    (r"\]", "R_BRACKET"), 
    (r"\|", "PIPE"),  
    (r":=", "ASSIGN"),  
    (r":", "COLON"), 
    (r"\.", "DOT"),  
    (r"\s+", None),  
    (r"\".*?\"", None)  
]



def print_help():
    print("""Code Analyzer in SOL25 (parse.py)
The filter-type script (parse.py in Python 3.11) reads source code in SOL25 from standard input, 
checks the lexical, syntactic, and static semantic correctness of the code, and outputs the XML representation 
of the abstract syntax tree of the program.""")



def tokenize(code):
    tokens = []
    while code:
        match = None

        
        if code.startswith('"'):
            end_index = code.find('"', 1)  
            if end_index == -1:
                sys.stderr.write("Error: Unclosed comment in source code.\n")
                sys.exit(21)

            
            code = code[end_index + 1:]
            continue  

        
        for pattern, token_type in TOKEN_TYPES:
            regex = re.compile(pattern)
            match = regex.match(code)

            if match:
               
                if token_type == "STRING":
                    string_value = match.group(0)

                    
                    if "\n" in string_value:
                        sys.stderr.write(f"Error: String contains a new line, which is not allowed.\n")
                        sys.exit(21)

                if token_type:  
                    tokens.append((token_type, match.group(0)))

               
                code = code[match.end():]
                break  

        
        if not match:
            print("\n Error: Invalid token detected!")
            print(f"   Remaining code: {code[:20]}")  
            print(f"   Last extracted tokens: {tokens[-5:]}")  
            sys.stderr.write(f"Error: Invalid token near '{code[:20]}'\n")
            print("21 Error")
            sys.exit(21)

    return tokens




def main():
    
    parser = argparse.ArgumentParser(add_help=False, allow_abbrev=False)
    parser.add_argument("--help", action="store_true", help="Show help message and exit")
    parser.add_argument("-h", action="store_true", help="Show help message and exit")
    parser.add_argument("--source", type=str, help="Path to input file (default: stdin)")

    args, unknown_args = parser.parse_known_args()
    
    
    if unknown_args:
        sys.stderr.write(f"Error: Unknown parameter(s): {' '.join(unknown_args)}\n")
        sys.exit(10) 
        
    
    help_count = sys.argv.count("--help") + sys.argv.count("-h")

    if help_count > 1:
        sys.stderr.write("Error: --help cannot be combined with itself or -h\n")
        sys.exit(10)

    if args.help or args.h:
        if args.source:
            sys.stderr.write("Error: --help cannot be combined with other parameters\n")
            sys.exit(10)
        print_help()
        sys.exit(0)

    # if not args.source:
    #     sys.stderr.write("Error: Missing required parameter\n")
    #     sys.exit(10)
        
    input_data = ""
    if args.source:
        try:
            with open(args.source, 'r', encoding='utf-8') as file:
                input_data = file.read()
        except FileNotFoundError:
            sys.stderr.write(f"Error: File '{args.source}' not found.\n")
            sys.exit(11)
        except PermissionError:
            sys.stderr.write(f"Error: No permission to read file '{args.source}'.\n")
            sys.exit(11)
    # POTIM dorobyty
    else:
        input_data = sys.stdin.read()
        
        

    tokens = tokenize(input_data)
    for token in tokens:
        print(token)
    
if __name__ == "__main__":
    main()