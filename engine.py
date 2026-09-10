"""Bounded sequential interpreter. Student programs never enter eval or exec."""
import ast
from dataclasses import dataclass
from decimal import Decimal
import json
import math
import re
import struct

LANGUAGES = ('Python', 'JavaScript', 'C', 'Java')
TYPES = ('int', 'float', 'string', 'bool')
MAX_CODE = 8000
READS = {'leggi_intero': 'int', 'leggi_decimale': 'float', 'leggi_testo': 'string', 'leggi_booleano': 'bool'}


class CodeError(Exception):
    def __init__(self, message, line=1, static=False):
        super().__init__(message)
        self.line, self.static = line, static


@dataclass(frozen=True)
class Value:
    kind: str
    data: object
    bits: int = 0


def f32(number):
    try:
        return struct.unpack('f', struct.pack('f', number))[0]
    except (OverflowError, struct.error):
        raise CodeError('Il numero è troppo grande per questo laboratorio.')


def value(raw, bits=64):
    kind = {bool: 'bool', int: 'int', float: 'float', str: 'string'}.get(type(raw))
    if kind is None:
        raise CodeError('Questo tipo di dato non è previsto nel laboratorio.')
    if kind in ('int', 'float') and (abs(raw) > 10000000 or not math.isfinite(raw)):
        raise CodeError('Usa numeri finiti tra -10000000 e 10000000: è un limite del laboratorio.')
    if kind == 'string' and len(raw) > 200:
        raise CodeError('Qui i testi possono contenere al massimo 200 caratteri.')
    return Value(kind, f32(raw) if kind == 'float' and bits == 32 else raw, bits if kind == 'float' else 0)


def type_name(item, language):
    if language == 'JavaScript' and item.kind in ('int', 'float'):
        return 'number'
    return {'Python': {'string': 'str'}, 'JavaScript': {'bool': 'boolean'}, 'C': {'string': 'const char *'},
            'Java': {'string': 'String', 'bool': 'boolean', 'float': 'float' if item.bits == 32 else 'double'}}.get(language, {}).get(item.kind, item.kind)


def display(item, language='Python', quoted=True):
    if item.kind == 'string':
        return json.dumps(item.data, ensure_ascii=False) if quoted else item.data
    if item.kind == 'bool':
        return str(item.data) if language == 'Python' else str(item.data).lower()
    if item.kind == 'float':
        result = repr(item.data)
        if language == 'JavaScript':
            if item.data.is_integer():
                return str(int(item.data))
            if abs(item.data) >= .000001:
                return format(Decimal(result), 'f')
            return result.replace('e-0', 'e-').replace('e+0', 'e+')
        if item.bits == 32:
            for digits in range(1, 10):
                candidate = format(item.data, f'.{digits}g')
                if f32(float(candidate)) == item.data:
                    result = candidate
                    break
        if '.' not in result and 'e' not in result.lower():
            result += '.0'
        return result
    return str(item.data)


def literal(raw, language='Python', float_bits=32):
    item = raw if isinstance(raw, Value) else value(raw)
    result = display(item, language)
    if item.kind == 'float' and language in ('C', 'Java') and float_bits == 32:
        result += 'f'
    return result


@dataclass(frozen=True)
class Instruction:
    target: str
    expression: str
    kind: str = ''
    line: int = 1
    tree: object = None
    constant: bool = False


def set_var(name, kind, expression):
    return Instruction(name, expression, kind)


def assign(name, expression):
    return Instruction(name, expression)


def output(expression):
    return Instruction('', expression)


