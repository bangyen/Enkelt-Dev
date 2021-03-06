# coding=utf-8

# Enkelt 4.2
# Copyright 2018, 2019, 2020 Edvard Busck-Nielsen
# This file is part of Enkelt.
#
#     Enkelt is free software: you can redistribute it and/or modify
#     it under the terms of the GNU General Public License as published by
#     the Free Software Foundation, either version 3 of the License, or
#     (at your option) any later version.
#
#     Enkelt is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     You should have received a copy of the GNU General Public License
#     along with Enkelt.  If not, see <https://www.gnu.org/licenses/>.

import sys
import re
import os
import collections
import urllib.request

# For the standard library
import math
import time
import datetime


# ####### #
# CLASSES #
# ####### #

class StandardLibrary:
    class matte:
        tak = math.ceil
        golv = math.floor
        fakultet = math.factorial
        sin = math.sin
        cos = math.cos
        tan = math.tan
        asin = math.asin
        acos = math.acos
        atan = math.atan
        potens = math.pow
        kvadratrot = math.sqrt
        log = math.log
        grader = math.degrees
        radianer = math.radians
        abs = abs

        @staticmethod
        def e(): return math.e

        @staticmethod
        def pi(): return math.pi

    class tid:
        epok = time.time
        tid = time.ctime
        datum = datetime.date
        nu = datetime.datetime.now
        idag = datetime.date.today


class ErrorClass:
    def __init__(self, error_msg):
        self.error = error_msg
        self.error_list = error_msg.split()
        self.errors = get_errors()

    def set_error(self, new_error_msg):
        self.error = new_error_msg

    def get_error_type(self):
        for part in self.errors:
            if 'Error' in part:
                return self.errors[part]
        return ''

    def get_error_message_data(self):
        if "module 'final_transpiled' has no attribute '__enkelt__'" in self.error:
            return 'IGNORED'

        from googletrans import Translator

        translator = Translator()

        error_type = self.get_error_type()

        if error_type == '':
            self.set_error(self.error.replace("Traceback (most recent call last):", ''))
            self.set_error(self.error.replace('File "tmp.py", ', ''))
            self.set_error(self.error.replace(", in <module>", ''))
            return translator.translate(self.error, dest='sv').text.replace('linje', 'rad').replace(
                'final_transpiled.py, ', '')
        else:
            # Get line number
            for index, item in enumerate(self.error_list):
                if 'line' in item and has_numbers(self.error_list[index + 1]):
                    line_index = index + 1
                    return error_type + " (vid rad " + str(int(self.error_list[line_index][:-1]) - 4) + ')'
            return error_type


# ############################################### #
# Modules Used When Executing The Transpiled Code #
# ############################################### #

def enkelt_print(data):
    print(translate_output_to_swedish(data))


def enkelt_input(prompt=''):
    tmp = input(prompt)

    try:
        tmp = int(tmp)
        return tmp
    except ValueError:
        try:
            tmp = float(tmp)
            return tmp
        except ValueError:
            return str(tmp)


# ############ #
# Main Methods #
# ############ #

def translate_output_to_swedish(data):
    if isinstance(data, collections.abc.KeysView):
        data = list(data)

    replace_dict = {
        "True": 'Sant',
        "False": 'Falskt',
        "<class 'float'>": 'decimaltal',
        "<class 'str'>": 'sträng',
        "<class 'int'>": 'heltal',
        "<class 'list'>": 'lista',
        "<class 'dict'>": 'lexikon',
        "<class 'bool'>": 'boolesk',
        "<class 'NoneType'>": 'inget',
        "<class 'Exception'>": 'Feltyp',
        "<class 'datetime.date'>": 'datum',
        "<class 'datetime.datetime'>": 'datum & tid',
        "<class 'range'>": 'område'
    }

    data = str(data)
    for key in replace_dict:
        data = data.replace(key, replace_dict[key])

    return data


def check_for_updates(version_nr):
    import json

    global repo_location

    url = repo_location + '/master/VERSION.json'

    response = urllib.request.urlopen(url)

    data_store = json.loads(response.read())

    if data_store['version'] > float(version_nr):
        print('Uppdatering tillgänglig! Du har version ' + str(
            version_nr) + ' men du kan uppdatera till Enkelt version ' + str(data_store['version']))


