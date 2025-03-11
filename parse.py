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
    """Трансформує parse_tree у AST (XML)"""

    def __init__(self):
        global input_data
        super().__init__()
        self.root = ET.Element("program", language="SOL25")
        comment_text = extract_first_comment(input_data)
        if comment_text:
            self.root.set("description", comment_text)

    def program(self, classes):
        """Обробляє програму (список класів)"""
        for cls in classes:
            self.root.append(cls)
        return self.root

    def class_def(self, args):
        """Обробка класу"""
        class_name, parent_name, *methods = args
        class_elem = ET.Element("class", name=class_name, parent=parent_name)
        for method in methods:
            class_elem.append(method)
        return class_elem

    def method_def(self, args):
        """Обробка методу SOL25"""
        # print("method_def DEBUG ->   ", args)
        # print()
        # print()
        if not args:
            raise ValueError("method_def отримав порожні аргументи!")

        method_tree = args.pop(0)  # Перший елемент - це ім'я методу

        # Отримуємо ім'я методу або селектор
        if isinstance(method_tree, Tree) and method_tree.data == "method_name":
            selector_tree = method_tree.children[0]
            if isinstance(selector_tree, Tree) and selector_tree.data == "method_selector":
                method_name = "".join(part for part in selector_tree.children)
            else:
                method_name = selector_tree.value  # Простий селектор (наприклад, run)
        else:
            raise ValueError(f"Невідома структура method_name: {method_tree}")

        # Обробка параметрів (якщо вони є)
        if args and isinstance(args[0], Tree) and args[0].data == "param_list":
            params = args.pop(0).children  # Отримуємо список параметрів
        else:
            params = []

        # Обробка тіла методу (якщо воно є)
        body = args if args else []

        # XML структура
        method_elem = ET.Element("method", selector=method_name)
        block_elem = ET.Element("block", arity=str(len(params)))

        # Додаємо параметри
        for i, param in enumerate(params, start=1):
            ET.SubElement(block_elem, "parameter", name=param, order=str(i))

        # ✅ **Головна зміна тут:**
        for stmt in body:
            if isinstance(stmt, ET.Element) and stmt.tag == "block":
                # Якщо stmt — це вже блок, додаємо його вміст напряму, не створюючи нового <block>
                for sub_stmt in list(stmt):
                    block_elem.append(sub_stmt)
            else:
                block_elem.append(stmt)

        # Додаємо <block> до методу
        method_elem.append(block_elem)

        return method_elem






    def blockstat(self, statements):
        """Обробка списку команд у блоці"""
        # print("blockstat DEBUG ->   ", statements)
        # print()
        # print()
        block_elem = ET.Element("block")  

        for order, stmt in enumerate(statements, start=1):
            if isinstance(stmt, ET.Element) and stmt.tag == "assign":
                stmt.set("order", str(order))  # ✅ Додаємо порядок виконання
            elif isinstance(stmt, Tree):  
                stmt = self.transform(stmt)  # Рекурсивне перетворення
                
            block_elem.append(stmt)

        return block_elem  # ✅ Тепер повертає XML






    def expr_tail(self, args):
        """Обробка виразів, які мають селектори (наприклад, obj from: 10 a: 5 b: 3)."""
        # print("expr_tail DEBUG ->   ", args)
        
        selectors = []  # Зберігає всі `from:`, `a:`, `b:` і т.д.
        values = []     # Зберігає всі значення аргументів
        newArgs = []
        # print(f"----------------------------- {len(args)}")
        if len(args) == 0: 
            return None
        if len(args) == 1 and isinstance(args[0], tuple):  
            args = args[0]
            for arg in args:
                newArgs.append(arg[0])
        elif len(args) == 1 and isinstance(args, list) :
            newArgs = args
        # else:
            
            # print("expr_tail DEBUG ->   ", args)
            
            
            
        # print(f"------------------------- {newArgs}")



        if not args:
            return None, []  # Якщо немає аргументів, повертаємо порожній селектор



        for arg in newArgs:
            
            if isinstance(arg, Token) and arg.type == "ID_COLON":
                selectors.append(arg.value)  # Додаємо `from:`, `a:`, `b:`
            elif isinstance(arg, Token) and arg.type == "ID":
                selectors.append(arg.value)
            elif isinstance(arg, Token) and arg.type == "VALID_ID":
                selectors.append(arg.value)
            elif isinstance(arg, ET.Element):
                values.append(arg)  # Додаємо аргументи (наприклад, `1`, `2`, `4`)

        # 🛠 **Виправлення помилки `IndexError`**
        if len(selectors) == 0:
            selector = None  # Якщо немає селекторів, повертаємо None
        elif len(selectors) == 1:
            selector = selectors[0]  # Якщо один селектор, повертаємо його як є
        else:
            selector = "".join(selectors)  # Якщо кілька селекторів, об'єднуємо їх

        # print("✅ FIXED expr_tail -> ", selector, values)
        return selector, values  # ✅ Повертаємо коректний селектор + значення




    
    def expr(self, args):
        """Обробка виразів"""
        # print("expr DEBUG ->   ", args)

        if len(args) == 1:
            base = args[0]
            tail = None
        else:
            base, tail = args

        # Якщо `base` — це ім'я класу (наприклад, `Integer`)
        if isinstance(base, str):  
            if base[0].isupper():
                base = ET.Element("literal", {"class": "class", "value": base})
            else:
                base = ET.Element("var", name=base)

        if tail:
            # Переконуємось, що `tail` - це tuple, а не Tree
            if isinstance(tail, tuple):  
                selector, values = tail
            else:
                selector = tail
                values = []

            send_elem = ET.Element("send", selector=str(selector))  # Тепер буде `from:a:b:`
            expr_elem = ET.SubElement(send_elem, "expr")
            expr_elem.append(base)  # Додаємо `Integer`

            # Додаємо аргументи всередину `send`
            for i, value in enumerate(values, start=1):
                arg_elem = ET.SubElement(send_elem, "arg", order=str(i))
                expr_inner = ET.SubElement(arg_elem, "expr")
                expr_inner.append(value)

            # print(f"✅ FIXED expr повертає -> {ET.tostring(send_elem, encoding='unicode')}")
            return send_elem

        return base


    def process_block(self, block_tree):
        """Обробка блоку коду або виразу у вигляді блоку"""
        if not isinstance(block_tree, Tree) or block_tree.data != "block":
            raise ValueError(f"Очікувався Tree(block), отримано {type(block_tree)}: {block_tree}")

        children = block_tree.children

        # Перевіряємо, чи є `param_list`
        if len(children) >= 2 and isinstance(children[0], Tree) and children[0].data == "param_list":
            param_list = children[0]
            block_body = children[1] if len(children) > 1 and isinstance(children[1], ET.Element) else None

            # Створюємо блок із правильним `arity`
            param_count = len(param_list.children)
            block_elem = ET.Element("block", arity=str(param_count))

            # Додаємо параметри
            for i, param in enumerate(param_list.children, start=1):
                ET.SubElement(block_elem, "parameter", name=param, order=str(i))

            # Додаємо тіло блоку, тільки якщо це **НЕ ВЖЕ БЛОК**
            if block_body is not None and block_body.tag != "block":
                block_elem.append(block_body)

        else:
            block_elem = ET.Element("block", arity="0")

        return block_elem





    def assign(self, args):
        """Обробка присвоєння (:=)"""
        var_name, value = args
        assign_elem = ET.Element("assign")

        ET.SubElement(assign_elem, "var", name=var_name)
        expr_elem = ET.SubElement(assign_elem, "expr")

        # Якщо value - це `Tree`, то перевіряємо, чи це `block`
        if isinstance(value, Tree) and value.data == "block":
            block_elem = self.process_block(value)  # Використовуємо ту ж саму логіку, що і в `method_def`
            expr_elem.append(block_elem)
        
        elif isinstance(value, ET.Element):
            expr_elem.append(value)  # Якщо це вже XML, додаємо його

        else:
            expr_elem.text = str(value)  # Якщо це число або рядок, додаємо як текст

        return assign_elem  # ✅ Тепер повертає коректний XML




    def expr_base(self, args):
        # print("expr_base DEBUG ->   ", args)
        # print()
        # print()
        base = args[0]  # Отримуємо токен
        
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
        
        return base  # Якщо це вже `ET.Element`, просто повертаємо його

    def expr_sel(self, args):
        """Обробка селекторних виразів (object method: value)."""
        # print("expr_sel DEBUG ->   ", args)

        selectors = []
        values = []

        for arg in args:
            if isinstance(arg, Token) and arg.type == "ID_COLON":
                selectors.append(arg)  # `from:`
            elif isinstance(arg, ET.Element):
                values.append(arg)  # `Integer`, `1`
            else:
                print(f"⚠️ ПОМИЛКА: Невідомий аргумент у expr_sel -> {arg}")

        # if not selectors:
        #     return None, values  # Якщо селектора немає, повертаємо значення

        return selectors, values




    def SIGNED_INT(self, token):
        """Обробка чисел"""
        #return ET.Element("literal", attrib={"class": "Integer"}, value=str(token))
        return token

    def STR(self, token):
        """Обробка рядків"""
        #return ET.Element("literal", attrib={"class": "String"}, value=token.strip("'"))
        return token
    def ID(self, token):
        """Обробка ідентифікаторів"""
        # if token in {"nil", "true", "false"}:
        #     return ET.Element("literal", {"class": token.capitalize(), "value": token})
        # return ET.Element("var", name=token)
        return token


    def CID(self, token):
        """Обробка імен класів"""
        return token

    def ID_COLON(self, token):
        """Обробка селекторів методів"""
        return token  

    def COLON_ID(self, token):
        """Обробка імен параметрів"""
        return token[1:]  # Видаляємо двокрапку
    
    def EXP_KEYWORD(self, token):
        """Обробка селекторів методів"""
        return token
    def KEYWORD(self, token):
        """Обробка селекторів методів"""
        return token
    def VALID_ID(self, token):
        """Обробка селекторів методів"""
        return token
    def METHOD_COLON(self, token):
        """Обробка селекторів методів"""
        return token


    def transform_to_xml(self):
        """Генерує XML з відступами"""
        raw_xml = ET.tostring(self.root, encoding="utf-8")  # Генеруємо XML як байти
        parsed_xml = xml.dom.minidom.parseString(raw_xml)  # Парсимо для форматування
        formatted_xml = parsed_xml.toprettyxml(indent="  ")  # Форматуємо XML
        # print("----------------------------------------------------------------")
        # print(formatted_xml)
        # print("----------------------------------------------------------------")
        # Not the best way 
        formatted_xml = formatted_xml.replace('<?xml version="1.0" ?>', '<?xml version="1.0" encoding="UTF-8"?>')

        return formatted_xml

