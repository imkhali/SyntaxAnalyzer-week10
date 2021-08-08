import os
import re
import sys
from typing import NamedTuple

# TODO: refactor, one thing, see if _eat can be called before handling the lexical

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
SUBROUTINE_BODY = "subroutineBody"
VAR_DEC = "varDec"
STATEMENTS = "statements"
TERM = "term"
EXPRESSION = "expression"
EXPRESSION_LIST = "expressionList"
RETURN_STATEMENT = "returnStatement"
DO_STATEMENT = "doStatement"
WHILE_STATEMENT = "whileStatement"
IF_STATEMENT = "ifStatement"
LET_STATEMENT = "letStatement"


class ParseException(Exception):
    pass


class Token(NamedTuple):
    type: str
    value: str
    line_number: int
    line: str  # for debugging

    def __repr__(self):
        return f"{self.line!r}"

    def __str__(self):
        return self.__repr__()


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
                        f"got wrong jack token: {token_value} in line {line_number}\n{str(line)}")
                else:
                    yield Token(token_type, token_value, line_number, line)

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
                    raise ParseException(f"Error, reached end of file\n{str(self.current_token)}")
        else:
            raise ParseException(
                f"Got wrong token in line {self.current_token.line_number}: "
                f"{self.current_token.value}, expected: {s!r}\n{str(self.current_token)}")

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
            self._eat(IDENTIFIER)

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
            self._eat(IDENTIFIER)

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

        # subroutineBody
        self.compile_subroutine_body()

        # </subroutineDec>
        self.indent_level -= 1
        self._write_close_tag(SUBROUTINE_DEC)

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
                self._eat(IDENTIFIER)
            else:
                break

            self._write_tag_value(IDENTIFIER, self.current_token.value)
            self._eat(IDENTIFIER)
            if not self.current_token.value == COMMA:
                break
            self._write_tag_value(SYMBOL, COMMA)
            self._eat(COMMA)

        self.indent_level -= 1
        self._write_close_tag(PARAMETER_LIST)

    def compile_subroutine_body(self):
        """compile a jack subroutine body which is varDec* statements
        """
        # <subroutineBody>
        self._write_open_tag(SUBROUTINE_BODY)
        self.indent_level += 1

        # {
        self._write_tag_value(SYMBOL, LEFT_BRACE)
        self._eat(LEFT_BRACE)

        while self.current_token.value == VAR:  # order matters, simplify
            self.compile_var_dec()

        self.compile_statements()

        # }
        self._write_tag_value(SYMBOL, RIGHT_BRACE)
        self._eat(RIGHT_BRACE)

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

        while self.current_token.value in [LET, IF, WHILE, DO, RETURN]:
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
        self._eat(IDENTIFIER)

        # =
        self._write_tag_value(SYMBOL, EQUAL_SIGN)
        self._eat(EQUAL_SIGN)

        # expression
        self.compile_expression()

        # ;
        self._write_tag_value(SYMBOL, SEMI_COLON)
        self._eat(SEMI_COLON)

        # <letStatement>
        self.indent_level -= 1
        self._write_close_tag(LET_STATEMENT)

    def compile_if_statement(self):
        """
        compile jack if statement
        """

        # <ifStatement>
        self._write_open_tag(IF_STATEMENT)
        self.indent_level += 1

        # if
        self._write_tag_value(KEYWORD, IF)
        self._eat(IF)

        # (expression)
        self._handle_expr_or_expr_list_within_paren(self.compile_expression)

        # {statements}
        self._handle_statements_within_braces()

        if self.current_token.value == ELSE:
            self._write_tag_value(KEYWORD, ELSE)
            self._eat(ELSE)
            self._handle_statements_within_braces()

        # <ifStatement>
        self.indent_level -= 1
        self._write_close_tag(IF_STATEMENT)

    def _handle_expr_or_expr_list_within_paren(self, compile_function):
        # (
        self._write_tag_value(SYMBOL, self.current_token.value)
        self._eat(LEFT_PAREN)
        # compile_expression or compile_expression_list
        compile_function()
        # )
        self._write_tag_value(SYMBOL, self.current_token.value)
        self._eat(RIGHT_PAREN)

    def _handle_statements_within_braces(self):
        # {
        self._write_tag_value(SYMBOL, LEFT_BRACE)
        self._eat(LEFT_BRACE)
        # statements
        while self.current_token.value in [LET, IF, WHILE, DO, RETURN]:
            self.compile_statements()
        # }
        self._write_tag_value(SYMBOL, RIGHT_BRACE)
        self._eat(RIGHT_BRACE)

    def compile_while_statement(self):
        """
        compile jack while statement
        """

        # <whileStatement>
        self._write_open_tag(WHILE_STATEMENT)
        self.indent_level += 1

        # while
        self._write_tag_value(KEYWORD, WHILE)
        self._eat(WHILE)

        # (expression)
        self._handle_expr_or_expr_list_within_paren(self.compile_expression)

        # {statements}
        self._handle_statements_within_braces()

        # <whileStatement>
        self.indent_level -= 1
        self._write_close_tag(WHILE_STATEMENT)

    def compile_do_statement(self):
        """
        compile jack do statement
        """

        # <doStatement>
        self._write_open_tag(DO_STATEMENT)
        self.indent_level += 1

        # do
        self._write_tag_value(KEYWORD, DO)
        self._eat(DO)

        #  subroutineName | (className | varName)'.'subroutineName
        self._write_tag_value(IDENTIFIER, self.current_token.value)
        self._eat(IDENTIFIER)
        # check if '.'
        if self.current_token.value == DOT:
            self._write_tag_value(SYMBOL, DOT)
            self._eat(DOT)
            self._write_tag_value(IDENTIFIER, self.current_token.value)
            self._eat(IDENTIFIER)

        # (expressionList)
        self._handle_expr_or_expr_list_within_paren(self.compile_expression_list)

        # ;
        self._write_tag_value(SYMBOL, SEMI_COLON)
        self._eat(SEMI_COLON)

        # </doStatement>
        self.indent_level -= 1
        self._write_close_tag(DO_STATEMENT)

    def compile_return_statement(self):
        """
        compile jack return statement
        """
        # <returnStatement>
        self._write_open_tag(RETURN_STATEMENT)
        self.indent_level += 1

        # return
        self._write_tag_value(KEYWORD, RETURN)
        self._eat(RETURN)

        # expression?
        if self.current_token.value != SEMI_COLON:
            self.compile_expression()

        # ;
        self._write_tag_value(SYMBOL, SEMI_COLON)
        self._eat(SEMI_COLON)

        # </returnStatement>
        self.indent_level -= 1
        self._write_close_tag(RETURN_STATEMENT)

    def compile_expression(self):
        """
        compile jack expression
        """

        # <expression>
        self._write_open_tag(EXPRESSION)
        self.indent_level += 1

        # TODO
        self.compile_term()

        # </expression>
        self.indent_level -= 1
        self._write_close_tag(EXPRESSION)

    def compile_term(self):
        """
        compile jack term
        """

        # <term>
        self._write_open_tag(TERM)
        self.indent_level += 1

        # TODO
        self._write_tag_value(IDENTIFIER, self.current_token.value)
        self._eat(IDENTIFIER)

        # </term>
        self.indent_level -= 1
        self._write_close_tag(TERM)

    def compile_expression_list(self):
        """
        compile jack expression list
        """
        # TODO: confirm it needs ( and )

        # <expressionList>
        self._write_open_tag(EXPRESSION_LIST)
        self.indent_level += 1

        # (expression (',' expression)*)?
        if not self.current_token.value == RIGHT_PAREN:
            while True:
                self.compile_expression()
                if not self.current_token.value == COMMA:
                    break
                self._write_tag_value(SYMBOL, COMMA)
                self._eat(COMMA)

        # </expressionList>
        self.indent_level -= 1
        self._write_close_tag(EXPRESSION_LIST)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: SyntaxAnalyzer.py <path-to-jack-file-or-directory-of-source-code>")
        sys.exit(1)
    inFilePath = sys.argv[1]

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