def get_functions_from_lexed_library_code(data, library_name):
    for token_index, _ in enumerate(data):
        if data[token_index][0] == 'USER_FUNCTION':
            data[token_index][1] = library_name + '.' + data[token_index][1]
            user_functions[-1] = library_name + '.' + user_functions[-1]

    return data


def transpile_library_code(library_code, library_name):
    global final
    global source_code
    global is_extension

    for line in library_code:
        if line != '\n':
            data = fix_up_code_line(line)
            data = lex(data)

            data = get_functions_from_lexed_library_code(data, library_name)

            if is_extension:
                source_code.append(line)
            else:
                parse(data, 0)

            if is_developer_mode:
                print('--DEV: transpile_library_code, line')
                print(line)
                print('--DEV: transpile_library_code, lexed line')
                print(data)

            final.append(''.join(source_code))
            final.append('\n')
            source_code = []


def get_import(file_or_code, is_file, library_name):
    global imported_libraries
    global source_code
    global final
    global user_functions

    imported_libraries.append(library_name)

    library_code = file_or_code

    if is_file:
        with open(file_or_code) as library_file:
            library_code = library_file.readlines()

    while '' in library_code:
        library_code.pop(library_code.index(''))

    transpile_library_code(library_code, library_name)


def load_library_from_remote(url, library_name):
    response = urllib.request.urlopen(url)
    library_code = response.read().decode('utf-8')

    library_code = library_code.split('\n')

    get_import(library_code, False, library_name)


def import_library(library_name):
    from urllib.error import HTTPError

    global enkelt_script_path
    global web_import_location

    # Checks if the library is user-made (i.e. local not remote).
    import_file = ''.join(enkelt_script_path.split('/')[:-1]) + '/' + library_name + '.e'

    if os.path.isfile(import_file):
        get_import(import_file, True, library_name)
        return

    # The library might be a local extension (.epy file)
    import_file += 'py'
    if os.path.isfile(import_file):
        get_import(import_file, True, library_name)

    # The library might be remote (i.e. needs to be fetched)
    else:
        url = web_import_location + library_name + '.e'

        try:
            load_library_from_remote(url, library_name)
        except HTTPError:
            # The library might be a remote extension (.epy file)
            url += 'py'

            try:
                load_library_from_remote(url, library_name)
            except HTTPError:
                print('Det inträffade ett fel!! Kunde inte importera ' + library_name)


def translate_clear():
    if os.name == 'nt':
        return 'cls'
    return 'clear'


def has_numbers(input_string):
    return any(char.isdigit() for char in input_string)


def get_errors():
    return {
        'SyntaxError': 'Syntaxfel',
        'IndexError': 'Indexfel',
        'TypeError': 'Typfel',
        'ValueError': 'Värdefel',
        'NameError': 'Namnfel',
        'ZeroDivisionError': 'Nolldelningsfel',
        'AttributeError': 'Attributfel'
    }


def functions_keywords_and_obj_notations():
    return {
        'functions': {
            # Functions with no statuses in parse()
            'skriv': 'print',
            'in': 'input',
            'Sträng': 'str',
            'Heltal': 'int',
            'Decimal': 'float',
            'Bool': 'bool',
            'längd': 'len',
            'till': 'append',
            'bort': 'pop',
            'sortera': 'sorted',
            'slump': '__import__("random").randint',
            'slumpval': '__import__("random").choice',
            'blanda': '__import__("random").shuffle',
            'området': 'range',
            'lista': 'list',
            'ärnum': 'isdigit',
            'runda': 'round',
            'versal': 'upper',
            'gemen': 'lower',
            'ärversal': 'isupper',
            'ärgemen': 'islower',
            'ersätt': 'replace',
            'infoga': 'insert',
            'index': 'index',
            'dela': 'split',
            'foga': 'join',
            'typ': 'type',
            'läs': 'read',
            'överför': 'write',
            'veckodag': 'weekday',
            'värden': 'values',
            'element': 'elements',
            'numrera': 'enumerate',
            'töm': 'os.system("' + translate_clear() + '"',
            'kasta': 'raise Exception',
            'nycklar': 'keys',
            # Functions with statuses in parse()
            'om': 'if',
            'anom': 'elif',
            'öppna': 'with open',
            'för': 'for',
            'medan': 'while',
        },
        'keywords': {
            'Sant': 'True',
            'Falskt': 'False',
            'inom': 'in ',
            'bryt': 'break',
            'fortsätt': 'continue',
            'returnera': 'return ',
            'passera': 'pass',
            'år': 'year',
            'månad': 'month',
            'dag': 'day',
            'timme': 'hour',
            'minut': 'minute',
            'sekund': 'second',
            'mikrosekund': 'microsecond',
            'global': 'global ',
            'om': ' if ',
            'annars': ' else '
        },
        'obj_notations': {
            'klass': 'class ',
            'försök': 'try',
            'fånga': 'except Exception as ',
            'slutligen': 'finally'
        }
    }


