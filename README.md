# Documentation of Project Implementation for IPP 2024/2025

### **Name and surname:** Rostyslav Kachan

### **Login**: xkacha02

## Short description
The `parse.py` script, written in Python 3.11, reads source code in SOL25 from standard input, verifies its lexical, syntactic, and semantic correctness, and outputs an XML representation of the program's abstract syntax tree (AST).

## Usage
To use the script, run it from the command line with(in PowerShell):
```bash
gc .\input.sol25 | python parse.py
```
The `--help` option provides brief information about this script
```bash
python3.11 parse.py --help
```
## Design Philosophy


The parse.py script combines procedural and object-oriented programming, ensuring a structured yet simple design. OOP is used where it logically encapsulates data and functionality, improving modularity and maintainability, while procedural code keeps the implementation straightforward. This balance prevents unnecessary complexity while effectively handling lexical, syntactic, and semantic analysis. The main libraries used in parse.py are: 

- `lark` – Provides a powerful LALR(1) parser, efficiently processing the grammar and constructing the abstract syntax tree (AST). 
- `xml.etree.ElementTree` – Generates and manipulates the XML output representing the parsed syntax tree.
- `re` – Provides regular expressions for efficient lexical analysis.

## Architecture

The script follows a structured approach to parsing SOL25 source code. The process consists of the following steps:

1. **Lexical Analysis** – The input source code is tokenized using regular expressions. This ensures proper classification of keywords, identifiers, literals, and symbols.
2. **Parsing and Lark Tree Generation** – The input source code is passed to the `Lark` parser, which processes the predefined grammar and constructs an Abstract Syntax Tree (AST).
3. **Semantic analysis** - AST is checked for semantic correctness, including the presence of the `Main` class, overriding class methods and cyclic inheritance. 
4. **XML Generation** – The verified AST is transformed into a structured XML representation, providing a machine-readable output of the parsed code.

### Classes
![Class diagram](IPP.drawio.svg)

### Class Overview
- **SOL25Transformer** – Converts the Lark-generated AST into an XML representation by iterating through nodes and transforming expressions, assignments, and method definitions.
- **SOL25Semantic** – Performs semantic validation, ensuring class inheritance rules, method uniqueness, and variable usage correctness.

Each of these components plays a critical role in ensuring accurate lexical, syntactic, and semantic analysis before generating the final XML output.

## Restrictions
The current semantic analysis has limitations: it does not check  exact parameter counts, block parameters may conflict with local variables or other block parameters, and undefined variables  are not validated.