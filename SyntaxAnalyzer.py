import os
import re
from typing import NamedTuple

# TODO: refactor, one thing, see if _eat can be called before handling the lexical

LET_STATEMENT = "letStatement"

IN_FILE_EXT = ".jack"
OUT_FILE_EXT = "_test.xml"
NEWLINE = "\n"
# Jack Lexical elements
# keywords
CLASS = "class"
CONSTRUCTOR = "constructor"
FUNCTION = "function"
METHOD = "method"
FIELD = "field"
STATIC = "static"
VAR = "var"
INT = "int"
CHAR = "char"
BOOLEAN = "boolean"
VOID = "void"
TRUE = "true"
FALSE = "false"
NULL = "null"
THIS = "this"
LET = "let"
DO = "do"
IF = "if"
ELSE = "else"
WHILE = "while"
RETURN = "return"
# Symbols
LEFT_BRACE = "{"
RIGHT_BRACE = "}"
LEFT_PAREN = "("
RIGHT_PAREN = ")"
LEFT_BRACKET = "["
RIGHT_BRACKET = "]"
DOT = "."
COMMA = ","
SEMI_COLON = ";"
PLUS = "+"
MINUS = "-"
ASTERISK = "*"
FORWARD_SLASH = "/"
AMPERSAND = "&"
PIPE = "|"
LESS_THAN = "<"
GREATER_THAN = ">"
EQUAL_SIGN = "="
TILDE = "~"
# Other constants
KEYWORD = "keyword"
SYMBOL = "symbol"
INT_CONSTANT = "integerConstant"
STR_CONSTANT = "stringConstant"
IDENTIFIER = "identifier"
DOUBLE_QUOTES = "\""
CLASS_VAR_DEC = "classVarDec"
SUBROUTINE_DEC = "subroutineDec"
PARAMETER_LIST = "parameterList"
SUBROUTINE_BODY = "subroutineDec"
VAR_DEC = "varDec"
STATEMENTS = "statements"


class ParseException(Exception):
    pass


class Token(NamedTuple):
    type: str
    value: str
    line_number: int


class JackTokenizer:
    tokens_specifications = dict(
        comment=r"//.*|/\*.*\*/",
        space=r"[ \t]+",
        keyword="|".join([
            "class", "constructor", "function",
            "method", "field", "static", "var", "int",
            "char", "boolean", "void", "true", "false",
            "null", "this", "let", "do", "if", "else",
            "while", "return"
        ]),
        symbol="|".join([
            "\{", "\}", "\(", "\)", "\[", "\]", "\.",
            "\,", "\;", "\+", "\-", "\*", "\/", "\&",
            "\|", "\<", "\>", "\=", "\~",
        ]),
        integerConstant=r"\d+",
        stringConstant=r'\"[^"\n]+\"',  # unicode characters
        identifier=r"[a-zA-Z_]{1}[a-zA-Z0-9_]*",  # must be after keywords, in python re site, considered keyword as
        # part of ID pattern newline=r"\n",
        mismatch=r".",  # any other character
    )
    jack_token = re.compile("|".join([r"(?P<{}>{})".format(token, specification)
                                      for token, specification in tokens_specifications.items()]))

    def __init__(self, in_stream):
        self.in_stream = in_stream
        self._current_token = None

    def start_tokenizer(self):
        line_number = 0
        for line in self.in_stream:
            line = line.strip()
            line_number += 1
            for m in self.jack_token.finditer(line):
                token_type = m.lastgroup
                token_value = m.group(token_type)
                if token_type == "integerConstant":
                    token_value = int(token_value)
                # if token_type == "newline":
                #    line_number += 1
                if token_type == "comment" or token_type == "space":
                    continue
                elif token_type == "mismatch":
                    raise ParseException(
                        f"got wrong jack token: {token_value} in line {line_number}")
                else:
                    yield Token(token_type, token_value, line_number)

    """
    # I think won't be necessary 
    @property
    def current_token(self):
        return self._current_token
    def has_more_tokens(self):
        return False

    def token_type():
        return

    def keyword() -> str:
        return

    def symbol() -> str:
        return

    def identifier() -> str:
        return

    def int_val() -> int:
        return

    def str_val() -> str:
        return
    """