def print_help():
    print("""Code Analyzer in SOL25 (parse.py)
The filter-type script (parse.py in Python 3.11) reads source code in SOL25 from standard input, 
checks the lexical, syntactic, and static semantic correctness of the code, and outputs the XML representation 
of the abstract syntax tree of the program.""")

def extract_first_comment(code):
    """Вилучає перший блочний коментар у SOL25."""
    comment_pattern = re.compile(r'"([^"]*)"', re.DOTALL)
    match = comment_pattern.search(code)
    
    return match.group(1) if match else None

# def format_comment(comment):
#     """Форматує коментар для XML, замінюючи `\n` на `&#10;` та запобігаючи екрануванню `&`."""
#     if comment:
#         return comment.replace("\n", "&#10;")  # Замінюємо новий рядок
#     return None


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
    # POTIM dorobyty
    else:
        input_data = sys.stdin.read()
        
        
    # print(input_data)
    # print("Input data above ---------------------------------------")
    tokens = tokenize(input_data)
    # print()
    # print(tokens)
    # print("Tokens above ---------------------------------------")
    # print()
    # for token in tokens:
    #     # print(token)
    
    parse_tree = parse_code(input_data)
    transformer = SOL25Transformer()
    xml_tree = transformer.transform(parse_tree)
    xml_output = transformer.transform_to_xml()
    print(xml_output)
    sys.exit(0)
      
if __name__ == "__main__":
    main()
    