def expression_source(source, language):
    """Authored expressions use Python syntax and three conversion names."""
    tree = ast.parse(source, mode='eval').body
    def render(node):
        if isinstance(node, ast.Constant):
            return literal(node.value, language)
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.UnaryOp):
            return ('not ' if language == 'Python' else '!') + '(' + render(node.operand) + ')' if isinstance(node.op, ast.Not) else '-' + '(' + render(node.operand) + ')'
        if isinstance(node, ast.BinOp):
            symbol = {ast.Add: '+', ast.Sub: '-', ast.Mult: '*', ast.Div: '/'}[type(node.op)]
            return '(' + render(node.left) + ' ' + symbol + ' ' + render(node.right) + ')'
        if isinstance(node, ast.Compare):
            symbol = {ast.Lt: '<', ast.LtE: '<=', ast.Gt: '>', ast.GtE: '>=', ast.Eq: '==', ast.NotEq: '!='}[type(node.ops[0])]
            return render(node.left) + ' ' + symbol + ' ' + render(node.comparators[0])
        if isinstance(node, ast.BoolOp):
            symbol = (' and ' if language == 'Python' else ' && ') if isinstance(node.op, ast.And) else (' or ' if language == 'Python' else ' || ')
            return '(' + symbol.join(render(child) for child in node.values) + ')'
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            name, args = node.func.id, [render(arg) for arg in node.args]
            if name in READS:
                return name + '()'
            if name == 'unisci':
                return 'unisci(' + ', '.join(args) + ')' if language == 'C' else '(' + ' + '.join(args) + ')'
            if name == 'float':
                return f'(float)({args[0]})' if language in ('C', 'Java') else ('float' if language == 'Python' else 'Number') + '(' + args[0] + ')'
            if name == 'int':
                return {'Python': 'int(' + args[0] + ')', 'JavaScript': 'parseInt(' + args[0] + ', 10)', 'C': 'atoi(' + args[0] + ')', 'Java': 'Integer.parseInt(' + args[0] + ')'}[language]
            if name == 'str':
                return {'Python': 'str', 'JavaScript': 'String', 'C': 'testo', 'Java': 'String.valueOf'}[language] + '(' + args[0] + ')'
        raise ValueError('Espressione del contenuto non supportata: ' + source)
    return render(tree)


def source_line(instruction, language):
    expression = expression_source(instruction.expression, language)
    if not instruction.target:
        command = {'Python': 'print', 'JavaScript': 'console.log', 'C': 'mostra', 'Java': 'System.out.println'}[language]
        return command + '(' + expression + ')' + ('' if language == 'Python' else ';')
    prefix = ''
    if instruction.kind and language == 'JavaScript':
        prefix = 'let '
    elif instruction.kind and language in ('C', 'Java'):
        prefix = {'string': 'const char *' if language == 'C' else 'String ', 'bool': 'bool ' if language == 'C' else 'boolean '}.get(instruction.kind, instruction.kind + ' ')
    return prefix + instruction.target + ' = ' + expression + ('' if language == 'Python' else ';')


def generate(instructions, language):
    return '\n'.join(source_line(item, language) for item in instructions) + '\n'


TOKEN = re.compile(r'\s+|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|(?:\d+\.\d*|\.\d+|\d+)(?:[eE][+-]?\d+)?[fF]?|[A-Za-z_][A-Za-z_0-9]*(?:\.[A-Za-z_][A-Za-z_0-9]*)*|&&|\|\||==|!=|<=|>=|[()+*/<>,!\-]')


