from jinja2 import Template
t = Template('''
{% set total = 0 %}
{% for x in [1, 2, 3] %}
  {% set total = total + x %}
{% endfor %}
Result: {{ total }}
''')
print(t.render())
