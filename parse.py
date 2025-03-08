import sys
import re
import argparse
import xml.etree.ElementTree as ET
from lark import Lark, Transformer, Tree, UnexpectedInput, UnexpectedCharacters, UnexpectedToken, LexError


TOKEN_TYPES = [
    (r"\b[a-z][a-zA-Z0-9]*:\s*", "SELECTOR"),
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
    
    (r":[a-z][_a-zA-Z0-9]*", "PARAMETR"),
    (r"\b[A-Z][a-zA-Z0-9]*\b", "CLASS_ID"),
    (r"[_a-z][_a-zA-Z0-9]*", "ID"), 
    (r"[+-]?\d+", "INTEGER"), 
    (r"'(?:\\['n\\]|[^'\\\n])*'", "STRING"),
    (r"\(", "L_ROUND"), 
    (r"\)", "R_ROUND"),   
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
program: class_def+

class_def: "class" CID ":" CID "{" method_def* "}"

method_def: method_name "[" param_list "|" blockstat "]"

method_name: VALID_ID | method_selector
method_selector: ID_COLON+

param_list: (COLON_ID)*

blockstat: (VALID_ID ":=" expr ".")*

// ========= ГОЛОВНЕ: вираз з опціональним хвостом:
expr: expr_base expr_tail

expr_tail: VALID_ID      // унарний селектор (наприклад, foo)
         | expr_sel      // keyword-форма (foo: expr bar: expr ...)

expr_sel: (ID_COLON expr_base expr_sel)?

// базовий вираз
expr_base: SIGNED_INT
         | STR
         | EXP_KEYWORD    // self, super, nil, true, false
         | ID             // звичайний ідентифікатор
         | CID            // ім'я класу
         | "(" expr ")"   // дужки
         | block          // блок

block: "[" param_list "|" blockstat "]"

// Ключові слова, які хочемо дозволити окремо від IDENT
EXP_KEYWORD : "self" | "super" | "nil" | "true" | "false"

// "class" та інші – заборонені як VALID_ID, але сама лексема існує
KEYWORD: "class" | "self" | "super" | "nil" | "true" | "false"

// Звичайний ідентифікатор (не збігається з ключовими словами)
VALID_ID: /(?!(class|self|super|nil|true|false)\b)[a-z_][a-zA-Z0-9_]*/

// Class ID
CID: /[A-Z][a-zA-Z0-9_]*/

// Звичайний ідентифікатор
ID: /[a-z_][a-zA-Z0-9_]*/

// `foo:` (keyword-селектор)
ID_COLON: /(?!(class|self|super|nil|true|false)\b)[a-z_][a-zA-Z0-9_]*:/

// `:foo` (параметр)
COLON_ID: /:(?!(class|self|super|nil|true|false)\b)[a-z_][a-zA-Z0-9_]*/

STR: /'([^'\\]|\\.)*'/
%import common.SIGNED_INT

%ignore /[ \t\n\f\r]+/
%ignore /"[^"]*"/
'''





parser = Lark(GRAMMAR,start = 'program',parser="lalr")

def parse_code(code):
    try:
        print("### DEBUG: Parsing starts ###")
        tree = parser.parse(code)
        print("### PARSING SUCCESS ###")
        print(tree.pretty())
        return tree
    except UnexpectedToken as e:
        print(f"Syntax error at line {e.line}, column {e.column}.")
        print(f"Got token: {e.token!r}. Expected one of: {e.expected}")
        # If you want to see some code context around the error, use:
        context_str = e.get_context(code, span=40)
        sys.stderr.write("Error: Syntax error.\n")
        sys.exit(22)
    # except UnexpectedCharacters:
    #     sys.stderr.write("Error: Syntax error.\n")
    #     sys.exit(22)
    except UnexpectedInput as e:
        print(f"Syntax error at line {e.line}, column {e.column}.")
        print(f"Got token: {e.token!r}. Expected one of: {e.expected}")
        # If you want to see some code context around the error, use:
        context_str = e.get_context(code, span=40)
        sys.stderr.write("Error: Syntax error.\n")
        sys.exit(22)
    # except LexError:
    #     sys.stderr.write("Error: Syntax error.\n")
    #     sys.exit(22)
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
    sys.exit(0)
      
if __name__ == "__main__":
    main()
    