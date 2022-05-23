# lang.py

root = {
    'error': {
        'database': 'Database error',
        'invalid': {
            'number': {
                'generic': 'Invalid number',
                'min': 'Invalid number, min is {0}',
                'max': 'Invalid number, max is {0}',
                'minmax': 'Invalid number, min is {0} and max is {1}.'
            },
            'string': {
                'illegal': 'String contains illegal character(s).',
                'generic': 'Invalid string',
                'min': 'Invalid string, min length is {0}',
                'max': 'Invalid string, max length is {0}',
                'minmax': 'Invalid string, min length is {0} and max is {1}.'
            },
            'integer': 'Invalid integer',
            'id': 'Invalid ID, please supply a number.',
            'idwithtype': 'Invalid {0} ID, please supply a number.',
            'generic': 'Invalid {0}'
        },
        'internal': 'Internal error (aka developer fucked up)',
        'unknown': 'Unknown error, please contact andyinnie.'
    },
    'supply': {
        'number': 'Please supply a number.',
        'integer': 'Please supply an integer.',
        'id': 'Please supply an ID.',
        'generic': 'Please supply {0}.'
    }
}


def lang(id, *fmt):
    path = id.split('.')
    current = root
    for term in path:
        try:
            current = current[term]
        except KeyError:
            return id
        if isinstance(current, str):
            return current if fmt is None else current.format(*fmt)


def load(core):
    core.exports.put('lang', lang)
    print('Exported lang')