def get_obj_notations():
    return ['klass', 'försök', 'fånga']


def translate_operator(operator):
    operator_translations = {
        '&': ' and ',
        '|': ' or ',
        '!': 'not ',
        'not': '!',  # this is needed for != expressions
    }

    return operator_translations[operator]


def operator_symbols():
    return ['+', '-', '*', '/', '%', '<', '>', '=', '!', '.', ',', ')', ':', ';', '&', '|']


def forbidden_variable_names():
    return ['in', 'själv']


def translate_function(func):
    function_translations = functions_keywords_and_obj_notations()['functions']

    return function_translations[func] if func in function_translations.keys() else 'error'


def transpile_function(func):
    global source_code

    source_code.append(translate_function(func) + '(')


def translate_obj_notation(obj_notation):
    obj_notation_translations = functions_keywords_and_obj_notations()['obj_notations']

    return obj_notation_translations[obj_notation] if obj_notation in obj_notation_translations.keys() else 'error'


def translate_keyword(keyword):
    keyword_translations = functions_keywords_and_obj_notations()['keywords']

    return keyword_translations[keyword] if keyword in keyword_translations.keys() else 'error'


def transpile_keyword(keyword):
    global source_code

    source_code.append(translate_keyword(keyword))


# Parses the code tree and transpiles to python.
def parse(lexed, token_index):
    global source_code
    global indent_layers
    global is_if
    global is_math
    global is_for
    global look_for_loop_ending
    global needs_start_statuses
    global is_file_open
    global is_extension
    global lambda_num

    global standard_library

    forbidden = forbidden_variable_names()

    global is_console_mode

    is_comment = False

    token_type = str(lexed[token_index][0])
    token_val = lexed[token_index][1]

    needs_start = needs_start_statuses[-1]

    if indent_layers and token_index == 0:
        for _ in indent_layers:
            source_code.append('\t')
    if token_type == 'COMMENT':
        source_code.append(token_val)
        is_comment = True
    elif token_type == 'FUNCTION':
        # Specific functions & function cases that ex. required updating of statuses.
        if token_val == 'skriv' or token_val == 'in':
            tmp = ''
            if not is_console_mode:
                tmp = 'Enkelt.enkelt_'
            source_code.append(tmp + 'print(' if token_val == 'skriv' else tmp + 'input(')
        elif token_val == 'om' or token_val == 'anom':
            source_code.append(translate_function(token_val) + ' ')
            is_if = True
        elif token_val == 'öppna':
            transpile_function(token_val)
            needs_start_statuses.append(True)
            is_file_open = True
        elif token_val == 'för' or token_val == 'medan':
            source_code.append(translate_function(token_val) + ' ')
            look_for_loop_ending = True
            if token_val == 'för':
                is_for = True
        elif token_val == 'töm':
            source_code.append(translate_function(token_val))
        # Every other function get's transpiled in the same way.
        else:
            transpile_function(token_val)
    elif token_type == 'VAR':
        if token_val not in forbidden:
            source_code.append(token_val)
        elif token_val == 'själv':
            source_code.append('self')
        else:
            print('Det inträffade ett fel! namnet ' + token_val + " är inte tillåtet som variabelnamn!")
    elif token_type == 'STRING':
        if is_file_open and len(token_val) <= 2:
            token_val = token_val.replace('l', 'r').replace('ö', 'w')
        source_code.append('"' + token_val + '"')
    elif token_type == 'PNUMBER' or token_type == 'NNUMBER':
        source_code.append(token_val)
    elif token_type == 'IMPORT' or token_type == 'EXTENSION':
        if token_type == 'EXTENSION':
            is_extension = True
        import_library(token_val)
    elif token_type == 'OPERATOR':
        # Special operator cases
        if is_if and token_val == ')':
            is_if = False
            needs_start_statuses.append(True)
        elif is_math and token_val == ')':
            is_math = False
        elif look_for_loop_ending and token_val == ')':
            look_for_loop_ending = False
            needs_start_statuses.append(True)
        elif token_val == '>' and lexed[token_index-1][1] == '=' and lexed[token_index+1][0] == 'USER_FUNCTION_CALL':
            lambda_num += 1
            if lexed[token_index-2][0] != 'VAR':
                source_code = source_code[:-1]
            source_code.append('lambda ')
        elif lambda_num and token_val == ')':
            source_code.append(': ')
        elif token_val in ['&', '|', '!']:
            to_translate = token_val

            # Checks if the ! is part of a != expression
            if token_val == '!' and token_index+1 < len(lexed):
                if lexed[token_index+1][1] == '=':
                    to_translate = 'not'

            source_code.append(translate_operator(to_translate))
        # All other operators just gets appended to the source
        else:
            source_code.append(token_val)
    elif token_type == 'LIST_START' or token_type == 'LIST_END':
        source_code.append(token_val)
    elif token_type == 'START':
        if not lambda_num:
            if not needs_start:
                source_code.append(token_val)
            elif len(lexed) - 1 == token_index:
                source_code.append(':')
            else:
                source_code.append(':' + '\n')
            if needs_start:
                indent_layers.append("x")
    elif token_type == 'END':
        if lambda_num:
            lambda_num -= 1
        elif not needs_start:
            source_code.append(token_val)
        else:
            needs_start_statuses.pop(-1)
            indent_layers.pop(-1)
            if len(lexed) - 1 != token_index:
                source_code.append('\n')
                for _ in indent_layers:
                    source_code.append('\t')
    elif token_type == 'KEYWORD' or token_type == 'BOOL':
        # Specific keywords & keyword cases that ex. required updating of statuses.
        if token_val == 'annars':
            source_code.append(translate_keyword(token_val))
            needs_start_statuses.append(True)
        # Every other keyword get's transpiled in the same way.
        else:
            transpile_keyword(token_val)
    elif token_type == 'USER_FUNCTION':
        # Needed when functions are imported functions
        token_val = token_val.replace('.', '__enkelt__')
        source_code.append('def ' + token_val + '(')
        needs_start_statuses.append(True)
    elif token_type == 'USER_FUNCTION_CALL' and not lambda_num:
        if '.' in token_val:
            if token_val.split('.')[0] in standard_library:
                # The function is part of the standard library
                library = token_val.split('.')[0]
                rest = ''.join(token_val.split('.')[1:])

                token_val = 'Enkelt.StandardLibrary.' + library + '.' + rest
            else:
                # Function is an imported functions
                token_val = token_val.replace('.', '__enkelt__')
        source_code.append(token_val + '(')
    elif token_type == 'OBJ_NOTATION':
        source_code.append(translate_obj_notation(token_val))
        needs_start_statuses.append(True)
    elif token_type == 'OBJ_NOTATION_PARAM':
        source_code.append(' ' + token_val)
        needs_start_statuses.append(True)
    elif token_type == 'LAMBDA_CALL':
        source_code.append(token_val)

    # Recursively calls parse() when there is more code to parse
    if len(lexed) - 1 >= token_index + 1 and not is_comment:
        parse(lexed, token_index + 1)


