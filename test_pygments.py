from pygments import *
from pygments.lexers import *

CODE="""\
```python
for n in range(100):
    print(n)
```
"""

CODE = '''FOO=bar ls -al ./ foo="bar"'''


lexer = get_lexer_by_name("sh")

for token_type, token in lexer.get_tokens(CODE):
    print(f"{token_type}\t{token}")