class CompilationEngine:
    special_xml = {
        LESS_THAN: "&lt;",
        GREATER_THAN: "&gt;",
        AMPERSAND: "&amp;",
        DOUBLE_QUOTES: "&quot;"
    }

    def __init__(self, tokens_stream, out_stream):
        """ initialize the compilation engine which parses tokens from tokensStream and write in outFileStream
        INVARIANT: current_token is the token we are handling now given _eat() is last to run in handling it
        Args:
            tokens_stream (Generator): Generator of jack tokens
            out_stream (stream): file to write parsed jack code into
        """
        self.tokens_stream = tokens_stream
        self.out_stream = out_stream
        self.current_token = None
        self.indent_level = 0

    def _write_tag_value(self, tag, value):
        """writes xml tagged jack token to outFileStream
        Args:
            tag (str): type of token
            value (str | integer): value of token
        """
        value = self.special_xml.get(value, value)
        indent = "\t" * self.indent_level  # followed the test files format (seems arbitrary though)
        self.out_stream.write(f"{indent}<{tag}> {value} </{tag}>{NEWLINE}")

    def _write_open_tag(self, tag):
        """writes xml open tag with given tag
        Args:
            tag (str): xml tag
        """
        indent = "\t" * self.indent_level
        self.out_stream.write(f"{indent}<{tag}>{NEWLINE}")

    def _write_close_tag(self, tag):
        """writes xml close tag with given tag
        Args:
            tag (str): xml tag
        """
        indent = "\t" * self.indent_level
        self.out_stream.write(f"{indent}</{tag}>{NEWLINE}")

    def _eat(self, s):
        """advance to next token if given string is same as the current token, otherwise raise error
        Args:
            s (str): string to match current token against
        Raises:
            ParseException: in case no match
        """
        if s == self.current_token.value or \
                (s == self.current_token.type and s in [INT_CONSTANT, STR_CONSTANT, IDENTIFIER]):
            try:
                self.current_token = next(self.tokens_stream)
            except StopIteration:
                if s != RIGHT_BRACE:  # last token
                    raise ParseException("Error, reached end of file")
        else:
            raise ParseException(
                f"Got wrong token on line {self.current_token.line_number}: {str(self.current_token)}, expected: {s!r}")

    def compile_class(self):
        """Starting point in compiling a jack source file
        """
        # first token
        try:
            self.current_token = self.current_token or next(self.tokens_stream)
        except StopIteration:  # jack source file is empty
            return

        # <class>
        self._write_open_tag(CLASS)
        self.indent_level += 1

        # class
        self._write_tag_value(KEYWORD, self.current_token.value)
        self._eat(CLASS)

        # className
        self._write_tag_value(IDENTIFIER, self.current_token.value)
        self._eat(IDENTIFIER)

        # {
        self._write_tag_value(SYMBOL, self.current_token.value)
        self._eat(LEFT_BRACE)

        # classVarDec*
        while self.current_token.value in [STATIC, FIELD]:
            self.compile_class_var_dec()

        # subroutineDec*
        while self.current_token.value in [CONSTRUCTOR, FUNCTION, METHOD]:
            self.compile_subroutine_dec()

        # }
        self._write_tag_value(SYMBOL, self.current_token.value)
        self._eat(RIGHT_BRACE)

        # </class>
        self.indent_level -= 1
        self._write_close_tag(CLASS)

    def compile_class_var_dec(self):
        """compile a jack class variable declarations
        ASSUME: only called if current token's value is static or field
        """
        # <classVarDec>
        self._write_open_tag(CLASS_VAR_DEC)
        self.indent_level += 1

        # field | static
        self._write_tag_value(KEYWORD, self.current_token.value)
        if self.current_token.value == STATIC:
            self._eat(STATIC)
        elif self.current_token.value == FIELD:
            self._eat(FIELD)

        self._handle_type_var_name()

        # </classVarDec>
        self.indent_level -= 1
        self._write_close_tag(CLASS_VAR_DEC)

    def _handle_type_var_name(self):
        # type
        if self.current_token.value in [INT, CHAR, BOOLEAN]:
            self._write_tag_value(KEYWORD, self.current_token.value)
            self._eat(self.current_token.value)
        elif self.current_token.type == IDENTIFIER:
            self._write_tag_value(IDENTIFIER, self.current_token.value)
            self._eat(self.current_token.value)

        # varName (, varName)*;
        while True:
            self._write_tag_value(IDENTIFIER, self.current_token.value)
            self._eat(IDENTIFIER)
            if self.current_token.value == SEMI_COLON:
                break
            self._write_tag_value(SYMBOL, COMMA)
            self._eat(COMMA)
        self._write_tag_value(SYMBOL, SEMI_COLON)
        self._eat(SEMI_COLON)

    def compile_subroutine_dec(self):
        """compile a jack class subroutine declarations
        ASSUME: only called if current token's value is constructor, function or method
        """
        # <subroutineDec>
        self._write_open_tag(SUBROUTINE_DEC)
        self.indent_level += 1

        # constructor | function | method
        self._write_tag_value(KEYWORD, self.current_token.value)
        if self.current_token.value == CONSTRUCTOR:
            self._eat(CONSTRUCTOR)
        elif self.current_token.value == FUNCTION:
            self._eat(FUNCTION)
        elif self.current_token.value == METHOD:
            self._eat(METHOD)

        # void | type
        if self.current_token.value in [VOID, INT, CHAR, BOOLEAN]:
            self._write_tag_value(KEYWORD, self.current_token.value)
            self._eat(self.current_token.value)
        elif self.current_token.type == IDENTIFIER:
            self._write_tag_value(IDENTIFIER, self.current_token.value)
            self._eat(self.current_token.value)

        # subroutineName
        self._write_tag_value(IDENTIFIER, self.current_token.value)
        self._eat(IDENTIFIER)

        # (
        self._write_tag_value(SYMBOL, self.current_token.value)
        self._eat(LEFT_PAREN)

        # parameterList
        self.compile_parameter_list()

        # )
        self._write_tag_value(SYMBOL, self.current_token.value)
        self._eat(RIGHT_PAREN)

        # {
        self._write_tag_value(SYMBOL, LEFT_BRACE)
        self._eat(LEFT_BRACE)

        # subroutineBody
        self.compile_subroutine_body()

        # }
        self._write_tag_value(SYMBOL, RIGHT_BRACE)
        self._eat(RIGHT_BRACE)

    def compile_parameter_list(self):
        """compile a jack parameter list which is 0 or more list
        """
        # <parameterList>
        self._write_open_tag(PARAMETER_LIST)
        self.indent_level += 1

        # ((type varName) (, type varName)*)?
        while True:
            if self.current_token.value in [INT, CHAR, BOOLEAN]:
                self._write_tag_value(KEYWORD, self.current_token.value)
                self._eat(self.current_token.value)
            elif self.current_token.type == IDENTIFIER:
                self._write_tag_value(IDENTIFIER, self.current_token.value)
                self._eat(self.current_token.value)
            else:
                break

            self._write_tag_value(IDENTIFIER, self.current_token.value)
            self._eat(IDENTIFIER)
            if not self.current_token.value == COMMA:
                break

        self.indent_level -= 1
        self._write_close_tag(PARAMETER_LIST)

    def compile_subroutine_body(self):
        """compile a jack subroutine body which is varDec* statements
        """
        # <subroutineBody>
        self._write_open_tag(SUBROUTINE_BODY)
        self.indent_level += 1

        while self.current_token.value == VAR:  # order matters, simplify
            self.compile_var_dec()

        while self.current_token.value in [LET, IF, WHILE, DO, RETURN]:
            self.compile_statements()

        # </subroutineBody>
        self.indent_level -= 1
        self._write_close_tag(SUBROUTINE_BODY)

    def compile_var_dec(self):
        """compile jack variable declaration, varDec*, only called if current token is var
        """
        # <varDec>
        self._write_open_tag(VAR_DEC)
        self.indent_level += 1

        # VAR
        self._write_tag_value(KEYWORD, self.current_token.value)
        self._eat(VAR)

        # type varName (',' varName)*;
        self._handle_type_var_name()

        # </varDec>
        self.indent_level -= 1
        self._write_close_tag(VAR_DEC)

    def compile_statements(self):
        """
        match the current token value to the matching jack statement
        """
        # <statements>
        self._write_open_tag(STATEMENTS)
        self.indent_level += 1

        {
            LET: self.compile_let_statement,
            IF: self.compile_if_statement,
            WHILE: self.compile_while_statement,
            DO: self.compile_do_statement,
            RETURN: self.compile_return_statement,
        }[self.current_token.value]()

        # </statements>
        self.indent_level -= 1
        self._write_close_tag(STATEMENTS)

    def compile_let_statement(self):
        """
        compile jack let statement
        """
        # <letStatement>
        self._write_open_tag(LET_STATEMENT)
        self.indent_level += 1

        # let - TODO: confirm its rule, not sure about it
        self._write_tag_value(KEYWORD, LET)
        self._eat(LET)

        # varName
        self._write_tag_value(IDENTIFIER, self.current_token.value)
        self._eat(self.current_token.value)

        # <letStatement>
        self.indent_level -= 1
        self._write_close_tag(LET_STATEMENT)

    def compile_if_statement(self):
        return

    def compile_while_statement(self):
        return

    def compile_do_statement(self):
        return

    def compile_return_statement(self):
        return

    def compile_expression(self):
        return

    def compile_term(self):
        return

    def compile_expression_list(self):
        return


if __name__ == "__main__":
    # if len(sys.argv) != 2:
    #     print("Usage: compiler.py <path-to-jack-file-or-directory-of-source-code>")
    #     sys.exit(1)
    # inFilePath = sys.argv[1]

    inFilePath = r"C:\Users\khalil\OneDrive - Deakin University\PhD " \
                 r"Project\Programming\CSDegree\019_020_NAND_TETRIS\projects\10\ArrayTest\Temp.jack "


    def handle_file(path):
        out_file_path = path.replace(IN_FILE_EXT, OUT_FILE_EXT)
        with open(path) as inFileStream:
            with open(out_file_path, "w") as outFileStream:
                tokens_stream = JackTokenizer(inFileStream).start_tokenizer()
                compilation_engine = CompilationEngine(tokens_stream, outFileStream)
                compilation_engine.compile_class()


    def handle_dir(path):
        for f in os.listdir():
            if f.endswith(IN_FILE_EXT):
                handle_file(path + NEWLINE + f)


    if os.path.isfile(inFilePath):
        handle_file(inFilePath)
    elif os.path.isdir(inFilePath):
        handle_dir(inFilePath)
    else:
        raise RuntimeError(
            "I/O Error, make sure to provide a valid file .jack or directory name that has .jack source code")