def expression_tree(expression, language, line):
    tokens, pos = [], 0
    while pos < len(expression):
        match = TOKEN.match(expression, pos)
        if not match:
            raise CodeError('Simbolo non previsto. Usa valori, variabili, calcoli e conversioni della scheda Comandi.', line)
        token = match.group()
        if not token.isspace():
            if token.startswith("'") and language in ('C', 'Java'):
                raise CodeError('Per una stringa usa le virgolette doppie. Il tipo char non fa parte di queste sfide.', line, True)
            tokens.append(token)
        pos = match.end()
    if language in ('C', 'Java'):
        i = 0
        while i + 3 < len(tokens):
            if tokens[i] == '(' and tokens[i + 1] in ('int', 'float') and tokens[i + 2] == ')':
                name = 'cast_' + tokens[i + 1]
                if tokens[i + 3] == '(':
                    tokens[i:i + 3] = [name]
                else:
                    end = i + 4 + (tokens[i + 3] == '-')
                    tokens[i:end] = [name, '('] + tokens[i + 3:end] + [')']
            i += 1
    if language != 'Python':
        # ! binds to its operand before arithmetic/comparisons in these languages.
        def unary_operand_end(index):
            if index >= len(tokens):
                raise CodeError('Manca il valore da negare.', line)
            if tokens[index] in ('!', '-', '+'):
                return unary_operand_end(index + 1)
            if tokens[index] == '(':
                depth = 1
                end = index + 1
                while end < len(tokens) and depth:
                    depth += (tokens[end] == '(') - (tokens[end] == ')')
                    end += 1
                return end
            if index + 1 < len(tokens) and tokens[index + 1] == '(':
                return unary_operand_end(index + 1)
            return index + 1
        for i in range(len(tokens) - 1, -1, -1):
            if tokens[i] == '!':
                end = unary_operand_end(i + 1)
                tokens[i:end] = ['logical_not', '('] + tokens[i + 1:end] + [')']
        if any(token in ('and', 'or', 'not', 'True', 'False') for token in tokens):
            raise CodeError('Qui usa &&, ||, ! e true/false: and, or, not e True/False appartengono a Python.', line, True)
    normalized = []
    names = {'true': 'True', 'false': 'False', '&&': 'and', '||': 'or', '!': 'not',
             'Integer.parseInt': 'java_int', 'String.valueOf': 'str', 'String': 'str', 'testo': 'str', 'Number': 'number'}
    for token_index, token in enumerate(tokens):
        if language != 'Python' and re.fullmatch(r'(?:\d+\.\d*|\.\d+|\d+)(?:[eE][+-]?\d+)?[fF]', token):
            if language == 'JavaScript':
                raise CodeError('JavaScript non usa il suffisso f.', line)
            normalized.extend(['as_float32', '(', token[:-1], ')'])
        else:
            convert = token in ('true', 'false', '&&', '||', '!') or (token_index + 1 < len(tokens) and tokens[token_index + 1] == '(')
            normalized.append(names.get(token, token) if language != 'Python' and convert else token)
    try:
        tree = ast.parse(' '.join(normalized).strip(), mode='eval').body
    except (SyntaxError, ValueError, RecursionError):
        raise CodeError('Controlla l’espressione: parentesi, operatore e virgolette. Per i decimali usa il punto.', line)
    allowed = (ast.Constant, ast.Name, ast.Load, ast.BinOp, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.UnaryOp, ast.USub, ast.UAdd, ast.Not,
               ast.Compare, ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.BoolOp, ast.And, ast.Or, ast.Call)
    nodes = list(ast.walk(tree))
    if len(nodes) > 100:
        raise CodeError('Semplifica questa espressione.', line)
    for node in nodes:
        if not isinstance(node, allowed):
            raise CodeError('Costrutto non previsto: qui lavoriamo su singoli dati e istruzioni sequenziali.', line)
        if isinstance(node, ast.Call) and (not isinstance(node.func, ast.Name) or node.keywords):
            raise CodeError('Usa soltanto le funzioni elencate nella scheda Comandi.', line)
        if isinstance(node, ast.Compare) and len(node.ops) != 1:
            raise CodeError('Qui scrivi confronti separati con AND, senza concatenarli.', line)
    reads = [node for node in nodes if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in READS]
    if reads and (len(reads) != 1 or reads[0] is not tree):
        raise CodeError('Leggi un ingresso in una istruzione separata, poi usalo nei calcoli: così l’ordine delle letture è esplicito.', line)
    return tree


def split_statements(code, language):
    """Keep strings and comments intact while preserving actual line numbers."""
    result, buffer, quote, escape, line, start, index = [], '', None, False, 1, 1, 0
    while index < len(code):
        char = code[index]
        if quote:
            buffer += char
            if escape:
                escape = False
            elif char == '\\':
                escape = True
            elif char == quote:
                quote = None
        elif char in ('"', "'"):
            quote, buffer = char, buffer + char
        elif (language == 'Python' and char == '#') or (language != 'Python' and code[index:index + 2] == '//'):
            end = code.find('\n', index)
            index = len(code) if end < 0 else end
            continue
        elif char == ';' or char == '\n':
            if char == '\n' and language != 'Python' and buffer.strip():
                raise CodeError('Concludi l’istruzione con un punto e virgola ;.', start, True)
            if buffer.strip():
                result.append((start, buffer.strip()))
            buffer = ''
            start = line + (char == '\n')
        else:
            if not buffer.strip():
                start = line
            buffer += char
        if char == '\n':
            line += 1
        index += 1
    if quote:
        raise CodeError('Chiudi le virgolette del testo.', start)
    if buffer.strip():
        if language != 'Python':
            raise CodeError('Manca il punto e virgola finale ;.', start, True)
        result.append((start, buffer.strip()))
    return result


