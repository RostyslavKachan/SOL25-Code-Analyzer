import sys
import re
import argparse
import xml.etree.ElementTree as ET
from lark import Lark, Transformer, Tree, UnexpectedInput, UnexpectedCharacters, UnexpectedToken


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
                lexeme = match.group(0)
                
                
                # if token_type == "STRING":
                #     string_content = lexeme[1:-1] 
                #     try:
                #         unescaped_string = bytes(string_content, "utf-8").decode("unicode_escape")  
                #     except UnicodeDecodeError:
                #         sys.stderr.write(f"Error: Invalid escape sequence in string: {string_content}\n")
                #         sys.exit(21)

                #     print("string")
                #     escape_sequences = re.findall(r'\.', string_content)
                #     print(escape_sequences)
                #     allowed_escapes = ["\'", "\n", "\\"]
                #     for esc in escape_sequences:
                #         print("esc" + esc)
                #         if esc not in allowed_escapes:
                #             sys.stderr.write(f"Error: Invalid escape sequence {esc} in string.\n")
                #             sys.exit(21)
                            

                if token_type:  
                   tokens.append((token_type, lexeme))

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

GRAMMAR = r'''
    start: class_def+ COMMENT?
    
    class_def: "class" CLASS_ID ":" CLASS_ID "{" method_def* "}"
    
    method_def: METHOD_ID "[" "|" statement* "|" "]"

    statement: assignment 
             | instantiation_stmt
             | method_call_stmt

    assignment: ID ":=" expr "."

    instantiation_stmt: CLASS_ID "(" expr_list? ")" "."

    method_call_stmt: ID "." ID "(" expr_list? ")" "."

    expr: ID
        | INTEGER
        | STRING
        | instantiation_expr
        | method_call_expr
        | "(" expr ")"  -> group

    instantiation_expr: CLASS_ID "(" expr_list? ")" 
    method_call_expr: ID "." ID "(" expr_list? ")" 

    expr_list: expr ("," expr)*

    COMMENT: "\"" /[^"]*/ "\""

    ID: /[a-z_][a-zA-Z0-9_]*/
    CLASS_ID: /[A-Z][a-zA-Z0-9_]*/
    METHOD_ID: "run" | ID   // Allows `run` but also other method names

    INTEGER: /[0-9]+/
    STRING: /'[^']*'/

    %ignore /\s+/
    %ignore COMMENT
'''


parser = Lark(GRAMMAR,start = 'start',parser="lalr")

def parse_code(code):
    try:
        print("### DEBUG: Parsing starts ###")
        tree = parser.parse(code)
        print("### PARSING SUCCESS ###")
        print(tree.pretty())
        return tree
    except UnexpectedToken:
        sys.stderr.write("Error: Syntax error.\n")
        sys.exit(22)
    except UnexpectedCharacters:
        sys.stderr.write("Error: Syntax error.\n")
        sys.exit(22)
    except UnexpectedInput:
        sys.stderr.write("Error: Syntax error.\n")
        sys.exit(22)
    

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
        
        
    print(input_data)
    print("Input data above ---------------------------------------")
    tokens = tokenize(input_data)
    print()
    print(tokens)
    print("Tokens above ---------------------------------------")
    print()
    for token in tokens:
        print(token)
    
    parse_code(input_data)
      
if __name__ == "__main__":
    main()
    


