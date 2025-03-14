import sys
import re
import argparse
import xml.etree.ElementTree as ET
from lark import Lark, Transformer, Tree, UnexpectedInput, UnexpectedCharacters, UnexpectedToken, LexError, Token
import xml.dom.minidom



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

class SOL25Transformer(Transformer):
    

    def __init__(self):
        global input_data
        super().__init__()
        self.root = ET.Element("program", language="SOL25")
        comment_text = extract_first_comment(input_data)
        if comment_text:
            self.root.set("description", comment_text)

    def program(self, classes):
        
        for cls in classes:
            self.root.append(cls)
        return self.root

    def class_def(self, args):
        
        class_name, parent_name, *methods = args
        class_elem = ET.Element("class", name=class_name, parent=parent_name)
        for method in methods:
            class_elem.append(method)
        return class_elem

    def method_def(self, args):
        
        # print("method_def DEBUG ->   ", args)
        # print()
        # print()
        if not args:
            raise ValueError("method_def not arguments!")

        method_tree = args.pop(0)  

        
        if isinstance(method_tree, Tree) and method_tree.data == "method_name":
            selector_tree = method_tree.children[0]
            if isinstance(selector_tree, Tree) and selector_tree.data == "method_selector":
                method_name = "".join(part for part in selector_tree.children)
            else:
                method_name = selector_tree.value  
        else:
            raise ValueError(f"Unknown sturcture method_name: {method_tree}")

        
        if args and isinstance(args[0], Tree) and args[0].data == "param_list":
            params = args.pop(0).children  
        else:
            params = []

        
        body = args if args else []

        
        method_elem = ET.Element("method", selector=method_name)
        block_elem = ET.Element("block", arity=str(len(params)))

        
        for i, param in enumerate(params, start=1):
            ET.SubElement(block_elem, "parameter", name=param, order=str(i))

        
        for stmt in body:
            if isinstance(stmt, ET.Element) and stmt.tag == "block":
                
                for sub_stmt in list(stmt):
                    block_elem.append(sub_stmt)
            else:
                block_elem.append(stmt)

        
        method_elem.append(block_elem)

        return method_elem






    def blockstat(self, statements):
        
        # print("blockstat DEBUG ->   ", statements)
        # print()
        # print()
        block_elem = ET.Element("block")  

        for order, stmt in enumerate(statements, start=1):
            if isinstance(stmt, ET.Element) and stmt.tag == "assign":
                stmt.set("order", str(order))  
            elif isinstance(stmt, Tree):  
                stmt = self.transform(stmt) 
                
            block_elem.append(stmt)

        return block_elem 






    def expr_tail(self, args):
        """Обробка виразів, які мають селектори (наприклад, obj from: 10 a: 5 b: 3)."""

        selectors = []
        values = []
        newArgs = []

        if not args:
            return 

        # Якщо перший елемент - tuple, розгортаємо його
        while len(args) == 1 and isinstance(args[0], tuple):
            args = args[0]

        for arg in args:
            if isinstance(arg, tuple) and len(arg) == 2:
                # Якщо аргумент є tuple (селектор, значення), додаємо окремо
                selectors.extend(arg[0])  # Додаємо всі селектори
                values.extend(arg[1])  # Додаємо всі значення
            else:
                newArgs.append(arg)

        # Обробка залишкових аргументів (які не є tuple)
        for arg in newArgs:
            if isinstance(arg, Token) and arg.type == "ID_COLON":
                selectors.append(arg.value)  # Додаємо `from:`, `a:`, `b:`
            elif isinstance(arg, Token) and arg.type == "VALID_ID":
                selectors.append(arg.value)  # Додаємо `from:`, `a:`, `b:`
            elif isinstance(arg, ET.Element):
                values.append(arg)  # Додаємо аргументи (наприклад, `1`, `2`, `4`)
            elif isinstance(arg, str):
                # Якщо це випадково став просто текстовий рядок, додаємо як селектор
                selectors.append(arg)
            elif isinstance(arg, list):
                # Якщо випадково аргумент є списком, розгортаємо його
                for sub_arg in arg:
                    if isinstance(sub_arg, Token) and sub_arg.type == "ID_COLON":
                        selectors.append(sub_arg.value)
                    elif isinstance(sub_arg, ET.Element):
                        values.append(sub_arg)
                    elif isinstance(sub_arg, Tree):
                        values.append(self.transform(sub_arg))
                    elif isinstance(sub_arg, str):
                        selectors.append(sub_arg)

        # Формуємо фінальний селекторний рядок
        selector = "".join(selectors) if selectors else None

        return selector, values  # Повертаємо коректний селектор + значення






    
    def expr(self, args):
        # print("expr DEBUG ->   ", args)

        if len(args) == 2 and args[1] is None:
            base = args[0]
            tail = None
        else:
            base, tail = args

        # Перетворення base у XML-структуру
        if isinstance(base, str):
            if base[0].isupper():
                base = ET.Element("literal", {"class": "class", "value": base})
            else:
                base = ET.Element("var", name=base)

        elif isinstance(base, Tree):
            if base.data == "block":
                base = self.process_block(base)  # Використовуємо process_block для блоків
            else:
                transformed_base = self.transform(base)  # Перетворюємо дерево у XML
                
                if isinstance(transformed_base, ET.Element):
                    base = transformed_base  # Тільки якщо це XML, оновлюємо base
                else:
                    print(f"⚠️ ПОМИЛКА: Неможливо перетворити base у XML -> {base}")
                    base = None  # Не додаємо його у XML

        if tail:
            # Перевіряємо, чи tail є кортежем (селектор + значення)
            if isinstance(tail, tuple):
                selector, values = tail
            else:
                selector = tail
                values = []

            send_elem = ET.Element("send", selector=str(selector))
            expr_elem = ET.SubElement(send_elem, "expr")

            # Додаємо base у expr_elem тільки якщо це коректний XML-елемент
            if isinstance(base, ET.Element):
                expr_elem.append(base)
            elif base is not None:
                print(f"⚠️ ПОМИЛКА: Неможливо додати base у XML -> {base}")

            # Обробляємо аргументи
            for i, value in enumerate(values, start=1):
                arg_elem = ET.SubElement(send_elem, "arg", order=str(i))
                expr_inner = ET.SubElement(arg_elem, "expr")

                if isinstance(value, Tree):
                    if value.data == "block":  
                        transformed_value = self.process_block(value)
                    else:
                        transformed_value = self.transform(value)

                    if isinstance(transformed_value, ET.Element):
                        expr_inner.append(transformed_value)
                    else:
                        print(f"⚠️ ПОМИЛКА: Неможливо перетворити Tree у XML -> {value}")

                elif isinstance(value, ET.Element):
                    expr_inner.append(value)  # Якщо це вже XML, додаємо напряму

                elif isinstance(value, str):
                    literal_elem = ET.Element("literal", {"class": "String", "value": value})
                    expr_inner.append(literal_elem)

                else:
                    print(f"⚠️ ПОМИЛКА: Невідомий тип аргументу у expr -> {type(value)}")

            return send_elem

        return base  # Якщо немає tail, повертаємо сам base





    def process_block(self, block_tree):
        """Обробка блоку коду"""
        if not isinstance(block_tree, Tree) or block_tree.data != "block":
            raise ValueError(f"Очікував Tree(block), отримав {type(block_tree)}: {block_tree}")

        children = block_tree.children

        # Якщо є список параметрів
        if len(children) >= 2 and isinstance(children[0], Tree) and children[0].data == "param_list":
            param_list = children[0]
            block_body = children[1] if len(children) > 1 and isinstance(children[1], ET.Element) else None

            param_count = len(param_list.children)
            block_elem = ET.Element("block", arity=str(param_count))

            for i, param in enumerate(param_list.children, start=1):
                ET.SubElement(block_elem, "parameter", name=param, order=str(i))

            # Якщо блок тіла існує, **переконуємось, що не обгортаємо його вдруге**
            if block_body is not None and block_body.tag == "block":
                for sub_elem in list(block_body):
                    block_elem.append(sub_elem)  # Додаємо лише внутрішні елементи
            elif block_body is not None:
                block_elem.append(block_body)

        else:
            block_elem = ET.Element("block", arity="0")

        return block_elem









    def assign(self, args):
        
        var_name, value = args
        assign_elem = ET.Element("assign")

        ET.SubElement(assign_elem, "var", name=var_name)
        expr_elem = ET.SubElement(assign_elem, "expr")

        
        if isinstance(value, Tree) and value.data == "block":
            block_elem = self.process_block(value) 
            expr_elem.append(block_elem)
        
        elif isinstance(value, ET.Element):
            expr_elem.append(value)  

        else:
            expr_elem.text = str(value) 

        return assign_elem  




    def expr_base(self, args):
        # print("expr_base DEBUG ->   ", args)
        # print()
        # print()
        base = args[0]  
        
        if isinstance(base, Token):  
            if base.type == "SIGNED_INT":
                return ET.Element("literal", attrib={"class": "Integer", "value": base.value})
            elif base.type == "STR":
                return ET.Element("literal", attrib={"class": "String", "value": base.value.strip("'")})
            elif base.type == "ID":
                if base.value in {"nil", "true", "false"}:
                 return ET.Element("literal", {"class": base.value.capitalize(), "value": base.value})
                return ET.Element("var", name=base.value)
            elif base.type == "CID":
                return ET.Element("literal", attrib={"class": "class", "value": base.value})
        
        return base  

    def expr_sel(self, args):
        """Обробка селекторних виразів (наприклад, obj compute: 3 and: 2 and: 5)."""

        selectors = []
        values = []

        for arg in args:
            if isinstance(arg, Token) and arg.type == "ID_COLON":
                selectors.append(arg.value)  # Додаємо селектор (наприклад, `and:`)
            elif isinstance(arg, ET.Element):
                values.append(arg)  # Додаємо значення (наприклад, `5`)
            elif isinstance(arg, tuple) and len(arg) == 2:
                # Рекурсивний випадок: `arg` вже містить селектори та значення з попереднього рівня
                prev_selectors, prev_values = arg
                selectors.extend(prev_selectors)  # Додаємо попередні селектори
                values.extend(prev_values)  # Додаємо попередні значення
            elif isinstance(arg, Tree) and arg.data == "block":
                # Обробка блоку (викликаємо self.transform, щоб отримати XML)
                block_xml = self.transform(arg)
                values.append(block_xml)  # Додаємо як значення
            else:
                print(f"⚠️ ПОМИЛКА: Невідомий аргумент у expr_sel -> {arg}")

        return selectors, values  # Повертаємо всі селектори і всі значення у вигляді двох списків






    def SIGNED_INT(self, token):
        
        #return ET.Element("literal", attrib={"class": "Integer"}, value=str(token))
        return token

    def STR(self, token):
        
        #return ET.Element("literal", attrib={"class": "String"}, value=token.strip("'"))
        return token
    def ID(self, token):
        
        # if token in {"nil", "true", "false"}:
        #     return ET.Element("literal", {"class": token.capitalize(), "value": token})
        # return ET.Element("var", name=token)
        return token


    def CID(self, token):
        
        return token

    def ID_COLON(self, token):
        
        return token  

    def COLON_ID(self, token):
        
        return token[1:]  
    
    def EXP_KEYWORD(self, token):
        
        return token
    def KEYWORD(self, token):
        
        return token
    def VALID_ID(self, token):
        
        return token
    def METHOD_COLON(self, token):
        
        return token


    def transform_to_xml(self):
        
        raw_xml = ET.tostring(self.root, encoding="utf-8")  
        parsed_xml = xml.dom.minidom.parseString(raw_xml) 
        formatted_xml = parsed_xml.toprettyxml(indent="  ")  
        # print("----------------------------------------------------------------")
        # print(formatted_xml)
        # print("----------------------------------------------------------------")
        
        formatted_xml = formatted_xml.replace('<?xml version="1.0" ?>', '<?xml version="1.0" encoding="UTF-8"?>')

        return formatted_xml