def parse(code, language):
    if language not in LANGUAGES:
        raise CodeError('Linguaggio sconosciuto.')
    if len(code) > MAX_CODE or len(code.splitlines()) > 80:
        raise CodeError('Il laboratorio accetta al massimo 8000 caratteri e 80 righe.')
    if '???' in code:
        raise CodeError('Completa i punti segnati con ??? prima di eseguire.', code[:code.index('???')].count('\n') + 1)
    instructions = []
    printer = {'Python': 'print', 'JavaScript': 'console.log', 'C': 'mostra', 'Java': 'System.out.println'}[language]
    for line, statement in split_statements(code, language):
        printed = re.fullmatch(re.escape(printer) + r'\s*\((.*)\)', statement)
        if printed:
            expression = printed.group(1)
            instructions.append(Instruction('', expression, line=line, tree=expression_tree(expression, language, line)))
            continue
        declaration = ''
        constant = False
        if language == 'JavaScript':
            match = re.match(r'(let|const)\s+', statement)
            if match:
                declaration, constant = 'dynamic', match.group(1) == 'const'
                statement = statement[match.end():]
        elif language in ('C', 'Java'):
            pattern = r'(int\b|float\b|bool\b|const\s+char\s*\*)\s*' if language == 'C' else r'(int|float|boolean|String)\s+'
            match = re.match(pattern, statement)
            if match:
                declaration = {'boolean': 'bool', 'String': 'string'}.get(match.group(1), 'string' if match.group(1).startswith('const') else match.group(1))
                statement = statement[match.end():]
        assigned = re.fullmatch(r'([A-Za-z][A-Za-z_0-9]{0,23})\s*=\s*(?!=)(.+)', statement)
        if not assigned:
            raise CodeError('Scrivi un’assegnazione o un’uscita. Qui non servono if, cicli, classi o import. = assegna; == confronta.', line, language in ('C', 'Java'))
        name, expression = assigned.groups()
        if name in set(READS) | {'print', 'mostra', 'True', 'False', 'true', 'false', 'int', 'float', 'bool', 'str', 'let', 'const', 'if', 'elif', 'else', 'for', 'while', 'class', 'return', 'import', 'new', 'void', 'double', 'char', 'switch', 'case'}:
            raise CodeError('Scegli un nome di variabile diverso da una parola riservata o da un comando.', line, True)
        instructions.append(Instruction(name, expression, declaration, line, expression_tree(expression, language, line), constant))
    if not instructions:
        raise CodeError('Il nastro è vuoto: aggiungi almeno un’istruzione.')
    if len(instructions) > 32:
        raise CodeError('Qui sono previste al massimo 32 istruzioni.')
    return instructions