def lex(line):
    if line[0] == '#':
        return ['COMMENT', line]

    global user_functions
    global imported_libraries
    global standard_library

    operators = operator_symbols()
    obj_notations = get_obj_notations()

    tmp_data = ''
    is_string = False
    is_var = False
    is_function = False
    is_obj_notation = False
    is_import = False
    is_extension_mode = False
    lexed_data = []
    last_action = ''
    might_be_negative_num = False
    data_index = -1
    op_dict = {
        '=': 'OPERATOR',
        '[': 'LIST_START',
        ']': 'LIST_END',
        '{': 'START',
        '}': 'END',
        '(': 'LAMBDA_CALL'
    }
    op_dict.update({key:'OPERATOR' for key in operators})

    for chr_index, char in enumerate(line):
        if is_import and char != ' ':
            tmp_data += char
        if is_import and chr_index == len(line) - 1:
            lexed_data.append(['IMPORT' if not is_extension_mode else 'EXTENSION', tmp_data])
            is_import = False
            is_extension_mode = False
            tmp_data = ''
        if is_function and char not in operators and char != '(':
            tmp_data += char
        elif is_function and char == '(':
            lexed_data.append(['USER_FUNCTION', tmp_data])
            user_functions.append(tmp_data)
            tmp_data = ''
            is_function = False
        elif char == '{' and not is_var:
            if is_obj_notation:
                lexed_data.append(['OBJ_NOTATION_PARAM', tmp_data])
                tmp_data = ''
                is_obj_notation = False
            lexed_data.append(['START', char])
        elif char == '}' and not is_var:
            lexed_data.append(['END', char])
        elif char == '#' and not is_string:
            break
        elif char.isdigit() and not is_string and not is_var:
            if might_be_negative_num or last_action == 'NNUMBER':
                if last_action == 'NNUMBER':
                    lexed_data[data_index - 1] = ['NNUMBER', lexed_data[data_index - 1][1] + char]
                else:
                    lexed_data.append(['NNUMBER', '-' + char])
                    data_index += 1
                last_action = 'NNUMBER'
                might_be_negative_num = False
            else:
                if last_action == 'PNUMBER':
                    lexed_data[-1] = ['PNUMBER', lexed_data[-1][1] + char]
                else:
                    lexed_data.append(['PNUMBER', char])
                    data_index += 1

                last_action = 'PNUMBER'
        elif char == '-' and not is_string and not is_var:
            might_be_negative_num = True
        else:
            last_action = ''
            if char == '"' and not is_string:
                is_string = True
                tmp_data = ''
            elif char == '"' and is_string:
                is_string = False
                lexed_data.append(['STRING', tmp_data])
                tmp_data = ''
            elif is_string:
                tmp_data += char
            else:
                if char == '[' and not is_var:
                    lexed_data.append(['LIST_START', '['])
                elif char == ']' and not is_var:
                    lexed_data.append(['LIST_END', ']'])
                else:
                    if char == '$':
                        is_var = True
                        tmp_data = ''
                    elif is_var:
                        if char in operators + list(' =[]{}('):
                            is_var = False
                            lexed_data.append(['VAR', tmp_data])
                            if char != ';':
                                lexed_data.append([op_dict[char], char])
                            else:
                                lexed_data[-1][-1] = tmp_data + ' '
                            tmp_data = ''
                        else:
                            tmp_data += char
                            if len(line) - 1 == chr_index:
                                is_var = False
                                lexed_data.append(['VAR', tmp_data])
                                tmp_data = ''
                    elif char in operators and tmp_data not in imported_libraries and tmp_data not in standard_library:
                        lexed_data.append(['OPERATOR', char])
                    elif char in imported_libraries or char in standard_library and char != '.':
                        lexed_data.append(['OPERATOR', char])
                    elif char in imported_libraries or char in standard_library and char == '.':
                        tmp_data += char
                    else:
                        if tmp_data == 'Sant' or tmp_data == 'Falskt':
                            lexed_data.append(['BOOL', tmp_data])
                            tmp_data = ''
                        else:
                            if char == '(' and translate_function(tmp_data) != 'error':
                                lexed_data.append(['FUNCTION', tmp_data])
                                tmp_data = ''
                            elif char == '(' and tmp_data in user_functions or char == '(' and translate_function(
                                    tmp_data) == 'error':
                                lexed_data.append(['USER_FUNCTION_CALL', tmp_data])
                                tmp_data = ''
                            else:
                                if not is_import:
                                    tmp_data += char
                                if tmp_data == 'Sant' or tmp_data == 'Falskt':
                                    lexed_data.append(['BOOL', tmp_data])
                                    tmp_data = ''
                                else:
                                    if translate_keyword(tmp_data) != 'error':
                                        lexed_data.append(['KEYWORD', tmp_data])
                                        tmp_data = ''
                                    elif tmp_data == 'def':
                                        is_function = True
                                        tmp_data = ''
                                    elif tmp_data == 'importera' or tmp_data == 'utöka':
                                        is_import = True
                                        is_extension_mode = True if (tmp_data == 'utöka') else False
                                        tmp_data = ''
                                    elif tmp_data in obj_notations:
                                        lexed_data.append(['OBJ_NOTATION', tmp_data])
                                        tmp_data = ''
                                        is_obj_notation = True

    return lexed_data