def print_help():
    print("""Code Analyzer in SOL25 (parse.py)
The filter-type script (parse.py in Python 3.11) reads source code in SOL25 from standard input, 
checks the lexical, syntactic, and static semantic correctness of the code, and outputs the XML representation 
of the abstract syntax tree of the program.""")


def extract_first_comment(code):
    
    in_string = False
    escape = False
    comment_start = None

    for i, char in enumerate(code):
        if char == "'" and not escape: 
            in_string = not in_string  
        elif char == '"' and not in_string: 
            if comment_start is None:
                comment_start = i + 1  
            else:
                return code[comment_start:i]  

        escape = (char == "\\" and not escape)  

    return None  





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
            # print("\n Error: Invalid token detected!")
            # print(f"   Remaining code: {code[:20]}")  
            # print(f"   Last extracted tokens: {tokens[-5:]}")  
            sys.stderr.write(f"Error: Invalid token near '{code[:20]}'\n")
            # print("21 Error")
            sys.exit(21)

    return tokens

GRAMMAR = r'''
program: class_def+

class_def: "class" CID ":" CID "{" method_def* "}"

method_def: method_name "[" param_list* "|" blockstat* "]"

method_name: VALID_ID | method_selector
method_selector: ID_COLON+

param_list: (COLON_ID)*

blockstat: (assign ".")*
assign: VALID_ID ":=" expr




expr: expr_base expr_tail

expr_tail: expr_sel?      
         | VALID_ID      

expr_sel: ID_COLON expr_base expr_sel*


expr_base: SIGNED_INT
         | STR
         | EXP_KEYWORD    
         | ID             
         | CID            
         | "(" expr ")"   
         | block          

block: "[" param_list "|" blockstat "]"


EXP_KEYWORD : "self" | "super" | "nil" | "true" | "false"


KEYWORD: "class" | "self" | "super" | "nil" | "true" | "false"


VALID_ID: /(?!(class|self|super|nil|true|false)\b)[a-z_][a-zA-Z0-9_]*/


CID: /[A-Z][a-zA-Z0-9_]*/


ID: /[a-z_][a-zA-Z0-9_]*/

ID_COLON.2: /[a-z_][a-zA-Z0-9_]*:/
//ID_COLON: /(?!(class|self|super|nil|true|false)\b)[a-z_][a-zA-Z0-9_]*:/

//METHOD_COLON: /[a-z_][a-zA-Z0-9_]*:/


COLON_ID: /:(?!(class|self|super|nil|true|false)\b)[a-z_][a-zA-Z0-9_]*/

STR: /'([^'\\]|\\.)*'/
%import common.SIGNED_INT

%ignore /[ \t\n\f\r]+/
%ignore /"[^"]*"/
'''





