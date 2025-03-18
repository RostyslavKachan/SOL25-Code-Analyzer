#Kachan Rostyslav xkacha02
# IPP 2024 1.part
import sys
import re
import argparse
import xml.etree.ElementTree as ET
from lark import Lark, Transformer, Tree, UnexpectedInput, UnexpectedCharacters, UnexpectedToken, LexError, Token , Visitor
import xml.dom.minidom



TOKEN_TYPES = [
    # @brief Keywords in SOL25.
    (r"\bclass\b", "KEY_CLASS"),
    (r"\bself\b", "KEY_SELF"),
    (r"\bsuper\b", "KEY_SUPER"),
    (r"\bnil\b", "KEY_NIL"),
    (r"\btrue\b", "KEY_TRUE"),
    (r"\bfalse\b", "KEY_FALSE"),

    # @brief Built-in class names.
    (r"\bObject\b", "OBJECT_CLASS"),
    (r"\bNil\b", "NIL_CLASS"),
    (r"\bTrue\b", "TRUE_CLASS"),
    (r"\bFalse\b", "FALSE_CLASS"),
    (r"\bInteger\b", "INTEGER_CLASS"),
    (r"\bString\b", "STRING_CLASS"),
    (r"\bBlock\b", "BLOCK_CLASS"),

    # @brief Identifiers and selectors.
    (r":[a-z_][a-zA-Z0-9_]*", "PARAMETER"),
    (r"\b[A-Z][a-zA-Z0-9_]*\b", "CLASS_ID"),
    (r"\b[a-z_][a-zA-Z0-9_]*\b", "ID"),
    (r"\b[a-z_][a-zA-Z0-9_]*(:[a-z_][a-zA-Z0-9_]*)*:", "SELECTOR"),

    # @brief Literals.
    (r"[+-]?\d+", "INTEGER"),  
    (r"'(?:\\['n\\]|[^'\\\n])*'", "STRING"),  

    # @brief Operators and delimiters.
    (r":=", "ASSIGN"),
    (r":", "COLON"),
    (r"\.", "DOT"),
    (r"\(", "L_ROUND"), 
    (r"\)", "R_ROUND"),   
    (r"\{", "L_CURLY"),   
    (r"\}", "R_CURLY"),   
    (r"\[", "L_BRACKET"), 
    (r"\]", "R_BRACKET"), 
    (r"\|", "PIPE"),  

    # @brief Ignored characters (whitespace, comments).
    (r"\s+", None), 
    (r"\".*?\"", None)
]