def fix_up_code_line(statement):
    global is_extension

    statement = statement.replace('\n', '')\
                         .replace("'", '"')\
                         .replace('\\"', '|-ENKELT_ESCAPED_QUOTE-|')\
                         .replace('\\', '|-ENKELT_ESCAPED_BACKSLASH-|')
    if not is_extension:
        statement = statement.replace('\t', '')

    current_line = ''
    is_string = False
    is_import = False

    for char in statement:
        if char == ' ' and not is_string and not is_import:
            continue
        elif char == '"':
            is_string = not is_string
        current_line += char

        if current_line == 'importera':
            is_import = True

    return current_line


def fix_up_and_prepare_transpiled_code():
    global final

    # Removes unnecessary tabs
    for line_index, line in enumerate(final):
        tmp_line = list(line)
        chars_started = False
        for char_index, char in enumerate(tmp_line):
            if char != '\t' and char != '\n' and not chars_started:
                chars_started = True
            elif chars_started and char == '\t' and char_index > 0:
                tmp_line[char_index] = ' '

        final[line_index] = ''.join(tmp_line)

    # Turn = = into == and ! = into != and + = into +=
    final = list(''.join(final).replace('= =', '==').replace('! =', '==').replace('+ =', '+='))

    # Fixes escaped (\) characters
    final = list(
        ''.join(final).replace('|-ENKELT_ESCAPED_QUOTE-|', '\\"').replace('|-ENKELT_ESCAPED_BACKSLASH-|', '\\')
    )

    # Remove empty lines from final
    final = list(re.sub(r'\n\s*\n', '\n\n', ''.join(final)))

    code = ''.join(final)

    return code