parser = Lark(GRAMMAR,start = 'program',parser="lalr")

def parse_code(code):
    try:
        # print("### DEBUG: Parsing starts ###")
        tree = parser.parse(code)
        # print("### PARSING SUCCESS ###")
        # print(tree.pretty())
        return tree
    except UnexpectedToken as e:
        # print(f"Syntax error at line {e.line}, column {e.column}.")
        # print(f"Got token: {e.token!r}. Expected one of: {e.expected}")
        
        context_str = e.get_context(code, span=40)
        sys.stderr.write("Error: Syntax error.\n")
        sys.exit(22)
    except UnexpectedCharacters:
        sys.stderr.write("Error: Lexical error.\n")
        sys.exit(21)
    except UnexpectedInput as e:
        # print(f"Syntax error at line {e.line}, column {e.column}.")
        # print(f"Got token: {e.token!r}. Expected one of: {e.expected}")
        
        context_str = e.get_context(code, span=40)
        sys.stderr.write("Error: Syntax error.\n")
        sys.exit(22)
    # except LexError:
    #     sys.stderr.write("Error: Syntax error.\n")
    #     sys.exit(22)
 

input_data = ""
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
        
    global input_data
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
    
    else:
        input_data = sys.stdin.read()
        
        
    
    tokens = tokenize(input_data)
    # print("--------------------------------",type(tokens))
    # for token in tokens:
    #     print(token)
    # print("--------------------------------",type(input_data))
    parse_tree = parse_code(input_data)
    transformer = SOL25Transformer()
    xml_tree = transformer.transform(parse_tree)
    xml_output = transformer.transform_to_xml()
    print(xml_output)
    sys.exit(0)
      
if __name__ == "__main__":
    main()
    