def evaluate(tree, memory, language, reader):
    if language in ('C', 'Java'):
        call_names = {id(node.func) for node in ast.walk(tree) if isinstance(node, ast.Call)}
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and id(node) not in call_names and node.id not in memory:
                raise CodeError(f'{node.id} va dichiarata e inizializzata prima di usarla.', static=True)
    def java_kind(node):
        if isinstance(node, ast.Constant):
            return value(node.value).kind
        if isinstance(node, ast.Name):
            return memory[node.id].kind
        if isinstance(node, ast.Call):
            name = node.func.id
            kinds = [java_kind(arg) for arg in node.args]
            if name == 'logical_not' and kinds != ['bool']:
                raise CodeError('In Java ! richiede un booleano.', static=True)
            if name in READS:
                return READS[name]
            return 'string' if name in ('str', 'unisci') else 'bool' if name == 'logical_not' else 'int' if name in ('java_int', 'cast_int') else 'float'
        if isinstance(node, ast.UnaryOp):
            kind = java_kind(node.operand)
            if kind not in ('int', 'float'):
                raise CodeError('Questo operatore numerico non accetta booleani o testi in Java.', static=True)
            return kind
        if isinstance(node, ast.BoolOp):
            if any(java_kind(child) != 'bool' for child in node.values):
                raise CodeError('In Java && e || richiedono booleani, anche nella parte che il cortocircuito salta.', static=True)
            return 'bool'
        if isinstance(node, ast.BinOp):
            kinds = {java_kind(node.left), java_kind(node.right)}
            if isinstance(node.op, ast.Add) and 'string' in kinds:
                return 'string'
            if not kinds <= {'int', 'float'}:
                raise CodeError('In Java questa operazione richiede numeri.', static=True)
            return 'float' if 'float' in kinds else 'int'
        if isinstance(node, ast.Compare):
            kinds = {java_kind(node.left), java_kind(node.comparators[0])}
            if not kinds <= {'int', 'float'} and not (kinds == {'bool'} and isinstance(node.ops[0], (ast.Eq, ast.NotEq))):
                raise CodeError('Tipi non compatibili con questo confronto Java. I confronti del contenuto delle stringhe sono fuori da queste sfide.', static=True)
            return 'bool'
        raise CodeError('Espressione non prevista.', static=True)
    if language == 'Java':
        java_kind(tree)
    def numeric(item):
        if item.kind in ('int', 'float'):
            return item
        if item.kind == 'bool' and language != 'Java':
            return value(int(item.data))
        raise CodeError('Questa operazione richiede numeri. Converti il testo esplicitamente.', static=True)
    def ev(node):
        if isinstance(node, ast.Constant):
            return value(node.value)
        if isinstance(node, ast.Name):
            if node.id not in memory:
                raise CodeError(f'{node.id} non ha ancora un valore. Prima inizializzala, poi leggila.', static=language in ('C', 'Java'))
            return memory[node.id]
        if isinstance(node, ast.UnaryOp):
            item = ev(node.operand)
            if isinstance(node.op, ast.Not):
                if language == 'Java' and item.kind != 'bool':
                    raise CodeError('In Java ! richiede un booleano.', static=True)
                return value(not item.data)
            item = numeric(item)
            return value(-item.data if isinstance(node.op, ast.USub) else +item.data, item.bits or 64)
        if isinstance(node, ast.BoolOp):
            item = ev(node.values[0])
            for child in node.values[1:]:
                if language == 'Java' and item.kind != 'bool':
                    raise CodeError('In Java && e || richiedono booleani.', static=True)
                if (isinstance(node.op, ast.And) and not item.data) or (isinstance(node.op, ast.Or) and item.data):
                    return value(int(bool(item.data))) if language == 'C' else value(bool(item.data)) if language == 'Java' else item
                item = ev(child)
            if language == 'Java' and item.kind != 'bool':
                raise CodeError('In Java && e || richiedono booleani.', static=True)
            return value(int(bool(item.data))) if language == 'C' else value(bool(item.data)) if language == 'Java' else item
        if isinstance(node, ast.BinOp):
            left, right = ev(node.left), ev(node.right)
            if isinstance(node.op, ast.Add) and (left.kind == 'string' or right.kind == 'string'):
                if language == 'C':
                    raise CodeError('Per unire testi usa unisci(a, b). Il laboratorio non simula l’aritmetica sui puntatori C.', static=True)
                if language == 'Python' and (left.kind != 'string' or right.kind != 'string'):
                    raise CodeError('In Python testo + numero non è valido. Usa str(numero) per il testo oppure int(testo) per il calcolo.')
                return value(display(left, language, False) + display(right, language, False))
            left, right = numeric(left), numeric(right)
            bits = max(left.bits, right.bits) or 64
            a, b = left.data, right.data
            if isinstance(node.op, ast.Div):
                if b == 0:
                    raise CodeError('Divisione per zero: il nastro si ferma qui. I valori infiniti non sono simulati.')
                result = math.trunc(a / b) if language in ('C', 'Java') and left.kind == right.kind == 'int' else a / b
            else:
                result = a + b if isinstance(node.op, ast.Add) else a - b if isinstance(node.op, ast.Sub) else a * b
            return value(result, bits)
        if isinstance(node, ast.Compare):
            left, right = ev(node.left), ev(node.comparators[0])
            if language in ('C', 'JavaScript') and left.kind in ('int', 'float', 'bool') and right.kind in ('int', 'float', 'bool'):
                left, right = numeric(left), numeric(right)
            if 'string' in (left.kind, right.kind) and language in ('C', 'Java'):
                raise CodeError('In C e Java il confronto del contenuto dei testi richiede strumenti specifici, fuori da queste sfide.', static=True)
            if left.kind != right.kind and not {left.kind, right.kind} <= {'int', 'float'}:
                if isinstance(node.ops[0], (ast.Eq, ast.NotEq)) and language == 'Python':
                    return value(left.data == right.data if isinstance(node.ops[0], ast.Eq) else left.data != right.data)
                raise CodeError('Confronta dati dello stesso tipo: le conversioni implicite tra testo e numeri non sono simulate qui.', static=True)
            a, b, op = left.data, right.data, node.ops[0]
            result = a == b if isinstance(op, ast.Eq) else a != b if isinstance(op, ast.NotEq) else a < b if isinstance(op, ast.Lt) else a <= b if isinstance(op, ast.LtE) else a > b if isinstance(op, ast.Gt) else a >= b
            return value(int(result)) if language == 'C' else value(result)
        if isinstance(node, ast.Call):
            name = node.func.id
            if name == 'logical_not' and language != 'Python' and len(node.args) == 1:
                item = ev(node.args[0])
                if language == 'Java' and item.kind != 'bool':
                    raise CodeError('In Java ! richiede un booleano.', static=True)
                if language == 'C' and item.kind == 'string':
                    raise CodeError('Qui non si simula la negazione di un puntatore C: non coincide con controllare un testo vuoto.', static=True)
                return value(int(not item.data)) if language == 'C' else value(not item.data)
            if name in READS:
                if node.args:
                    raise CodeError('I comandi leggi_...() non ricevono argomenti.')
                return reader(READS[name])
            args = [ev(arg) for arg in node.args]
            if name == 'unisci' and len(args) == 2 and all(arg.kind == 'string' for arg in args):
                return value(args[0].data + args[1].data)
            if name == 'parseInt' and language == 'JavaScript' and len(args) == 2 and args[1].data == 10:
                args = args[:1]
            allowed = {'Python': ('int', 'float', 'str', 'bool'), 'JavaScript': ('parseInt', 'number', 'str', 'Boolean'),
                       'C': ('atoi', 'str', 'cast_int', 'cast_float', 'as_float32'),
                       'Java': ('java_int', 'str', 'cast_int', 'cast_float', 'as_float32')}[language]
            if name not in allowed or len(args) != 1:
                raise CodeError('Funzione non prevista o argomenti errati. Apri Dati e comandi.')
            item = args[0]
            try:
                if name in ('int', 'java_int', 'atoi', 'parseInt', 'cast_int'):
                    if name in ('atoi', 'java_int') and item.kind != 'string':
                        raise CodeError('Questa conversione legge un testo numerico.', static=True)
                    if name in ('atoi', 'parseInt'):
                        match = re.match(r'\s*([+-]?\d+)', str(item.data))
                        if not match and name == 'atoi':
                            return value(0)
                        if not match:
                            raise ValueError()
                        return value(int(match.group(1)))
                    if name == 'java_int' and not re.fullmatch(r'[+-]?\d+', item.data):
                        raise ValueError()
                    if name == 'cast_int' and item.kind not in ('int', 'float'):
                        raise CodeError('Il cast numerico richiede un numero, non un testo.', static=True)
                    return value(int(item.data))
                if name in ('float', 'number', 'cast_float', 'as_float32'):
                    if name in ('cast_float', 'as_float32') and item.kind not in ('int', 'float'):
                        raise CodeError('Il cast float richiede un numero, non una stringa.', static=True)
                    raw = 0.0 if name == 'number' and item.kind == 'string' and not item.data.strip() else float(item.data)
                    return value(raw, 32 if name in ('cast_float', 'as_float32') else 64)
                if name == 'str':
                    return value(display(item, language, False))
                return value(bool(item.data))
            except (ValueError, OverflowError):
                raise CodeError('Il contenuto non si può convertire così. Prova un testo numerico valido; NaN e infiniti non sono simulati.')
        raise CodeError('Espressione non prevista.')
    return ev(tree)