def run_transpiled_code():
    global final
    global is_developer_mode
    global is_console_mode

    if not is_console_mode:
        # Inserts necessary code to make importing a temporary python file work.
        code_to_append = """import enkelt as Enkelt\ndef __enkelt__():\n\tprint('', end='')\n"""
        final.insert(0, code_to_append)

    code = fix_up_and_prepare_transpiled_code()

    if is_developer_mode:
        print('--DEV: run_transpiled_code, final code')
        print(code)

    if not is_console_mode:
        # Writes the transpiled code to a file temporarily.
        with open('final_transpiled.py', 'w+', encoding='utf-8') as transpiled_f:
            transpiled_f.writelines(code)

    # Executes the code transpiled to python and catches Exceptions
    try:
        # The "main" way of executing the transpiled code
        if not is_console_mode:
            # This line will show an error;
            # it's importing a temporary file that get's created (and deleted) by this script.
            import final_transpiled
            final_transpiled.__enkelt__()
        # The "fallback"/console execution process.
        else:
            exec(code)
    except Exception as err:
        if is_developer_mode:
            if str(err) != 'module \'final_transpiled\' has no attribute \'__enkelt__\'':
                print('--DEV: run_final_transpiled_code, error')
                print(err)

        # Print out error(s) if any
        error = ErrorClass(str(err).replace('(<string>, ', '('))
        if error.get_error_message_data() != 'IGNORED':
            print(error.get_error_message_data())

    if not is_console_mode:
        # Removes the temporary python file.
        with open('final_transpiled.py', 'w+', encoding='utf-8') as transpiled_f:
            transpiled_f.writelines('')
        os.remove(os.getcwd() + '/final_transpiled.py')