# @brief Lark grammar based on SOL25 language.
GRAMMAR = r'''
program: class_def*

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
# @brief Create a Lark parser for the SOL25 language.
parser = Lark(GRAMMAR,start = 'program',parser="lalr")

def print_help():
    print("""Code Analyzer in SOL25 (parse.py)
The filter-type script (parse.py in Python 3.11) reads source code in SOL25 from standard input, 
checks the lexical, syntactic, and static semantic correctness of the code, and outputs the XML representation 
of the abstract syntax tree of the program.""")

def tokenize(code):
    """
    @brief Tokenizes the given SOL25 source code.
    
    @param code The source code as a string.
    @return A list of tuples, where each tuple contains a token type and its corresponding lexeme.

    @details
    This function scans the input code and breaks it into tokens based on predefined patterns.
    It follows these steps:
    1. Skips over comments enclosed in double quotes.
    2. Matches the code against predefined token patterns from TOKEN_TYPES.
    3. Adds recognized tokens to the token list.
    4. Handles invalid tokens by reporting an error and terminating execution.
    """
    tokens = []
    while code:
        match = None

        # @brief Skip comments enclosed in double quotes.
        if code.startswith('"'):
            end_index = code.find('"', 1)
            if end_index == -1:
                sys.stderr.write("Error: Unclosed comment in source code.\n")
                sys.exit(21)
            code = code[end_index + 1:]
            continue  

        # @brief Iterate through predefined token patterns.
        for pattern, token_type in TOKEN_TYPES:
            regex = re.compile(pattern)
            match = regex.match(code)

            if match:
                lexeme = match.group(0)
           
                # @brief Store the token only if it has a valid type.
                if token_type:  
                   tokens.append((token_type, lexeme))

                # @brief Move the cursor forward in the input code.
                code = code[match.end():]
                break  

        # @brief Handle unrecognized tokens.
        if not match:
            print("\n Error: Invalid token detected!")
            print(f"   Remaining code: {code[:20]}")  
            print(f"   Last extracted tokens: {tokens[-5:]}")  
            sys.stderr.write(f"Error: Invalid token near '{code[:20]}'\n")
            sys.exit(21)

    return tokens


def parse_code(code):
    
    """
    @brief Parses the given SOL25 source code.

    @param code The source code as a string.
    @return A parse tree representation of the code.

    @details
    This function attempts to parse the input code using the Lark parser.
    If parsing is successful, it returns the corresponding parse tree.
    Otherwise, it handles syntax and lexical errors by printing an error message
    and terminating the program with an appropriate exit code.
    
    @throws SyntaxError (exit code 22) if the code contains a syntax error.
    @throws LexicalError (exit code 21) if the code contains an invalid token.
    """
    try:
        
        tree = parser.parse(code)
        return tree
    except UnexpectedToken as e:
        sys.stderr.write("Error: Syntax error.\n")
        sys.exit(22)
    except UnexpectedCharacters:
        sys.stderr.write("Error: Lexical error.\n")
        sys.exit(21)
    except UnexpectedInput as e:
        sys.stderr.write("Error: Syntax error.\n")
        sys.exit(22)
    except LexError:
        sys.stderr.write("Error: Lexical error.\n")
        sys.exit(21)
        
        
class SOL25Semantic(Visitor):
    # @brief Performs semantic analysis of the parsed SOL25 source code.
    
    def __init__(self):
    # @brief Initializes data structures for semantic analysis.
    
        self.found_main = False   
        self.has_run_method = False  
        self.class_names = set()  
        self.current_class = None
        self.current_method = None
        self.methods = {}  
        self.builtin_classes = {"Object", "Nil", "Integer", "String", "Block", "True", "False"}
        self.class_variables = set()
        self.last_CID = None
        self.class_parents = {}
        self.method_params = {}
        self.method_param_names = {}
        

  

    def collect_classes(self, tree):
        """
        @brief Collects class definitions and validates uniqueness.

        @param tree Parsed syntax tree of the program.

        @details
        - Scans all class definitions in the syntax tree.
        - Checks for duplicate class declarations.
        - Records class names and their parent classes.
        - Detects cyclic inheritance structures.
        """
        for class_tree in tree.children:
            if class_tree.data == "class_def":
                class_name = class_tree.children[0].value
                parent_class = class_tree.children[1].value 

                
                if class_name in self.class_names:
                    sys.stderr.write(f"Error: Class {class_name} was declared twice.\n")
                    sys.exit(35)

                self.class_names.add(class_name)  
                self.class_parents[class_name] = parent_class  
                
        visited = set()
        for class_name in self.class_parents:
            self.detect_cycle(class_name, visited, set())  
                
         
         
    def detect_cycle(self, class_name, visited, stack):
        """
        @brief Detects cyclic inheritance in the class hierarchy.

        @param class_name The class currently being checked.
        @param visited Set of already validated classes.
        @param stack Set representing the current path in the inheritance tree.

        @details
        - Uses depth-first search (DFS) to detect inheritance cycles.
        """
        if class_name in stack:  
            sys.stderr.write(f"Error: Cyclic inheritance detected involving class {class_name}.\n")
            sys.exit(35)

        if class_name not in self.class_parents or class_name in visited:
            return  

        stack.add(class_name)  
        parent = self.class_parents[class_name]

        self.detect_cycle(parent, visited, stack)  
        stack.remove(class_name)  
        visited.add(class_name)     
        
            
    def collect_methods(self, tree):
        """
        @brief Collects method definitions and validates uniqueness.

        @param tree Parsed syntax tree of the program.

        @details
        - Scans each class for defined methods.
        - Checks for duplicate method definitions within a class.
        - Validates that method parameters have unique names.
        """
        for class_tree in tree.children:
            if class_tree.data == "class_def":
                class_name = class_tree.children[0].value  

                if class_name not in self.methods:
                    self.methods[class_name] = {}
                if class_name not in self.method_params:
                    self.method_params[class_name] = {}
                if class_name not in self.method_param_names:
                    self.method_param_names[class_name] = {}  

                for method_tree in class_tree.children[2:]:  
                    if method_tree.data == "method_def":
                        method_name = self.extract_method_name(method_tree.children[0])

                        
                        if method_name in self.methods[class_name]:
                            sys.stderr.write(f"Error: Method '{method_name}' is redefined in class '{class_name}'.\n")
                            sys.exit(35)  

                        
                        param_list = next((child for child in method_tree.children if child.data == "param_list"), None)
                        param_names = [param.value.lstrip(":") for param in param_list.children if isinstance(param, Token)] if param_list else []
                        param_count = len(param_names)

                        
                        if len(param_names) != len(set(param_names)):
                            sys.stderr.write(f"Error: Duplicate parameter names in method '{method_name}' of class '{class_name}'.\n")
                            sys.exit(35) 

                        self.methods[class_name][method_name] = param_count
                        self.method_params[class_name][method_name] = param_count
                        self.method_param_names[class_name][method_name] = param_names  






    def class_def(self, tree):
        """
        @brief Processes a class definition.

        @param tree Parsed syntax tree representing the class definition.

        @details
        - Extracts the class name and its parent class.
        - Ensures that a class does not inherit from itself.
        - Validates that the parent class is either defined or a built-in class.
        - If the class is `Main`, marks it as found.
        """
        class_name = tree.children[0].value  
        parent_class = tree.children[1].value
        
        self.current_class = class_name

        if class_name == parent_class:
            sys.stderr.write(f"Error: Class {class_name} cannot inherit itself.\n")
            sys.exit(32)

        if parent_class not in self.class_names and parent_class not in self.builtin_classes:
            sys.stderr.write(f"Error: Class {class_name} extends undefined class {parent_class}.\n")
            sys.exit(32)

        if class_name == "Main":
            self.found_main = True

    def method_def(self, tree):
        """
        @brief Processes a method definition.

        @param tree Parsed syntax tree representing the method definition.

        @details
        - Extracts the method name.
        - Clears previously stored variables for the new method scope.
        - Validates that the method is defined within its class.
        - Ensures the `run` method in `Main` has no parameters.
        """
        method_name = self.extract_method_name(tree.children[0])  
        self.current_method = method_name
        param_list = tree.children[1] if len(tree.children) > 1 else None
        param_count = len(param_list.children) if isinstance(param_list, Tree) and param_list.data == "param_list" else 0
        self.class_variables.clear()

        
        if method_name not in self.methods[self.current_class]:
            sys.stderr.write(f"Error: Method '{method_name}' is not defined in class '{self.current_class}'.\n")
            sys.exit(32)
        
       
        if self.current_class == "Main" and method_name == "run":
            self.has_run_method = True
            if param_count > 0:
                sys.stderr.write("Error: Method 'run' in class 'Main' must not have parameters.\n")
                sys.exit(33)


    def extract_method_name(self, method_name_tree):
        """
        @brief Extracts the method name from the parsed syntax tree.

        @param method_name_tree Tree node containing method name information.

        @return str The extracted method name.

        """
        if isinstance(method_name_tree, Token):  
            return method_name_tree.value  
        elif isinstance(method_name_tree, Tree) and method_name_tree.data == "method_name":
            method_name_subtree = method_name_tree.children[0]
            if isinstance(method_name_subtree, Token):  
                return method_name_subtree.value  
            elif isinstance(method_name_subtree, Tree) and method_name_subtree.data == "method_selector":
                return "".join(child.value for child in method_name_subtree.children if isinstance(child, Token))

        sys.stderr.write("Error: Invalid method name format.\n")
        sys.exit(21)


            
    def expr_base(self, tree):
        """
        @brief Processes the base of an expression.

        @param tree Parsed syntax tree representing the base expression.

        @details
        - If the base is a token:
        - Accepts integer (`SIGNED_INT`) and string (`STR`) literals.
        - Validates if a class identifier (`CID`) exists in defined or built-in classes.
        - If the base is another expression (`expr`), recursively processes it.
        """
        
        if isinstance(tree.children[0], Token):
            token = tree.children[0]

            
            if token.type in {"SIGNED_INT", "STR"}:
                return  

            elif token.type == "CID":
                class_name = token.value
                if class_name not in self.class_names and class_name not in self.builtin_classes:
                    sys.stderr.write(f"Error: Undefined class '{class_name}'.\n")
                    sys.exit(32)
                self.last_CID = class_name
        elif isinstance(tree.children[0], Tree):
            node = tree.children[0]

            
            if node.data == "expr":
                self.visit(node)
            elif node.data == "block":
                return
            else:
                sys.stderr.write(f"Error: Unexpected expression base '{node.data}'.\n")
                sys.exit(22)


    def expr_tail(self, tree):
        """
        @brief Processes the tail of an expression.

        @param tree Parsed syntax tree representing the expression tail.

        @details
        - If empty, returns immediately.
        - If the first child is a token:
        - Validates `read` method for `String`-descendant classes.
        - Resets `last_CID` after validation.
        
        """
        if not tree.children:
            return  

        first_child = tree.children[0] 

        
        if isinstance(first_child, Token):
            method_name = first_child.value  

            
            if self.last_CID and method_name == "read":
                if not self.is_descendant_of_string(self.last_CID):
                    sys.stderr.write(f"Error: Class '{self.last_CID}' cannot use method '{method_name}'.\n")
                    sys.exit(32)
                else:
                    self.last_CID = None
                    return
                
            
        
        elif isinstance(first_child, Tree):
            if first_child.data == "expr_sel":
                return  
            else:
                sys.stderr.write(f"Error: Unexpected structure in expr_tail: {first_child.data}\n")
                sys.exit(22)
                
    def is_descendant_of_string(self, class_name):
        """
        @brief Checks if a given class is a descendant of 'String'.

        @param class_name The name of the class to check.
        @return True if the class or any of its ancestors is 'String', otherwise False.

        @details
        - Iteratively traverses the inheritance hierarchy.
        - Uses `class_parents` to move up the class tree.
        - Returns True if 'String' is found as a parent, otherwise returns False.
        """
        while class_name:
            if class_name == "String":
                return True  
            class_name = self.class_parents.get(class_name, None) 
        return False  

    def assign(self, tree):
        """
        @brief Handles variable assignment in the parsed syntax tree.

        @param tree The parsed syntax tree containing an assignment operation.

        @details
        - Extracts the variable name being assigned.
        - Checks if the variable conflicts with method parameters.
        - If the variable name matches a method parameter, exits with an error.
        - Otherwise, adds the variable to `class_variables`.
        """
        
        var_name = tree.children[0].value 

        
        if self.current_class in self.method_param_names and self.current_method in self.method_param_names[self.current_class]:
            param_names = [param.lstrip(":") for param in self.method_param_names[self.current_class][self.current_method]]  
            
            if var_name in param_names:
                sys.stderr.write(f"Error: Variable '{var_name}' in method '{self.current_method}' of class '{self.current_class}' conflicts with a method parameter.\n")
                sys.exit(34)  

        self.class_variables.add(var_name)

    def check_final(self):
        """
        @brief Performs final validation checks before parsing completes.

        @details
        - Ensures that the 'Main' class exists.
        - Ensures that the 'Main' class contains a method named 'run'.
        - Exits with an error if any of these conditions are not met.
        """
        if not self.found_main:
            sys.stderr.write("Error: Class 'Main' is missing!\n")
            sys.exit(31)

        if not self.has_run_method:
            sys.stderr.write("Error: Class 'Main' does not have a method 'run'!\n")
            sys.exit(31)


def check_semantics(parse_tree):
    """
    @brief Performs semantic analysis on the parsed syntax tree.

    @param parse_tree The root of the parsed syntax tree.

    @details
    - Initializes an instance of `SOL25Semantic` to check for semantic errors.
    - Collects class definitions and validates inheritance rules.
    - Collects method definitions and verifies method uniqueness.
    - Traverses the syntax tree in a top-down manner to check for rule violations.
    - Runs a final validation to ensure the presence of a valid `Main` class with a `run` method.
    
    """
    semantic_check = SOL25Semantic()
    semantic_check.collect_classes(parse_tree)
    semantic_check.collect_methods(parse_tree)
    semantic_check.visit_topdown(parse_tree)
    semantic_check.check_final()
    
    
class SOL25Transformer(Transformer):
    #  @brief Transforms the parsed syntax tree into an XML representation.

    def __init__(self):
        """
        @brief Initializes the XML root element and extracts the program description.

        @note The description is retrieved from the first comment in the source code.
        """
        global input_data
        super().__init__()
        self.root = ET.Element("program", language="SOL25")
        comment_text = extract_first_comment(input_data)
        if comment_text:
            self.root.set("description", comment_text)

    def program(self, classes):
        """
        @brief Constructs the XML representation of a program.

        @param classes List of class elements.

        @return The root XML element representing the program.

        @details
        - Iterates over the parsed classes and appends them to the root XML element.
        """
        for cls in classes:
            self.root.append(cls)
        return self.root

    def class_def(self, args):
        """
        @brief Transforms a class definition into an XML element.

        @param args A list where:
            - The first element is the class name.
            - The second element is the parent class name.
            - The remaining elements are method definitions.

        @return An XML element representing the class.
        """
        class_name, parent_name, *methods = args
        class_elem = ET.Element("class", name=class_name, parent=parent_name)
        for method in methods:
            class_elem.append(method)
        return class_elem

    def method_def(self, args):
        """
        @brief Transforms a method definition into an XML element.

        @param args A list where:
            - The first element represents the method name.
            - The second (optional) element contains method parameters.
            - The remaining elements form the method body.

        @return An XML element representing the method.

        @details
        - Extracts the method name from the syntax tree.
        - Checks for method parameters and constructs the method signature.
        - Converts method body statements into an XML representation.
        - Handles methods with and without parameters.
    """
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
        """
        @brief Transforms a list of statements into an XML block element.

        @param statements A list of parsed statements to be transformed.

        @return An XML element representing a block of code.

        @details
        - Iterates through the statements and assigns execution order to assignments.
        - Transforms trees into XML elements where necessary.
        - Appends processed statements to the block element.
    """
        block_elem = ET.Element("block")  

        for order, stmt in enumerate(statements, start=1):
            if isinstance(stmt, ET.Element) and stmt.tag == "assign":
                stmt.set("order", str(order))  
            elif isinstance(stmt, Tree):  
                stmt = self.transform(stmt) 
                
            block_elem.append(stmt)

        return block_elem 


    def expr_tail(self, args):
        """
        @brief Processes selector expressions and their arguments.

        @param args A list of elements representing selectors and their corresponding arguments.

        @return A tuple containing:
            - A string representing the full selector.
            - A list of XML elements representing the arguments.

        @details
        - Extracts method selectors and their corresponding argument expressions.
        - Supports nested expressions and multiple selectors.
        - Handles various argument types, including Tokens, Trees, and XML elements.
        """
        selectors = []
        values = []
        newArgs = []

        if not args:
            return 

        
        while len(args) == 1 and isinstance(args[0], tuple):
            args = args[0]

        for arg in args:
            if isinstance(arg, tuple) and len(arg) == 2:
                selectors.extend(arg[0])
                values.extend(arg[1])
            else:
                newArgs.append(arg)

        
        for arg in newArgs:
            if isinstance(arg, Token) and arg.type == "ID_COLON":
                selectors.append(arg.value)  
            elif isinstance(arg, Token) and arg.type == "VALID_ID":
                selectors.append(arg.value)  
            elif isinstance(arg, ET.Element):
                values.append(arg)  
            elif isinstance(arg, str):
                selectors.append(arg)
            elif isinstance(arg, list):
                for sub_arg in arg:
                    if isinstance(sub_arg, Token) and sub_arg.type == "ID_COLON":
                        selectors.append(sub_arg.value)
                    elif isinstance(sub_arg, ET.Element):
                        values.append(sub_arg)
                    elif isinstance(sub_arg, Tree):
                        values.append(self.transform(sub_arg))
                    elif isinstance(sub_arg, str):
                        selectors.append(sub_arg)

        
        selector = "".join(selectors) if selectors else None

        return selector, values 


    def expr(self, args):
        """
        @brief Transforms an expression into an XML representation.

        @param args A list containing the components of the expression.

        @return An XML element representing the expression.

        @details
        - Extracts the base of the expression and its potential selector (method call).
        - Converts variables, literals, and blocks into appropriate XML elements.
        - Handles method calls (`send` elements) with arguments.
        """
        if len(args) == 2 and args[1] is None:
            base = args[0]
            tail = None
        else:
            base, tail = args

        
        if isinstance(base, str):
            if base[0].isupper():
                base = ET.Element("literal", {"class": "class", "value": base})
            else:
                base = ET.Element("var", name=base)

        elif isinstance(base, Tree):
            if base.data == "block":
                base = self.process_block(base)  
            else:
                transformed_base = self.transform(base)  
                
                if isinstance(transformed_base, ET.Element):
                    base = transformed_base  
                else:
                    base = None  

        if tail:
            if isinstance(tail, tuple):
                selector, values = tail
            else:
                selector = tail
                values = []

            send_elem = ET.Element("send", selector=str(selector))
            expr_elem = ET.SubElement(send_elem, "expr")

            
            if isinstance(base, ET.Element):
                expr_elem.append(base)
            elif base is not None:
                print(f"Error: Cannot add base to XML -> {base}")
           
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
                        print(f"Error: Cannot transorm Tree to XML -> {value}")

                elif isinstance(value, ET.Element):
                    expr_inner.append(value)  

                elif isinstance(value, str):
                    literal_elem = ET.Element("literal", {"class": "String", "value": value})
                    expr_inner.append(literal_elem)

                else:
                    print(f"Error: Unknown type of argument -> {type(value)}")

            return send_elem

        return base  

    def process_block(self, block_tree):
        """
        @brief Processes a block of code and converts it into an XML representation.

        @param block_tree A parse tree representing the block.

        @return An XML element representing the block.

        @details
        - Checks if the input is a valid "block" tree.
        - Extracts parameters from the block and assigns them to XML attributes.
        - Processes the block's body and adds corresponding XML elements.
        - If no parameters are found, the arity is set to 0.
        """
        if not isinstance(block_tree, Tree) or block_tree.data != "block":
            raise ValueError(f"Expect Tree(block), but get {type(block_tree)}: {block_tree}")

        children = block_tree.children

        
        if len(children) >= 2 and isinstance(children[0], Tree) and children[0].data == "param_list":
            param_list = children[0]
            block_body = children[1] if len(children) > 1 and isinstance(children[1], ET.Element) else None

            param_count = len(param_list.children)
            block_elem = ET.Element("block", arity=str(param_count))

            for i, param in enumerate(param_list.children, start=1):
                ET.SubElement(block_elem, "parameter", name=param, order=str(i))

            
            if block_body is not None and block_body.tag == "block":
                for sub_elem in list(block_body):
                    block_elem.append(sub_elem)  
            elif block_body is not None:
                block_elem.append(block_body)

        else:
            block_elem = ET.Element("block", arity="0")

        return block_elem


    def assign(self, args):
        """
        @brief Converts an assignment statement into an XML representation.

        @param args A list containing the variable name and assigned value.

        @return An XML element representing the assignment.

        @details
        - Extracts the variable name and value from the input arguments.
        - Creates an XML element for the assignment operation.
        - Converts the assigned value into the correct XML format.
        
        """
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
        """
        @brief Converts a base expression into an XML representation.

        @param args A list containing the base expression.

        @return An XML element representing the base expression.
        """
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
        """
        @brief Processes a selector-based expression and converts it into an XML representation.

        @param args A list containing selectors and values.

        @return A tuple containing:
            - A list of selector strings.
            - A list of argument values in XML format.

        @details
        - Extracts method selectors and corresponding argument values.
        - Supports:
        - Chained selectors (`ID_COLON`).
        - Expression values converted into XML.
        - Blocks transformed into XML before being added as arguments.
        - Nested selectors and arguments extracted from tuples.
        """
        selectors = []
        values = []

        for arg in args:
            if isinstance(arg, Token) and arg.type == "ID_COLON":
                selectors.append(arg.value)  
            elif isinstance(arg, ET.Element):
                values.append(arg)  
            elif isinstance(arg, tuple) and len(arg) == 2:
                prev_selectors, prev_values = arg
                selectors.extend(prev_selectors)  
                values.extend(prev_values)  
            elif isinstance(arg, Tree) and arg.data == "block":
                
                block_xml = self.transform(arg)
                values.append(block_xml)
            else:
                print(f"Error: Unknown argument in expr_sel -> {arg}")

        return selectors, values 

    # @brief Return different  type of  tokens.
    def SIGNED_INT(self, token):
        return token
    def STR(self, token):
        return token
    def ID(self, token):
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
        """
        @brief Converts the internal XML representation to a formatted string.

        @return A well-formatted XML string with proper indentation and encoding.
        """
        raw_xml = ET.tostring(self.root, encoding="utf-8")  
        parsed_xml = xml.dom.minidom.parseString(raw_xml) 
        formatted_xml = parsed_xml.toprettyxml(indent="  ")  
        formatted_xml = formatted_xml.replace('<?xml version="1.0" ?>', '<?xml version="1.0" encoding="UTF-8"?>')

        return formatted_xml




def extract_first_comment(code):
    """
    @brief Extracts the first comment from the given source code.

    @param code The source code as a string.

    @return The first comment found, or None if no comment is present.
    """
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

input_data = ""
def main():
    """
    @brief Entry point of the script, responsible for parsing arguments, reading input, 
           performing lexical analysis, parsing, semantic analysis, and XML transformation.

    @details
    - Uses `argparse` to handle command-line arguments.
    - Supports `--help` and `-h` for displaying usage information.
    - Reads input from a file (if provided) or from standard input.
    - Prints the resulting XML to standard output.
   
    """
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
    parse_tree = parse_code(input_data)
    check_semantics(parse_tree)
    transformer = SOL25Transformer()
    xml_tree = transformer.transform(parse_tree)
    xml_output = transformer.transform_to_xml()
    print(xml_output)
    sys.exit(0)
      
if __name__ == "__main__":
    main()
    