@dataclass(frozen=True)
class Frame:
    line: int
    title: str
    message: str
    memory: tuple
    outputs: tuple
    consumed: int
    target: str = ''
    before: object = None
    after: object = None


@dataclass
class Execution:
    frames: list
    error: object = None


def run(instructions, inputs, language):
    memory, declarations, outputs, consumed = {}, {}, [], 0
    frames = [Frame(0, 'Pronti sul nastro', 'Nessuna istruzione eseguita: la memoria e lo schermo sono ancora vuoti.', (), (), 0)]
    def reader(kind):
        nonlocal consumed
        if consumed >= len(inputs):
            raise CodeError('Gli ingressi sono finiti: c’è una lettura in più.')
        item = inputs[consumed]
        if item.kind != kind:
            raise CodeError(f'Il prossimo ingresso è {item.kind}, ma stai leggendo {kind}. Rispetta l’ordine degli ingressi.')
        consumed += 1
        return value(item.data, 32 if language in ('C', 'Java') and item.kind == 'float' else 64)
    for instruction in instructions:
        previous_consumed = consumed
        try:
            if instruction.target and instruction.kind and instruction.target in declarations:
                raise CodeError('Questa variabile è già dichiarata. Per aggiornarla non ripetere il tipo o let.', static=True)
            if instruction.target and language in ('C', 'Java', 'JavaScript') and not instruction.kind and instruction.target not in declarations:
                raise CodeError('Dichiara la variabile prima di assegnarle un valore. JavaScript qui usa let o const (ambito rigoroso).', static=True)
            if instruction.target in declarations and declarations[instruction.target][1]:
                raise CodeError('Una variabile const non può ricevere una nuova assegnazione.', static=True)
            item = evaluate(instruction.tree or expression_tree(instruction.expression, language, instruction.line), memory, language, reader)
            before = memory.get(instruction.target)
            if instruction.target:
                if language in ('C', 'Java'):
                    kind = instruction.kind or declarations[instruction.target][0]
                    if kind == 'int' and item.kind in ('float', 'bool') and language == 'C':
                        item = value(int(item.data))
                    elif kind == 'float' and (item.kind in ('int', 'float') or item.kind == 'bool' and language == 'C'):
                        if language == 'Java' and item.kind == 'float' and item.bits == 64:
                            raise CodeError('In Java un double non entra implicitamente in float. Usa il suffisso f o un cast esplicito (float)(...).', static=True)
                        item = value(float(item.data), 32)
                    elif kind == 'bool' and language == 'C' and item.kind in ('int', 'float'):
                        item = value(bool(item.data))
                    elif kind != item.kind:
                        raise CodeError(f'Il valore è {item.kind}, ma la variabile richiede {kind}. Controlla il tipo o la conversione.', static=True)
                memory[instruction.target] = item
                if instruction.kind:
                    declarations[instruction.target] = (instruction.kind, instruction.constant)
                if len(memory) > 8:
                    raise CodeError('In questo laboratorio usa al massimo otto variabili.')
                old = display(before, language) if before else 'non inizializzata'
                message = f'{instruction.target}: {old} → {display(item, language)}. '
                message += 'Legge il prossimo ingresso e lo memorizza.' if consumed != previous_consumed else 'Calcola a destra con i valori attuali, poi scrivi nella cella a sinistra.'
                title = 'Memoria aggiornata'
            else:
                outputs.append(item)
                message = 'Sullo schermo compare ' + display(item, language) + '. Mostrare un valore non lo modifica e non lo ricalcola in seguito.'
                title = 'Nuova uscita'
            frames.append(Frame(instruction.line, title, message, tuple(memory.items()), tuple(outputs), consumed, instruction.target, before, item))
        except (CodeError, RecursionError, TypeError) as error:
            if not isinstance(error, CodeError):
                error = CodeError('Espressione troppo complessa o tipi non compatibili.')
            error.line = instruction.line
            if error.static and language in ('C', 'Java'):
                frames = frames[:1]
            return Execution(frames, error)
    return Execution(frames)


def execute(code, inputs, language):
    return run(parse(code, language), inputs, language)