def transpile_line(line):
    global source_code
    global is_developer_mode
    global final

    if line != '\n':
        if is_developer_mode:
            print('--DEV: transpile_line, line')
            print(line)

        data = fix_up_code_line(line)
        data = lex(data)

        if is_developer_mode:
            print('--DEV: transpile_line, lexed line')
            print(data)

        parse(data, 0)

        # Appends the transpiled code to the final source code
        final.append(''.join(source_code))
        final.append('\n')
        source_code = []


def prepare_and_run_code_lines_to_be_run(code):
    global final
    global variables

    # Removes empty lines
    while '' in code:
        code.pop(code.index(''))

    # Inserts previously saved variables into the transpiled code (used in the console mode)
    if variables:
        for var in variables[::-1]:
            final.insert(0, var + '\n')

    # Runs the code line by line
    for line_to_run in code:
        transpile_line(line_to_run)

    run_transpiled_code()


def console_mode(first):
    global version
    global variables
    global source_code
    global final
    global is_console_mode

    is_console_mode = True

    if first:  # is first console run -> shows copyright & license info.
        check_for_updates(version)
        print('Enkelt v' + str(version) + ' © 2018-2019-2020 Edvard Busck-Nielsen' + ". GNU GPL v.3")
        print('Skriv "x" eller tryck Ctrl+C för att avsluta')

    code_line = input('Enkelt >>> ')

    if code_line != '' and code_line != 'x':
        tmp_lexed_code_line_to_test_if_var = fix_up_code_line(code_line)
        tmp_lexed_code_line_to_test_if_var = lex(tmp_lexed_code_line_to_test_if_var)

        # Makes sure that the line is a "normal" code line, i.e. not the clear command and not a variable declaration.
        if code_line.replace(' (', '(') != 'töm()' and tmp_lexed_code_line_to_test_if_var[0][0] != 'VAR':
            prepare_and_run_code_lines_to_be_run([code_line])

        # Clear command was issued
        elif code_line.replace(' (', '(') == 'töm()':
            os.system(translate_clear())

        # A variable was declared
        else:
            parse(tmp_lexed_code_line_to_test_if_var, 0)
            variables.append(''.join(source_code))

    if code_line == 'x':
        return

    # Calling the console, recursively
    source_code = []
    final = []
    console_mode(False)


# ----- SETUP GLOBAL VARIABLES -----

is_list = False
is_if = False
is_math = False
is_for = False
look_for_loop_ending = False
needs_start_statuses = [False]
is_file_open = False
is_extension = False
lambda_num = 0

is_console_mode = False

source_code = []
indent_layers = []
imported_libraries = []
standard_library = ['matte', 'tid']
user_functions = []

# When user/dev tests
is_developer_mode = False
# Gets an env. variable to check if it's a circle-ci test run.
is_dev = os.getenv('ENKELT_DEV', False)

version = 4.1
repo_location = 'https://raw.githubusercontent.com/Enkelt/Enkelt/'
web_import_location = 'https://raw.githubusercontent.com/Enkelt/EnkeltWeb/master/bibliotek/bib/'

final = []
variables = []

enkelt_script_path = ''

# ----- START -----
if not is_dev:
    try:
        if sys.version_info[0] < 3:
            raise Exception("Du måste använda Python 3 eller högre")

        # Checks if code is being provided from an enkelt script or if it's a console/repl mode launch
        if len(sys.argv) >= 2:
            if '.e' in sys.argv[1]:
                enkelt_script_path = sys.argv[1]

            # Checks if enkelt is being run in developer mode (--d flag)
            if len(sys.argv) >= 3:
                if sys.argv[2] == '--d':
                    is_developer_mode = True

            if os.path.isfile(os.getcwd() + '/' + enkelt_script_path):
                with open(enkelt_script_path, encoding='utf-8') as f:
                    tmp_code_to_run = f.readlines()

                prepare_and_run_code_lines_to_be_run(tmp_code_to_run)
            else:
                print('Filen ' + enkelt_script_path + ' kunde inte hittas!')

            check_for_updates(version)
        else:
            # Starts console/repl mode
            variables = []
            final = []
            console_mode(True)
    except Exception as e:
        print(e)
